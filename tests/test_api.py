"""HTTP API: scoring contract, ops endpoints, and the live simulator source."""

import time
from collections.abc import Callable, Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import make_tx
from petosvahti.api import create_app
from petosvahti.api.app import AppContext
from petosvahti.config import Settings
from petosvahti.scoring.model import FraudModel


def _payload(**overrides: Any) -> dict[str, Any]:
    tx = make_tx(**overrides)
    return tx.model_dump(mode="json", exclude={"transaction_id"})


@pytest.fixture
def app(quick_model: FraudModel) -> FastAPI:
    return create_app(Settings(source="none", auto_train=False), model=quick_model)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as c:
        ctx: AppContext = app.state.ctx
        now = make_tx().timestamp
        for i in range(30):  # a month of ordinary Prisma shopping for C1
            ctx.scorer.observe(make_tx(timestamp=now - timedelta(days=30 - i), amount_eur=20.0 + i))
        yield c


def _wait_for(check: Callable[[], bool], timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.1)
    raise AssertionError("condition not met in time")


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["model_version"].startswith("iforest-")
    assert body["source"] == {"kind": "none"}


def test_everyday_payment_is_approved(client: TestClient) -> None:
    r = client.post("/score", json=_payload(amount_eur=31.5))
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] == "approve"
    assert body["risk_score"] < 20
    assert body["transaction_id"]


def test_safe_account_scam_is_stopped_with_reasons(client: TestClient) -> None:
    scam = _payload(
        amount_eur=4800.0,
        channel="siirto",
        payee_id="FI2179900000000001",
        payee_name="Stranger",
        timestamp=make_tx().timestamp + timedelta(hours=8),
    )
    body = client.post("/score", json=scam).json()
    assert body["decision"] in {"review", "block"}
    codes = {r["code"] for r in body["reasons"]}
    assert {"NEW_PAYEE", "AMOUNT_UNUSUAL"} <= codes
    assert set(body["features"]) >= {"amount_z", "new_payee"}
    assert body["latency_ms"] < 100


def test_score_fills_missing_timestamp(client: TestClient) -> None:
    payload = _payload()
    del payload["timestamp"]
    assert client.post("/score", json=payload).status_code == 200


@pytest.mark.parametrize(
    "bad",
    [{"amount_eur": -5}, {"channel": "bitcoin"}, {"country": "finland"}, {"surprise": 1}],
)
def test_invalid_payloads_are_rejected(client: TestClient, bad: dict[str, Any]) -> None:
    assert client.post("/score", json={**_payload(), **bad}).status_code == 422


def test_metrics_feed_and_stats_track_api_traffic(client: TestClient) -> None:
    client.post("/score", json=_payload())
    metrics = client.get("/metrics").text
    assert 'petosvahti_transactions_scored_total{decision="approve"}' in metrics
    assert "petosvahti_scoring_latency_ms_count 1" in metrics
    events = client.get("/api/events", params={"since": 0}).json()
    assert len(events) == 1 and events[0]["source"] == "api" and events[0]["label"] is None
    assert client.get("/api/events", params={"since": events[0]["seq"]}).json() == []
    stats = client.get("/api/stats").json()
    assert stats["scored"] == 1 and stats["customers_profiled"] == 1


def test_model_info(client: TestClient) -> None:
    info = client.get("/api/model").json()
    assert info["thresholds"] == {"review_from": 20.0, "block_above": 85.0}
    assert "NEW_PAYEE" in info["reason_codes"]


def test_simulator_endpoints_need_simulator(client: TestClient) -> None:
    assert client.post("/api/simulator/inject", json={"pattern": "app_scam"}).status_code == 409
    assert client.get("/api/scenarios").status_code == 409


def test_dashboard_is_served(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and "Petosvahti" in r.text


def test_live_simulator_streams_scores_and_injects(quick_model: FraudModel) -> None:
    settings = Settings(
        source="simulator", sim_customers=30, sim_history_days=2, sim_rate=200, auto_train=False
    )
    with TestClient(create_app(settings, model=quick_model)) as c:
        _wait_for(lambda: c.get("/health").json()["source"]["ready"])
        r = c.post("/api/simulator/inject", json={"pattern": "card_testing"})
        assert r.status_code == 200
        victim = r.json()["customer_id"]

        def attack_seen() -> bool:
            events = c.get("/api/events", params={"limit": 500}).json()
            return any(e["label"] == "card_testing" for e in events)

        _wait_for(attack_seen)
        events = c.get("/api/events", params={"limit": 500}).json()
        attack = [e for e in events if e["label"] == "card_testing"]
        assert all(e["transaction"]["customer_id"] == victim for e in attack)

        scenarios = c.get("/api/scenarios").json()
        assert set(scenarios["scenarios"]) == {"everyday", "app_scam", "account_takeover"}
        assert c.post("/api/simulator/control", json={"paused": True}).json()["paused"] is True
        assert c.post("/api/simulator/inject", json={"pattern": "nope"}).status_code == 422
