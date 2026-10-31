"""Kafka wire format (no broker needed) and the CLI entry point."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from conftest import make_tx
from petosvahti.cli import main
from petosvahti.domain import FraudPattern, LabelledTransaction
from petosvahti.scoring.model import FraudModel
from petosvahti.streaming.kafka import LABEL_HEADER, REPLAY_HEADER, decode, encode


def test_encode_decode_roundtrip() -> None:
    lt = LabelledTransaction(make_tx(amount_eur=4800.0), FraudPattern.APP_SCAM)
    key, value, headers = encode(lt, replay=False)
    assert key == b"C1"  # partition by customer keeps each customer's payments ordered
    tx, label, replay = decode(value, headers)
    assert tx == lt.transaction
    assert label == "app_scam"
    assert replay is False


def test_decode_accepts_dict_headers_and_replay_flag() -> None:
    _, value, _ = encode(LabelledTransaction(make_tx()), replay=True)
    tx, label, replay = decode(value, {REPLAY_HEADER: b"1", LABEL_HEADER: "legit"})
    assert replay is True and label == "legit" and tx.customer_id == "C1"


@pytest.mark.parametrize("value", [None, b"{}", b"not json"])
def test_decode_rejects_poison_messages(value: bytes | None) -> None:
    with pytest.raises(ValueError):  # ValidationError is a ValueError
        decode(value, None)
    assert issubclass(ValidationError, ValueError)


def test_cli_quick_train_writes_model_and_report(tmp_path: Path) -> None:
    model_path = tmp_path / "model.joblib"
    report = tmp_path / "report.md"
    args = ["train", "--quick", "--customers", "200", "--model", str(model_path)]
    assert main([*args, "--report", str(report)]) == 0
    assert FraudModel.load(model_path).version.startswith("iforest-")
    assert "## Threshold analysis" in report.read_text(encoding="utf-8")
