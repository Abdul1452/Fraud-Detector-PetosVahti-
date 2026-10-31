"""Stateful, per-customer feature extraction.

Most fraud signals are relative to the customer's own history ("first payment
to this payee", "ten times their usual amount"), so features come from a small
in-memory profile store. The same code builds the training matrix and serves
online requests, which rules out train/serve skew in feature logic.

Learning policy: every attempt counts towards velocity, but only transactions
the caller marks as trusted (`learn=True`, i.e. approved) extend the profile.
Otherwise a blocked transfer would teach the store that the mule's IBAN is a
"known payee" and make the fraudster's second attempt look normal.
"""

import math
from collections import deque
from dataclasses import dataclass, field

from petosvahti.domain import HELSINKI, HOME_COUNTRY, INSTANT_CHANNELS, Transaction

FEATURE_NAMES: tuple[str, ...] = (
    "log_amount",
    "amount_z",
    "new_payee",
    "new_device",
    "new_country",
    "night",
    "instant_rail",
    "tx_count_1h",
    "log_amount_24h",
    "log_secs_since_last",
)

MIN_HISTORY = 5  # learned transactions before the personal amount profile is trusted
POPULATION_LOG_MEAN = math.log1p(30.0)  # cold-start prior: a typical ~€30 purchase
POPULATION_LOG_STD = 1.0
MIN_LOG_STD = 0.5
HOUR = 3600.0
DAY = 86_400.0
MAX_GAP = 30 * DAY

FeatureVector = tuple[float, ...]


@dataclass(slots=True)
class CustomerProfile:
    recent: deque[tuple[float, float]] = field(default_factory=deque)  # (epoch s, EUR), 24 h
    last_ts: float | None = None
    n: int = 0
    mean_log: float = 0.0
    m2_log: float = 0.0  # Welford running sum of squares of log-amount
    payees: set[str] = field(default_factory=set)
    devices: set[str] = field(default_factory=set)
    countries: set[str] = field(default_factory=lambda: {HOME_COUNTRY})


class FeatureStore:
    """Per-customer profiles. Not thread-safe; the `Scorer` serialises access."""

    def __init__(self) -> None:
        self._profiles: dict[str, CustomerProfile] = {}

    def __len__(self) -> int:
        return len(self._profiles)

    def __contains__(self, customer_id: object) -> bool:
        return customer_id in self._profiles

    def extract(self, tx: Transaction) -> FeatureVector:
        """Features of `tx` against history *before* it. Does not mutate state."""
        p = self._profiles.get(tx.customer_id) or CustomerProfile()
        ts = tx.timestamp.timestamp()
        log_amount = math.log1p(tx.amount_eur)

        if p.n >= MIN_HISTORY:
            std = max(math.sqrt(p.m2_log / (p.n - 1)), MIN_LOG_STD)
            amount_z = (log_amount - p.mean_log) / std
        else:
            amount_z = (log_amount - POPULATION_LOG_MEAN) / POPULATION_LOG_STD

        count_1h = 0
        sum_24h = 0.0
        for when, amount in p.recent:
            if when <= ts:
                if ts - when <= HOUR:
                    count_1h += 1
                if ts - when <= DAY:
                    sum_24h += amount

        gap = MAX_GAP if p.last_ts is None else min(max(ts - p.last_ts, 0.0), MAX_GAP)
        hour = tx.timestamp.astimezone(HELSINKI).hour

        return (
            log_amount,
            min(max(amount_z, -5.0), 10.0),
            float(tx.payee_id not in p.payees),
            float(tx.device_id not in p.devices),
            float(tx.country not in p.countries),
            float(hour < 6),
            float(tx.channel in INSTANT_CHANNELS),
            float(min(count_1h, 50)),
            math.log1p(sum_24h),
            math.log1p(gap),
        )

    def update(self, tx: Transaction, *, learn: bool = True) -> None:
        """Record `tx`; extend the trusted profile only when `learn` is set."""
        p = self._profiles.get(tx.customer_id)
        if p is None:
            p = self._profiles[tx.customer_id] = CustomerProfile()
        ts = tx.timestamp.timestamp()
        p.recent.append((ts, tx.amount_eur))
        newest = max(ts, p.recent[-1][0], p.last_ts or ts)
        while p.recent and newest - p.recent[0][0] > DAY:
            p.recent.popleft()
        p.last_ts = newest
        if learn:
            log_amount = math.log1p(tx.amount_eur)
            p.n += 1
            delta = log_amount - p.mean_log
            p.mean_log += delta / p.n
            p.m2_log += delta * (log_amount - p.mean_log)
            p.payees.add(tx.payee_id)
            p.devices.add(tx.device_id)
            p.countries.add(tx.country)

    def extract_and_update(self, tx: Transaction, *, learn: bool = True) -> FeatureVector:
        features = self.extract(tx)
        self.update(tx, learn=learn)
        return features


def as_dict(features: FeatureVector) -> dict[str, float]:
    return dict(zip(FEATURE_NAMES, features, strict=True))
