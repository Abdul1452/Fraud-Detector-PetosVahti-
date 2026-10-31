"""Training + replay-evaluation pipeline.

Time-ordered splits over one continuous simulated stream (no shuffling, so
no leakage from the future):

    | warm-up | train | calibrate | test (replay) |
      profiles   fit     Platt map   scored online by the real Scorer

The test window is not scored as a static matrix: every transaction goes
through `Scorer.score` in order, so the evaluation includes the online
learning policy (blocked payments do not teach the profile) and yields real
per-call latency.
"""

import collections
import hashlib
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from petosvahti.domain import HELSINKI, FraudPattern, Transaction
from petosvahti.generator import Simulator
from petosvahti.scoring.features import FEATURE_NAMES, FeatureStore, FeatureVector
from petosvahti.scoring.forest import CompiledForest
from petosvahti.scoring.model import FraudModel
from petosvahti.scoring.policy import Decision
from petosvahti.scoring.reasons import base_rates
from petosvahti.scoring.scorer import Scorer, ScoreResult

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]


@dataclass(frozen=True)
class TrainConfig:
    n_customers: int = 2000
    seed: int = 2026
    start: datetime = datetime(2026, 8, 1, tzinfo=HELSINKI)
    warmup_days: int = 31  # one full month, so every customer's rent payee is known
    train_days: int = 21
    calib_days: int = 7
    test_days: int = 14
    fraud_incidents_per_1000_per_day: float = 3.5
    n_estimators: int = 200
    max_samples: int = 512


# Small enough for CI and first-run demos (~10 s), still enough fraud to calibrate.
QUICK_CONFIG = TrainConfig(
    n_customers=400,
    train_days=10,
    calib_days=7,
    test_days=5,
    fraud_incidents_per_1000_per_day=10.0,
    n_estimators=100,
    max_samples=256,
)


@dataclass
class Window:
    rows: list[FeatureVector] = field(default_factory=list)
    patterns: list[FraudPattern | None] = field(default_factory=list)

    def x(self) -> FloatArray:
        return np.asarray(self.rows, dtype=np.float64)

    def y(self) -> npt.NDArray[np.int_]:
        return np.asarray([p is not None for p in self.patterns], dtype=np.int_)


@dataclass(frozen=True)
class ReplayRecord:
    transaction: Transaction
    pattern: FraudPattern | None
    result: ScoreResult


@dataclass
class TrainingResult:
    model: FraudModel
    config: TrainConfig
    evaluation: dict[str, Any]
    records: list[ReplayRecord]


def _collect(sim: Simulator, store: FeatureStore, until: datetime) -> Window:
    window = Window()
    for lt in sim.take_until(until):
        window.rows.append(store.extract_and_update(lt.transaction, learn=True))
        window.patterns.append(lt.fraud_pattern)
    return window


def train(cfg: TrainConfig = TrainConfig(), log: Callable[[str], None] = print) -> TrainingResult:
    sim = Simulator(cfg.n_customers, cfg.seed, cfg.start, cfg.fraud_incidents_per_1000_per_day)
    store = FeatureStore()
    t_warm = cfg.start + timedelta(days=cfg.warmup_days)
    t_train = t_warm + timedelta(days=cfg.train_days)
    t_calib = t_train + timedelta(days=cfg.calib_days)
    t_test = t_calib + timedelta(days=cfg.test_days)

    # Warm-up: historic traffic before any model existed, so profiles learn from everything.
    warmup = sim.take_until(t_warm)
    for lt in warmup:
        store.update(lt.transaction, learn=True)
    train_w = _collect(sim, store, t_train)
    calib_w = _collect(sim, store, t_calib)
    log(f"simulated {len(warmup):,} warm-up, {len(train_w.rows):,} train, "
        f"{len(calib_w.rows):,} calibration transactions")  # fmt: skip

    forest = IsolationForest(
        n_estimators=cfg.n_estimators,
        max_samples=cfg.max_samples,
        contamination="auto",
        random_state=cfg.seed,
    ).fit(train_w.x())

    # Platt scaling: anomaly score -> P(fraud), fitted on the calibration window only.
    calib_anomaly = -forest.score_samples(calib_w.x())
    platt = LogisticRegression(C=100.0).fit(calib_anomaly.reshape(-1, 1), calib_w.y())
    slope, intercept = float(platt.coef_[0, 0]), float(platt.intercept_[0])
    if slope <= 0:
        raise RuntimeError("calibration slope <= 0: anomaly score does not rank fraud")

    trained_at = datetime.now(UTC)
    model = FraudModel(
        forest=forest,
        compiled=CompiledForest.from_sklearn(forest),
        calibration=(slope, intercept),
        reason_rates=base_rates(train_w.rows),
        version=f"iforest-{trained_at:%Y%m%d}-s{cfg.seed}",
        trained_at=trained_at.isoformat(timespec="seconds"),
    )

    scorer = Scorer(model, store)
    records = [
        ReplayRecord(lt.transaction, lt.fraud_pattern, scorer.score(lt.transaction))
        for lt in sim.take_until(t_test)
    ]
    log(f"replayed {len(records):,} test transactions through the online scorer")

    evaluation = evaluate(records, train_w, cfg)
    model.summary = {
        "pr_auc": evaluation["headline"]["pr_auc"],
        "recall_flagged": evaluation["headline"]["recall_flagged"],
        "alerts_per_1000": evaluation["headline"]["alerts_per_1000"],
        "p99_latency_ms": evaluation["latency_ms"]["p99"],
        "config": {k: str(v) for k, v in asdict(cfg).items()},
    }
    return TrainingResult(model, cfg, evaluation, records)


