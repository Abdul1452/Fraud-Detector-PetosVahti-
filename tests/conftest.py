"""Shared fixtures. The quick model is trained once per test session (~15 s)."""

from datetime import datetime

import pytest

from petosvahti.domain import HELSINKI, Channel, Transaction
from petosvahti.scoring.model import FraudModel
from petosvahti.training import QUICK_CONFIG, TrainingResult, train


@pytest.fixture(scope="session")
def quick_result() -> TrainingResult:
    return train(QUICK_CONFIG, log=lambda _: None)


@pytest.fixture(scope="session")
def quick_model(quick_result: TrainingResult) -> FraudModel:
    return quick_result.model


def make_tx(**overrides: object) -> Transaction:
    fields: dict[str, object] = {
        "customer_id": "C1",
        "timestamp": datetime(2026, 10, 1, 12, 0, tzinfo=HELSINKI),
        "amount_eur": 25.0,
        "channel": Channel.CARD,
        "payee_id": "prisma-turku",
        "payee_name": "Prisma Turku",
        "device_id": "dev-1",
    }
    fields.update(overrides)
    return Transaction.model_validate(fields)
