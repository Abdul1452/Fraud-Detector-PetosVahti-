"""Fraud model: Isolation Forest anomaly score → calibrated 0-100 risk.

The forest is unsupervised [R18][R19]: it learns what normal traffic looks
like and never sees a label. Labels are used once, on a held-out calibration
window, to fit a monotone (isotonic) map from anomaly score to fraud
probability, so that `risk_score ≈ 100 · P(fraud)` and the policy thresholds
have a probabilistic meaning. Isotonic rather than Platt scaling: at a 0.4 %
base rate the logistic curve was badly under-confident in the tail (see the
model evaluation report). Monotone, so ranking (PR-AUC) is unchanged.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import numpy.typing as npt
from sklearn.ensemble import IsolationForest

from petosvahti.scoring.features import FEATURE_NAMES, FeatureVector
from petosvahti.scoring.forest import CompiledForest
from petosvahti.scoring.reasons import Reason, explain

FloatArray = npt.NDArray[np.float64]


_ONLINE_MAX_ROWS = 64  # below this the compiled walk wins; above, scikit-learn's C loop


@dataclass
class FraudModel:
    forest: IsolationForest
    compiled: CompiledForest
    calibration: tuple[FloatArray, FloatArray]  # isotonic knots: anomaly → P(fraud)
    reason_rates: dict[str, float]
    version: str
    trained_at: str
    feature_names: tuple[str, ...] = FEATURE_NAMES
    summary: dict[str, Any] = field(default_factory=dict)

    def anomaly(self, x: FloatArray) -> FloatArray:
        """Raw anomaly score; higher = more isolated (≈ 0.35 normal, > 0.6 odd)."""
        if x.shape[0] <= _ONLINE_MAX_ROWS:
            return self.compiled.score(x)
        return np.asarray(-self.forest.score_samples(x), dtype=np.float64)

    def risk_from_anomaly(self, anomaly: FloatArray) -> FloatArray:
        knots_x, knots_y = self.calibration
        return np.asarray(100.0 * np.interp(anomaly, knots_x, knots_y), dtype=np.float64)

    def risk(self, x: FloatArray) -> FloatArray:
        return self.risk_from_anomaly(self.anomaly(x))

    def risk_one(self, features: FeatureVector) -> float:
        return float(self.risk(np.asarray([features], dtype=np.float64))[0])

    def explain(self, features: FeatureVector, limit: int = 3) -> list[Reason]:
        return explain(features, self.reason_rates, limit)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: Path) -> "FraudModel":
        # joblib uses pickle: only load artifacts this project produced.
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError(f"{path} does not contain a {cls.__name__}")
        if tuple(obj.feature_names) != FEATURE_NAMES:
            raise ValueError(
                f"{path} was trained on features {obj.feature_names}; "
                f"this code expects {FEATURE_NAMES}. Retrain with `petosvahti train`."
            )
        return obj

    def describe(self) -> Mapping[str, Any]:
        return {"version": self.version, "trained_at": self.trained_at, **self.summary}