# -- evaluation ----------------------------------------------------------------


def _precision_recall(mask: BoolArray, y: BoolArray) -> dict[str, float]:
    tp = int((mask & y).sum())
    return {
        "precision": tp / max(int(mask.sum()), 1),
        "recall": tp / max(int(y.sum()), 1),
        "alerts_per_1000": 1000 * float(mask.mean()) if mask.size else 0.0,
    }


def _test_matrix(records: Sequence[ReplayRecord]) -> FloatArray:
    return np.asarray([[r.result.features[n] for n in FEATURE_NAMES] for r in records])


def evaluate(records: Sequence[ReplayRecord], train_w: Window, cfg: TrainConfig) -> dict[str, Any]:
    y = np.asarray([r.pattern is not None for r in records])
    risk = np.asarray([r.result.risk_score for r in records])
    amount = np.asarray([r.transaction.amount_eur for r in records])
    decision = np.asarray([r.result.decision.value for r in records])
    flagged = decision != Decision.APPROVE.value
    blocked = decision == Decision.BLOCK.value
    reviewed = decision == Decision.REVIEW.value
    n = len(records)

    top_k = max(1, n // 100)
    top_idx = np.argsort(-risk, kind="stable")[:top_k]

    patterns: dict[str, dict[str, float]] = {}
    for pattern in FraudPattern:
        mask = np.asarray([r.pattern is pattern for r in records])
        if mask.any():
            patterns[pattern.value] = {
                "transactions": int(mask.sum()),
                "recall_flagged": float(flagged[mask].mean()),
                "blocked_share": float(blocked[mask].mean()),
                "median_risk": float(np.median(risk[mask])),
            }

    thresholds = [
        {"threshold": t, **_precision_recall(risk >= t, y)}
        for t in (20, 30, 40, 50, 60, 70, 80, 85, 90, 95)
    ]

    # Baseline 1: the kind of static rules a bank starts with.
    x_test = _test_matrix(records)
    col = {name: i for i, name in enumerate(FEATURE_NAMES)}
    rules = (
        ((amount >= 1000) & (x_test[:, col["new_payee"]] > 0))
        | (x_test[:, col["tx_count_1h"]] >= 5)
        | ((x_test[:, col["new_device"]] > 0) & (x_test[:, col["new_country"]] > 0))
    )
    # Baseline 2 (upper-bound reference): a supervised model that sees labels.
    supervised = HistGradientBoostingClassifier(random_state=cfg.seed).fit(train_w.x(), train_w.y())
    supervised_ap = float(average_precision_score(y, supervised.predict_proba(x_test)[:, 1]))

    latency = np.asarray([r.result.latency_ms for r in records])

    fn = [r for r, f, yy in zip(records, flagged, y, strict=True) if yy and not f]
    fp = [r for r, f, yy in zip(records, flagged, y, strict=True) if f and not yy]

    def reason_combos(rs: Sequence[ReplayRecord]) -> list[tuple[str, int]]:
        counter = collections.Counter(
            " + ".join(sorted(x.code for x in r.result.reasons)) or "(none)" for r in rs
        )
        return counter.most_common(5)

    return {
        "dataset": {
            "test_transactions": n,
            "test_fraud": int(y.sum()),
            "test_fraud_rate": float(y.mean()),
            "train_transactions": len(train_w.rows),
            "train_fraud_rate": float(train_w.y().mean()),
        },
        "headline": {
            "pr_auc": float(average_precision_score(y, risk)),
            "roc_auc": float(roc_auc_score(y, risk)),
            "precision_top1pct": float(y[top_idx].mean()),
            "precision_flagged": _precision_recall(flagged, y)["precision"],
            "recall_flagged": _precision_recall(flagged, y)["recall"],
            "precision_blocked": _precision_recall(blocked, y)["precision"],
            "recall_blocked": _precision_recall(blocked, y)["recall"],
            "alerts_per_1000": 1000 * float(reviewed.mean()),
            "legit_blocked_per_1000": 1000 * float((blocked & ~y).sum()) / n,
            "fraud_value_eur": float(amount[y].sum()),
            "fraud_value_stopped_eur": float(amount[y & blocked].sum()),
            "fraud_value_held_eur": float(amount[y & reviewed].sum()),
        },
        "baselines": {
            "rules": _precision_recall(rules, y),
            "supervised_pr_auc": supervised_ap,
        },
        "thresholds": thresholds,
        "patterns": patterns,
        "latency_ms": {
            "p50": float(np.percentile(latency, 50)),
            "p95": float(np.percentile(latency, 95)),
            "p99": float(np.percentile(latency, 99)),
            "max": float(latency.max()),
        },
        "errors": {
            "false_negatives": len(fn),
            "false_negative_patterns": collections.Counter(
                r.pattern.value for r in fn if r.pattern
            ).most_common(),
            "false_negative_median_eur": float(np.median([r.transaction.amount_eur for r in fn]))
            if fn
            else 0.0,
            "false_negative_reasons": reason_combos(fn),
            "false_positives": len(fp),
            "false_positive_channels": collections.Counter(
                r.transaction.channel.value for r in fp
            ).most_common(),
            "false_positive_reasons": reason_combos(fp),
        },
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
