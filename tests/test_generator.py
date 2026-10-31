"""Synthetic Finnish stream: determinism, ordering, realism checks, fraud injection."""

from collections import Counter
from datetime import datetime, timedelta

import pytest

from petosvahti.domain import (
    HELSINKI,
    INSTANT_CHANNELS,
    Channel,
    FraudPattern,
    LabelledTransaction,
)
from petosvahti.generator import Simulator
from petosvahti.generator.finnish import iban_is_valid, synthetic_iban

START = datetime(2026, 9, 1, tzinfo=HELSINKI)


def _week(seed: int = 1, fraud: float = 20.0) -> list[LabelledTransaction]:
    sim = Simulator(200, seed=seed, start=START, fraud_incidents_per_1000_per_day=fraud)
    return sim.take_until(START + timedelta(days=7))


def test_same_seed_same_stream() -> None:
    a = [lt.transaction for lt in _week(seed=3)]
    b = [lt.transaction for lt in _week(seed=3)]
    assert a == b
    assert a != [lt.transaction for lt in _week(seed=4)]


def test_stream_is_time_ordered_and_in_window() -> None:
    stamps = [lt.transaction.timestamp for lt in _week()]
    assert stamps == sorted(stamps)
    assert stamps[0] >= START


def test_volume_rails_and_fraud_mix_are_plausible() -> None:
    week = _week()
    per_customer_day = len(week) / 200 / 7
    assert 2.0 < per_customer_day < 5.0
    channels = Counter(lt.transaction.channel for lt in week)
    assert channels.most_common(1)[0][0] is Channel.CARD
    assert set(channels) == set(Channel)
    patterns = Counter(lt.fraud_pattern for lt in week if lt.is_fraud)
    assert set(patterns) == set(FraudPattern)
    assert 0.001 < sum(patterns.values()) / len(week) < 0.05


def test_activity_follows_helsinki_daytime() -> None:
    hours = Counter(lt.transaction.timestamp.astimezone(HELSINKI).hour for lt in _week(fraud=0))
    assert hours[18] > 5 * hours[3]


def test_fraud_patterns_have_their_signatures() -> None:
    fraud = [lt for lt in _week(fraud=60.0) if lt.is_fraud]
    app = [lt.transaction for lt in fraud if lt.fraud_pattern is FraudPattern.APP_SCAM]
    cards = [lt.transaction for lt in fraud if lt.fraud_pattern is FraudPattern.CARD_TESTING]
    assert all(t.channel in INSTANT_CHANNELS and t.amount_eur >= 300 for t in app)
    assert all(t.channel is Channel.CARD and t.amount_eur <= 4.0 for t in cards)


def test_inject_starts_incident_for_named_victim() -> None:
    sim = Simulator(50, seed=9, start=START, fraud_incidents_per_1000_per_day=0)
    sim.take_until(START + timedelta(hours=6))
    victim = sim.inject(FraudPattern.ACCOUNT_TAKEOVER, "C00007")
    upcoming = [next(sim) for _ in range(40)]
    hijacked = [lt for lt in upcoming if lt.fraud_pattern is FraudPattern.ACCOUNT_TAKEOVER]
    assert victim == "C00007"
    assert hijacked
    assert all(lt.transaction.customer_id == "C00007" for lt in hijacked)


def test_inject_unknown_customer_raises() -> None:
    sim = Simulator(5, seed=1, start=START)
    with pytest.raises(KeyError):
        sim.inject(FraudPattern.APP_SCAM, "nobody")


def test_synthetic_ibans_are_valid_finnish_format() -> None:
    import random

    rng = random.Random(0)
    ibans = [synthetic_iban(rng) for _ in range(200)]
    assert all(len(i) == 18 and i.startswith("FI") and iban_is_valid(i) for i in ibans)
    assert not iban_is_valid("FI0079900000000000")
