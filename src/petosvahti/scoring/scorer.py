"""Scorer: feature store + model + policy, the one entry point adapters call."""

import threading
from time import perf_counter

from pydantic import BaseModel

from petosvahti.domain import Transaction
from petosvahti.scoring.features import FeatureStore, as_dict
from petosvahti.scoring.model import FraudModel
from petosvahti.scoring.policy import Decision, decide
from petosvahti.scoring.reasons import Reason


class ScoreResult(BaseModel):
    transaction_id: str
    customer_id: str
    risk_score: float
    decision: Decision
    reasons: list[Reason]
    model_version: str
    latency_ms: float
    features: dict[str, float]


class Scorer:
    """Thread-safe scoring of single transactions against live customer state.

    One lock covers extract → predict → update so two concurrent payments by
    the same customer cannot both be scored against stale history. That
    serialises scoring (~1-2 ms each); sharding by customer id is the scale-out
    path, the same way a Kafka topic would be partitioned.
    """

    def __init__(self, model: FraudModel, store: FeatureStore | None = None) -> None:
        self.model = model
        self.store = store or FeatureStore()
        self._lock = threading.Lock()

    def score(self, tx: Transaction) -> ScoreResult:
        started = perf_counter()
        with self._lock:
            features = self.store.extract(tx)
            risk = round(self.model.risk_one(features), 1)
            decision = decide(risk)
            self.store.update(tx, learn=decision is Decision.APPROVE)
        return ScoreResult(
            transaction_id=tx.transaction_id,
            customer_id=tx.customer_id,
            risk_score=risk,
            decision=decision,
            reasons=self.model.explain(features),
            model_version=self.model.version,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            features={k: round(v, 4) for k, v in as_dict(features).items()},
        )

    def observe(self, tx: Transaction) -> None:
        """Add historical, already-settled traffic to customer profiles (warm-up)."""
        with self._lock:
            self.store.update(tx, learn=True)
