"""Per-customer feature store: novelty, velocity, amount profile, learning policy."""

from datetime import timedelta

from conftest import make_tx
from petosvahti.domain import Channel
from petosvahti.scoring.features import FEATURE_NAMES, FeatureStore, as_dict
from petosvahti.scoring.reasons import active_codes, base_rates, explain


def _history(store: FeatureStore, n: int = 10) -> None:
    base = make_tx()
    for i in range(n):
        store.update(make_tx(timestamp=base.timestamp - timedelta(days=n - i), amount_eur=20.0 + i))


def test_vector_matches_feature_names() -> None:
    assert len(FeatureStore().extract(make_tx())) == len(FEATURE_NAMES)


def test_extract_does_not_mutate() -> None:
    store = FeatureStore()
    store.extract(make_tx())
    assert "C1" not in store


def test_known_customer_known_payee_looks_normal() -> None:
    store = FeatureStore()
    _history(store)
    f = as_dict(store.extract(make_tx()))
    assert f["new_payee"] == 0 and f["new_device"] == 0 and f["new_country"] == 0
    assert abs(f["amount_z"]) < 2
    assert active_codes(store.extract(make_tx())) == []


def test_novel_large_instant_transfer_lights_up() -> None:
    store = FeatureStore()
    _history(store)
    tx = make_tx(
        amount_eur=4800.0,
        channel=Channel.SIIRTO,
        payee_id="FI00mule",
        payee_name="Mule",
        device_id="dev-new",
        country="NL",
    )
    f = as_dict(store.extract(tx))
    assert f["new_payee"] == f["new_device"] == f["new_country"] == f["instant_rail"] == 1
    assert f["amount_z"] > 5
    assert f["instant_new_payee_log_amount"] > 8
    codes = set(active_codes(store.extract(tx)))
    assert {
        "AMOUNT_UNUSUAL",
        "NEW_PAYEE",
        "NEW_DEVICE",
        "NEW_COUNTRY",
        "INSTANT_HIGH_VALUE",
    } <= codes


def test_velocity_counts_attempts_in_last_hour() -> None:
    store = FeatureStore()
    t0 = make_tx().timestamp
    for i in range(4):
        store.update(make_tx(timestamp=t0 + timedelta(seconds=30 * i), payee_id=f"shop-{i}"))
    f = as_dict(store.extract(make_tx(timestamp=t0 + timedelta(minutes=3), payee_id="shop-x")))
    assert f["tx_count_1h"] == 4
    assert f["new_payees_1h"] == 4
    later = as_dict(store.extract(make_tx(timestamp=t0 + timedelta(hours=2))))
    assert later["tx_count_1h"] == 0


def test_blocked_payment_does_not_teach_payee() -> None:
    store = FeatureStore()
    _history(store)
    mule = make_tx(payee_id="FI00mule", payee_name="Mule")
    store.update(mule, learn=False)
    later = mule.model_copy(update={"timestamp": mule.timestamp + timedelta(days=3)})
    assert as_dict(store.extract(later))["new_payee"] == 1


def test_beneficiary_cooling_off() -> None:
    store = FeatureStore()
    first = make_tx(payee_id="FI00friend")
    store.update(first, learn=True)
    soon = first.model_copy(update={"timestamp": first.timestamp + timedelta(minutes=10)})
    next_day = first.model_copy(update={"timestamp": first.timestamp + timedelta(hours=25)})
    assert as_dict(store.extract(soon))["new_payee"] == 1
    assert as_dict(store.extract(next_day))["new_payee"] == 0


def test_night_uses_helsinki_local_time() -> None:
    # 01:30 UTC on 1 Oct 2026 is 04:30 in Helsinki (EEST, UTC+3).
    from datetime import UTC, datetime

    tx = make_tx(timestamp=datetime(2026, 10, 1, 1, 30, tzinfo=UTC))
    assert as_dict(FeatureStore().extract(tx))["night"] == 1


def test_reasons_rank_rarest_first() -> None:
    store = FeatureStore()
    _history(store)
    tx = make_tx(payee_id="new-shop", device_id="dev-new")
    rates = {"NEW_PAYEE": 0.1, "NEW_DEVICE": 0.001}
    assert [r.code for r in explain(store.extract(tx), rates)] == ["NEW_DEVICE", "NEW_PAYEE"]
    smoothed = base_rates([store.extract(tx)] * 3)
    assert smoothed["NEW_PAYEE"] == (3 + 1) / (3 + 2)
