"""In-memory feed of scored transactions plus the counters behind /metrics.

Thread-safe: written by the stream source thread and request handlers, read
by the dashboard. Bounded (ring buffer + rolling latency window), so a
long-running demo does not grow memory. Persisting decisions for audit
(PostgreSQL) is the production replacement for this module.
"""

import threading
import time
from collections import Counter, deque
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel

from petosvahti.domain import Transaction
from petosvahti.scoring.policy import Decision
from petosvahti.scoring.scorer import ScoreResult

LEGIT = "legit"
Source = Literal["stream", "api"]


class FeedEvent(BaseModel):
    seq: int
    scored_at: float  # wall clock, epoch seconds
    source: Source
    label: str | None  # synthetic ground truth: "legit" | fraud pattern | None (unknown)
    transaction: Transaction
    result: ScoreResult


class Feed:
    def __init__(self, maxlen: int = 500, latency_window: int = 5000) -> None:
        self._lock = threading.Lock()
        self._events: deque[FeedEvent] = deque(maxlen=maxlen)
        self._latency: deque[float] = deque(maxlen=latency_window)
        self._latency_sum = 0.0
        self._seq = 0
        self._decisions: Counter[str] = Counter()
        self._sources: Counter[str] = Counter()
        self._truth: Counter[str] = Counter()
        self._patterns: dict[str, Counter[str]] = {}
        self._fraud_eur: dict[str, float] = {"attempted": 0.0, "blocked": 0.0, "held": 0.0}

    def add(
        self, tx: Transaction, result: ScoreResult, source: Source, label: str | None
    ) -> FeedEvent:
        with self._lock:
            self._seq += 1
            event = FeedEvent(
                seq=self._seq,
                scored_at=time.time(),
                source=source,
                label=label,
                transaction=tx,
                result=result,
            )
            self._events.append(event)
            self._latency.append(result.latency_ms)
            self._latency_sum += result.latency_ms
            decision = result.decision.value
            self._decisions[decision] += 1
            self._sources[source] += 1
            if label is not None:
                kind = "legit" if label == LEGIT else "fraud"
                self._truth[kind] += 1
                if result.decision is not Decision.APPROVE:
                    self._truth[f"{kind}_flagged"] += 1
                if result.decision is Decision.BLOCK:
                    self._truth[f"{kind}_blocked"] += 1
                if kind == "fraud":
                    self._patterns.setdefault(label, Counter())[decision] += 1
                    self._fraud_eur["attempted"] += tx.amount_eur
                    if result.decision is Decision.BLOCK:
                        self._fraud_eur["blocked"] += tx.amount_eur
                    elif result.decision is Decision.REVIEW:
                        self._fraud_eur["held"] += tx.amount_eur
            return event

    def since(self, seq: int, limit: int = 100) -> list[FeedEvent]:
        """Events newer than `seq`, oldest first, at most the `limit` most recent."""
        with self._lock:
            newer = [e for e in self._events if e.seq > seq]
        return newer[-limit:]

    def _quantiles(self) -> dict[str, float]:
        if not self._latency:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0}
        values = np.percentile(np.fromiter(self._latency, dtype=np.float64), [50, 95, 99])
        return {"p50": float(values[0]), "p95": float(values[1]), "p99": float(values[2])}

    def stats(self) -> dict[str, Any]:
        with self._lock:
            now = time.time()
            recent = sum(1 for e in self._events if now - e.scored_at <= 10.0)
            return {
                "scored": self._seq,
                "decisions": {d.value: self._decisions[d.value] for d in Decision},
                "by_source": dict(self._sources),
                "throughput_per_s": recent / 10.0,
                "latency_ms": self._quantiles(),
                "ground_truth": {
                    **{
                        k: self._truth[k]
                        for k in (
                            "fraud",
                            "fraud_flagged",
                            "fraud_blocked",
                            "legit",
                            "legit_flagged",
                            "legit_blocked",
                        )
                    },
                    "fraud_eur": round(self._fraud_eur["attempted"], 2),
                    "fraud_eur_blocked": round(self._fraud_eur["blocked"], 2),
                    "fraud_eur_held": round(self._fraud_eur["held"], 2),
                },
                "patterns": {
                    p: {
                        "seen": sum(c.values()),
                        "flagged": c[Decision.REVIEW.value] + c[Decision.BLOCK.value],
                    }
                    for p, c in self._patterns.items()
                },
            }

    def prometheus(self, model_version: str) -> str:
        """Prometheus text exposition format (no client library needed)."""
        with self._lock:
            q = self._quantiles()
            lines = [
                "# HELP petosvahti_transactions_scored_total Transactions scored, by decision.",
                "# TYPE petosvahti_transactions_scored_total counter",
                *(
                    f'petosvahti_transactions_scored_total{{decision="{d.value}"}} '
                    f"{self._decisions[d.value]}"
                    for d in Decision
                ),
                "# HELP petosvahti_scoring_latency_ms In-process scoring latency (rolling window).",
                "# TYPE petosvahti_scoring_latency_ms summary",
                f'petosvahti_scoring_latency_ms{{quantile="0.5"}} {q["p50"]:.4f}',
                f'petosvahti_scoring_latency_ms{{quantile="0.95"}} {q["p95"]:.4f}',
                f'petosvahti_scoring_latency_ms{{quantile="0.99"}} {q["p99"]:.4f}',
                f"petosvahti_scoring_latency_ms_sum {self._latency_sum:.4f}",
                f"petosvahti_scoring_latency_ms_count {self._seq}",
                "# HELP petosvahti_synthetic_fraud_total Labelled (synthetic) fraud by outcome.",
                "# TYPE petosvahti_synthetic_fraud_total counter",
                f'petosvahti_synthetic_fraud_total{{outcome="flagged"}} '
                f"{self._truth['fraud_flagged']}",
                f'petosvahti_synthetic_fraud_total{{outcome="missed"}} '
                f"{self._truth['fraud'] - self._truth['fraud_flagged']}",
                "# HELP petosvahti_model_info Model currently serving.",
                "# TYPE petosvahti_model_info gauge",
                f'petosvahti_model_info{{version="{model_version}"}} 1',
            ]
        return "\n".join(lines) + "\n"
