"""Seeded, event-driven simulator of a Finnish retail-banking payment stream.

Each customer is an independent arrival process (diurnal Helsinki-time
profile, personal merchants, P2P friends, monthly rent); fraud incidents are a
separate Poisson process that hijacks a random victim. Everything runs on a
simulated clock, so the same object serves both offline training data
(`take_until`) and the live demo stream (`next()` paced by the caller).
"""

import heapq
import itertools
import math
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from petosvahti.domain import (
    HELSINKI,
    HOME_COUNTRY,
    Channel,
    FraudPattern,
    LabelledTransaction,
    Transaction,
)
from petosvahti.generator import finnish as fi

# Relative activity per Helsinki hour 00..23: quiet nights, lunch and evening peaks.
HOUR_WEIGHTS = (
    0.15, 0.08, 0.05, 0.04, 0.05, 0.12, 0.35, 0.70, 0.90, 1.00, 1.05, 1.20,
    1.40, 1.20, 1.05, 1.10, 1.30, 1.50, 1.60, 1.40, 1.10, 0.80, 0.50, 0.30,
)  # fmt: skip
_W_MAX = max(HOUR_WEIGHTS)
_W_MEAN = sum(HOUR_WEIGHTS) / len(HOUR_WEIGHTS)

PATTERN_MIX = (
    (FraudPattern.APP_SCAM, 0.40),
    (FraudPattern.ACCOUNT_TAKEOVER, 0.35),
    (FraudPattern.CARD_TESTING, 0.25),
)

DAY = 86_400.0


@dataclass(frozen=True, slots=True)
class Payee:
    payee_id: str
    name: str
    channel: Channel
    median_eur: float
    country: str = HOME_COUNTRY


@dataclass(slots=True)
class Customer:
    customer_id: str
    city: str
    devices: list[str]
    spend_factor: float
    tx_per_day: float
    merchants: tuple[Payee, ...]
    merchant_weights: tuple[float, ...]
    friends: tuple[Payee, ...]
    landlord: Payee
    rent_day: int
    trip: tuple[float, float, str, tuple[str, ...]] | None


@dataclass(order=True, slots=True)
class _Event:
    at: float
    seq: int
    kind: str = field(compare=False)  # legit | rent | incident | ready
    customer: int = field(compare=False, default=-1)
    ready: LabelledTransaction | None = field(compare=False, default=None)


