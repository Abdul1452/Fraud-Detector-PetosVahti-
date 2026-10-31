"""Background transaction sources feeding the scorer: in-process simulator or Kafka."""

import logging
import random
import threading
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, Protocol

from petosvahti.api.feed import LEGIT, Feed
from petosvahti.config import Settings
from petosvahti.domain import HELSINKI, Channel, FraudPattern, Transaction
from petosvahti.generator import Simulator
from petosvahti.generator import finnish as fi
from petosvahti.scoring.scorer import Scorer, ScoreResult
from petosvahti.streaming.kafka import ConsumerStatus, consume_and_score

log = logging.getLogger(__name__)


class StreamSource(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def status(self) -> dict[str, Any]: ...
    def clock(self) -> datetime: ...


class SimulatorSource:
    """Warms profiles from simulated history, then streams live at `rate` tx/s."""

    def __init__(self, scorer: Scorer, feed: Feed, settings: Settings) -> None:
        self._scorer = scorer
        self._feed = feed
        self._sim = Simulator(
            settings.sim_customers,
            settings.sim_seed,
            datetime.now(HELSINKI) - timedelta(days=settings.sim_history_days),
            settings.sim_fraud_per_1000_per_day,
        )
        self.rate = settings.sim_rate
        self.ready = False
        self.warmed = 0
        self._stop = threading.Event()
        self._running = threading.Event()
        self._running.set()
        self._rng = random.Random()
        self._thread = threading.Thread(target=self._run, name="petosvahti-simulator", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._running.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        for lt in self._sim.take_until(datetime.now(HELSINKI)):
            if self._stop.is_set():
                return
            self._scorer.observe(lt.transaction)
            self.warmed += 1
        self.ready = True
        log.info("simulator warmed %d customers with %d transactions", len(self._scorer.store), self.warmed)  # fmt: skip
        while not self._stop.is_set():
            if not self._running.is_set():
                self._running.wait(0.5)
                continue
            lt = next(self._sim)
            result = self._scorer.score(lt.transaction)
            label = lt.fraud_pattern.value if lt.fraud_pattern else LEGIT
            self._feed.add(lt.transaction, result, "stream", label)
            self._stop.wait(1.0 / self.rate)

    # -- controls ---------------------------------------------------------

    def set_paused(self, paused: bool) -> None:
        if paused:
            self._running.clear()
        else:
            self._running.set()

    def inject(self, pattern: FraudPattern, customer_id: str | None = None) -> str:
        return self._sim.inject(pattern, customer_id)

    def clock(self) -> datetime:
        return self._sim.clock

    def status(self) -> dict[str, Any]:
        return {
            "kind": "simulator",
            "ready": self.ready,
            "warmed": self.warmed,
            "paused": not self._running.is_set(),
            "rate": self.rate,
            "customers": len(self._sim.customers),
            "sim_time": self._sim.clock.isoformat(timespec="seconds"),
        }

    def scenarios(self, customer_id: str | None = None) -> dict[str, Any]:
        """Ready-made payloads for one real simulated customer (dashboard "try it")."""
        customers = self._sim.customers
        c = next((x for x in customers if x.customer_id == customer_id), None)
        if c is None:
            c = self._rng.choice(customers)
        at = self._sim.clock + timedelta(seconds=1)
        shop = c.merchants[0]
        stranger = fi.person_name(self._rng)
        return {
            "customer_id": c.customer_id,
            "city": c.city,
            "scenarios": {
                "everyday": {
                    "label": "Everyday purchase",
                    "description": f"Their usual shop ({shop.name}), usual amount, own phone.",
                    "transaction": Transaction(
                        customer_id=c.customer_id,
                        timestamp=at,
                        amount_eur=round(shop.median_eur * c.spend_factor, 2),
                        channel=shop.channel,
                        payee_id=shop.payee_id,
                        payee_name=shop.name,
                        device_id=c.devices[0],
                    ),
                },
                "app_scam": {
                    "label": "\"Safe account\" scam",
                    "description": "Customer is phoned by a fake bank officer and sends "
                    "€4 800 by Siirto to a stranger — from their own phone.",
                    "transaction": Transaction(
                        customer_id=c.customer_id,
                        timestamp=at,
                        amount_eur=4800.0,
                        channel=Channel.SIIRTO,
                        payee_id=fi.synthetic_iban(self._rng),
                        payee_name=stranger,
                        device_id=c.devices[0],
                    ),
                },
                "account_takeover": {
                    "label": "Account takeover",
                    "description": "Stolen credentials used from an unknown device abroad: "
                    "€2 900 SEPA Instant to a new IBAN.",
                    "transaction": Transaction(
                        customer_id=c.customer_id,
                        timestamp=at,
                        amount_eur=2900.0,
                        channel=Channel.SEPA_INSTANT,
                        payee_id=fi.synthetic_iban(self._rng),
                        payee_name=fi.person_name(self._rng),
                        country="NL",
                        device_id=f"dev-{self._rng.getrandbits(40):010x}",
                    ),
                },
            },
        }


class KafkaSource:
    """Consumes `petosvahti.transactions`, scores, publishes `petosvahti.decisions`."""

    def __init__(self, scorer: Scorer, feed: Feed, settings: Settings) -> None:
        self._scorer = scorer
        self._feed = feed
        self._settings = settings
        self._status = ConsumerStatus()
        self._stop = threading.Event()
        self._last_seen: datetime | None = None
        self._thread = threading.Thread(target=self._run, name="petosvahti-kafka", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)

    def _on_scored(self, tx: Transaction, result: ScoreResult, label: str | None) -> None:
        self._last_seen = tx.timestamp
        self._feed.add(tx, result, "stream", label)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                consume_and_score(self._scorer, self._settings, self._on_scored, self._stop, self._status)  # fmt: skip
            except Exception as exc:  # broker down, etc. — keep the API alive and retry
                self._status.connected = False
                self._status.last_error = f"{exc.__class__.__name__}: {exc}"
                log.warning("kafka consumer failed, retrying in 5 s: %s", exc)
                self._stop.wait(5.0)

    def clock(self) -> datetime:
        return self._last_seen or datetime.now(HELSINKI)

    def status(self) -> dict[str, Any]:
        return {
            "kind": "kafka",
            "ready": self._status.connected,
            "bootstrap": self._settings.kafka_bootstrap,
            "topic": self._settings.kafka_transactions_topic,
            **asdict(self._status),
        }
