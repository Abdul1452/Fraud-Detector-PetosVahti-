"""Model: compiled-forest parity, calibration, persistence, end-to-end training quality."""

import dataclasses
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import IsolationForest

from petosvahti.scoring.features import FEATURE_NAMES
from petosvahti.scoring.forest import CompiledForest
from petosvahti.scoring.model import FraudModel
from petosvahti.scoring.policy import Decision
from petosvahti.training import TrainingResult
from petosvahti.training.report import render


def test_compiled_forest_matches_scikit_learn_exactly() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=(3000, 6))
    x[:, 2] = x[:, 2] > 1.2  # a binary column, like the novelty flags
    forest = IsolationForest(n_estimators=50, max_samples=128, random_state=0).fit(x)
    probe = rng.normal(scale=2.0, size=(500, 6))
    np.testing.assert_allclose(
        CompiledForest.from_sklearn(forest).score(probe), -forest.score_samples(probe), atol=1e-12
    )


def test_model_scores_single_rows_and_batches_identically(quick_model: FraudModel) -> None:
    rng = np.random.default_rng(1)
    x = rng.normal(size=(200, len(FEATURE_NAMES)))
    batch = quick_model.risk(x)  # > 64 rows: scikit-learn path
    single = np.array([quick_model.risk_one(tuple(row)) for row in x])  # compiled path
    np.testing.assert_allclose(batch, single, atol=1e-9)
    assert ((batch >= 0) & (batch <= 100)).all()


def test_calibration_is_monotone(quick_model: FraudModel) -> None:
    anomaly = np.linspace(0.2, 0.9, 200)
    risk = quick_model.risk_from_anomaly(anomaly)
    assert (np.diff(risk) >= 0).all()
    assert risk[0] < 5 and risk[-1] > 50


def test_save_load_roundtrip(quick_model: FraudModel, tmp_path: Path) -> None:
    path = tmp_path / "m.joblib"
    quick_model.save(path)
    loaded = FraudModel.load(path)
    row = tuple(float(i) for i in range(len(FEATURE_NAMES)))
    assert loaded.version == quick_model.version
    assert loaded.risk_one(row) == quick_model.risk_one(row)


def test_load_rejects_feature_mismatch(quick_model: FraudModel, tmp_path: Path) -> None:
    path = tmp_path / "old.joblib"
    dataclasses.replace(quick_model, feature_names=("legacy",)).save(path)
    with pytest.raises(ValueError, match="Retrain"):
        FraudModel.load(path)


def test_quick_training_detects_fraud(quick_result: TrainingResult) -> None:
    e = quick_result.evaluation
    assert e["dataset"]["test_fraud"] > 20
    assert e["headline"]["pr_auc"] > 0.6
    assert e["headline"]["recall_flagged"] > 0.6
    assert e["headline"]["precision_blocked"] > 0.8
    assert e["latency_ms"]["p99"] < 100
    # The model beats the static-rules baseline at a similar or lower alert rate.
    assert e["headline"]["recall_flagged"] >= e["baselines"]["rules"]["recall"] - 0.05


def test_replay_uses_online_policy(quick_result: TrainingResult) -> None:
    decisions = {r.result.decision for r in quick_result.records}
    assert decisions == set(Decision)


def test_report_renders_every_section(quick_result: TrainingResult) -> None:
    md = render(quick_result, "models/x.joblib", "abc123")
    for heading in (
        "Headline metrics",
        "Threshold analysis",
        "Error analysis",
        "Limitations",
        "Decision",
    ):
        assert f"## {heading}" in md
    assert "abc123" in md and "{" not in md.split("## Headline")[0]