class Simulator:
    """Infinite, time-ordered stream of labelled synthetic transactions.

    Args:
        n_customers: Population size.
        seed: RNG seed; same seed + start → identical stream.
        start: Simulated clock origin (default: now, Helsinki).
        fraud_incidents_per_1000_per_day: Background fraud rate. One incident is
            1-14 transactions depending on the pattern.
    """

    def __init__(
        self,
        n_customers: int = 500,
        seed: int = 2026,
        start: datetime | None = None,
        fraud_incidents_per_1000_per_day: float = 3.5,
    ) -> None:
        if n_customers < 1:
            raise ValueError("n_customers must be >= 1")
        self._rng = random.Random(seed)
        self._start = (start or datetime.now(HELSINKI)).timestamp()
        self._clock = self._start
        self._seq = itertools.count()
        self._heap: list[_Event] = []
        self._lock = threading.Lock()
        self._incident_rate = fraud_incidents_per_1000_per_day * n_customers / 1000 / DAY
        self.customers = [self._make_customer(i) for i in range(n_customers)]
        for i in range(n_customers):
            self._push(self._next_legit_time(self.customers[i], self._start), "legit", i)
            self._push(self._next_rent_time(self.customers[i], self._start), "rent", i)
        if self._incident_rate > 0:
            self._push(self._start + self._rng.expovariate(self._incident_rate), "incident")

    # -- public API -------------------------------------------------------

    @property
    def clock(self) -> datetime:
        """Simulated time of the most recently emitted event."""
        return datetime.fromtimestamp(self._clock, HELSINKI)

    def __iter__(self) -> "Simulator":
        return self

    def __next__(self) -> LabelledTransaction:
        with self._lock:
            return self._next_locked()

    def take_until(self, end: datetime) -> list[LabelledTransaction]:
        """Drain every transaction with timestamp <= `end` (bulk/offline use)."""
        limit = end.timestamp()
        out: list[LabelledTransaction] = []
        with self._lock:
            while self._heap[0].at <= limit:
                out.append(self._next_locked())
        return out

    def inject(self, pattern: FraudPattern, customer_id: str | None = None) -> str:
        """Start a fraud incident right now (demo button). Returns the victim id."""
        with self._lock:
            if customer_id is None:
                idx = self._rng.randrange(len(self.customers))
            else:
                idx = next(
                    (i for i, c in enumerate(self.customers) if c.customer_id == customer_id),
                    -1,
                )
                if idx < 0:
                    raise KeyError(customer_id)
            self._push_incident(pattern, idx, self._clock + 1.0, shift_time=False)
            return self.customers[idx].customer_id

    # -- event loop -------------------------------------------------------

    def _push(self, at: float, kind: str, customer: int = -1, ready: LabelledTransaction | None = None) -> None:  # fmt: skip
        heapq.heappush(self._heap, _Event(at, next(self._seq), kind, customer, ready))

    def _next_locked(self) -> LabelledTransaction:
        while True:
            ev = heapq.heappop(self._heap)
            self._clock = max(self._clock, ev.at)
            if ev.kind == "ready":
                assert ev.ready is not None
                return ev.ready
            if ev.kind == "legit":
                customer = self.customers[ev.customer]
                self._push(self._next_legit_time(customer, ev.at), "legit", ev.customer)
                return LabelledTransaction(self._legit_tx(customer, ev.at))
            if ev.kind == "rent":
                customer = self.customers[ev.customer]
                self._push(self._next_rent_time(customer, ev.at), "rent", ev.customer)
                return LabelledTransaction(self._rent_tx(customer, ev.at))
            # incident
            pattern = self._rng.choices(
                [p for p, _ in PATTERN_MIX], weights=[w for _, w in PATTERN_MIX]
            )[0]
            self._push_incident(pattern, self._rng.randrange(len(self.customers)), ev.at)
            self._push(ev.at + self._rng.expovariate(self._incident_rate), "incident")

    # -- population -------------------------------------------------------

    def _make_customer(self, i: int) -> Customer:
        rng = self._rng
        city = rng.choice(fi.CITIES)
        chains = rng.sample(fi.EVERYDAY_CHAINS, k=rng.randint(8, 14))
        merchants = tuple(
            Payee(
                fi.slug(f"{m.name} {city}" if m.local else m.name),
                f"{m.name} {city}" if m.local else m.name,
                m.channel,
                m.median_eur,
            )
            for m in chains
        )
        friends = tuple(
            Payee(
                fi.synthetic_iban(rng),
                fi.person_name(rng),
                Channel.MOBILEPAY if rng.random() < 0.7 else Channel.SIIRTO,
                25.0,
            )
            for _ in range(rng.randint(2, 6))
        )
        landlord_name = (
            f"As Oy {city}n {rng.choice(fi.LAST_NAMES)}la"
            if rng.random() < 0.5
            else rng.choice(("SATO Oyj", "Lumo Kodit", "VVO Vuokra", "Avara Asunnot"))
        )
        trip = None
        if rng.random() < 0.10:
            begin = self._start + rng.uniform(0, 60) * DAY
            country, places = rng.choice(fi.TRAVEL)
            trip = (begin, begin + rng.uniform(3, 7) * DAY, country, places)
        return Customer(
            customer_id=f"C{i:05d}",
            city=city,
            devices=[f"dev-{rng.getrandbits(40):010x}" for _ in range(1 if rng.random() < 0.6 else 2)],  # fmt: skip
            spend_factor=rng.lognormvariate(0.0, 0.35),
            tx_per_day=rng.uniform(1.5, 6.0),
            merchants=merchants,
            merchant_weights=tuple(1 / (k + 1) ** 0.8 for k in range(len(merchants))),
            friends=friends,
            landlord=Payee(fi.synthetic_iban(rng), landlord_name, Channel.ONLINE_BANK, 850.0),
            rent_day=rng.randint(1, 28),
            trip=trip,
        )

    def _next_legit_time(self, c: Customer, after: float) -> float:
        # Thinning of a homogeneous Poisson process by the hour-of-day profile.
        peak_rate = c.tx_per_day * _W_MAX / _W_MEAN / DAY
        t = after
        while True:
            t += self._rng.expovariate(peak_rate)
            hour = datetime.fromtimestamp(t, HELSINKI).hour
            if self._rng.random() < HOUR_WEIGHTS[hour] / _W_MAX:
                return t

    def _next_rent_time(self, c: Customer, after: float) -> float:
        now = datetime.fromtimestamp(after, HELSINKI)
        due = now.replace(day=c.rent_day, hour=8, minute=0, second=0, microsecond=0)
        if due.timestamp() <= after:
            month = now.month % 12 + 1
            due = due.replace(year=now.year + (now.month == 12), month=month)
        return due.timestamp() + self._rng.uniform(0, 4 * 3600)

    # -- legit behaviour --------------------------------------------------

    def _amount(self, median: float, sigma: float, factor: float = 1.0) -> float:
        value = self._rng.lognormvariate(math.log(median * factor), sigma)
        return round(min(max(value, 0.5), 50_000.0), 2)

    def _device(self, c: Customer) -> str:
        rng = self._rng
        if rng.random() < 0.002:  # customer gets a new phone
            c.devices.append(f"dev-{rng.getrandbits(40):010x}")
            return c.devices[-1]
        if len(c.devices) > 1 and rng.random() < 0.15:
            return rng.choice(c.devices)
        return c.devices[0]

    def _tx(
        self, c: Customer, at: float, payee: Payee, amount: float, device: str, channel: Channel | None = None  # fmt: skip
    ) -> Transaction:
        return Transaction(
            transaction_id=f"{self._rng.getrandbits(64):016x}",
            customer_id=c.customer_id,
            timestamp=datetime.fromtimestamp(at, HELSINKI),
            amount_eur=amount,
            channel=channel or payee.channel,
            payee_id=payee.payee_id,
            payee_name=payee.name,
            country=payee.country,
            device_id=device,
        )

    def _legit_tx(self, c: Customer, at: float) -> Transaction:
        rng = self._rng
        r = rng.random()
        if c.trip and c.trip[0] <= at < c.trip[1] and r < 0.85:
            _, _, country, places = c.trip
            name = rng.choice(places)
            payee = Payee(fi.slug(name), name, Channel.CARD, 25.0, country)
            return self._tx(c, at, payee, self._amount(25.0, 0.8, c.spend_factor), c.devices[0])
        if r < 0.70:
            payee = rng.choices(c.merchants, weights=c.merchant_weights)[0]
            amount = self._amount(payee.median_eur, 0.6, c.spend_factor)
        elif r < 0.80:  # somewhere new — the commonest legit "new payee"
            chain = rng.choice(fi.EVERYDAY_CHAINS)
            name = f"{chain.name} {rng.choice(fi.CITIES)}"
            payee = Payee(fi.slug(name), name, chain.channel, chain.median_eur)
            amount = self._amount(chain.median_eur, 0.6, c.spend_factor)
        elif r < 0.92:
            payee = rng.choice(c.friends)
            amount = self._amount(25.0, 0.8)
        elif r < 0.95:  # buying something second-hand from a stranger (Tori.fi style)
            payee = Payee(fi.synthetic_iban(rng), fi.person_name(rng), Channel.MOBILEPAY, 40.0)
            amount = self._amount(40.0, 0.8)
        elif r < 0.965:
            chain = rng.choice(fi.BIG_TICKET_CHAINS)
            name = f"{chain.name} {c.city}" if chain.local else chain.name
            payee = Payee(fi.slug(name), name, chain.channel, chain.median_eur)
            amount = self._amount(chain.median_eur, 0.5)
        elif r < 0.975:  # helping family out: large instant transfer to a known person
            friend = rng.choice(c.friends)
            payee = Payee(friend.payee_id, friend.name, Channel.SEPA_INSTANT, 400.0)
            amount = self._amount(400.0, 0.6)
        else:
            payee = c.merchants[0]
            amount = self._amount(payee.median_eur, 0.6, c.spend_factor)
        return self._tx(c, at, payee, amount, self._device(c))

    def _rent_tx(self, c: Customer, at: float) -> Transaction:
        amount = round(c.landlord.median_eur * c.spend_factor**0.5, 2)
        return self._tx(c, at, c.landlord, amount, c.devices[0])

    # -- fraud ------------------------------------------------------------

    def _shift_to_window(self, at: float, start_hour: int, end_hour: int) -> float:
        """Move `at` forward to a random moment in the next [start_hour, end_hour) window."""
        day = datetime.fromtimestamp(at, HELSINKI).replace(hour=0, minute=0, second=0, microsecond=0)  # fmt: skip
        for offset in range(3):
            base = day + timedelta(days=offset)
            lo = base.replace(hour=start_hour).timestamp()
            hi = base.replace(hour=end_hour).timestamp()
            if hi > at:
                return self._rng.uniform(max(lo, at), hi)
        return at

    def _push_incident(self, pattern: FraudPattern, idx: int, at: float, shift_time: bool = True) -> None:  # fmt: skip
        rng = self._rng
        c = self.customers[idx]
        txs: list[tuple[float, Transaction]] = []
        if pattern is FraudPattern.APP_SCAM:
            # Victim is talked into paying a "safe account" from their own phone.
            if shift_time and rng.random() < 0.6:
                at = self._shift_to_window(at, 17, 22)
            mule = Payee(fi.synthetic_iban(rng), fi.person_name(rng), Channel.SIIRTO, 2500.0)
            channel = Channel.SIIRTO if rng.random() < 0.5 else Channel.SEPA_INSTANT
            for _ in range(rng.choice((1, 1, 2, 3))):
                amount = min(max(self._amount(2500.0, 0.6), 300.0), 15_000.0)
                txs.append((at, self._tx(c, at, mule, amount, c.devices[0], channel)))
                at += rng.uniform(180, 1200)
        elif pattern is FraudPattern.ACCOUNT_TAKEOVER:
            # Stolen credentials used from the fraudster's own device, often at night.
            if shift_time and rng.random() < 0.5:
                at = self._shift_to_window(at, 0, 5)
            country = rng.choice(fi.FRAUD_COUNTRIES) if rng.random() < 0.6 else HOME_COUNTRY
            mule = Payee(fi.synthetic_iban(rng), fi.person_name(rng), Channel.SEPA_INSTANT, 1500.0, country)  # fmt: skip
            device = f"dev-{rng.getrandbits(40):010x}"
            channel = Channel.SEPA_INSTANT if rng.random() < 0.6 else Channel.ONLINE_BANK
            for _ in range(rng.randint(1, 4)):
                amount = min(max(self._amount(1500.0, 0.7), 150.0), 12_000.0)
                txs.append((at, self._tx(c, at, mule, amount, device, channel)))
                at += rng.uniform(60, 360)
        else:
            # Card testing: a script validates a stolen card with tiny CNP charges.
            country = rng.choice(fi.FRAUD_COUNTRIES) if rng.random() < 0.7 else HOME_COUNTRY
            device = f"web-{rng.getrandbits(40):010x}"
            for _ in range(rng.randint(5, 14)):
                name = f"webshop-{rng.randrange(10_000):04d}"
                shop = Payee(name, name, Channel.CARD, 2.0, country)
                amount = round(rng.uniform(0.5, 4.0), 2)
                txs.append((at, self._tx(c, at, shop, amount, device)))
                at += rng.uniform(10, 60)
        for when, tx in txs:
            self._push(when, "ready", ready=LabelledTransaction(tx, pattern))
