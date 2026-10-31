"""Kafka adapter [R22]: synthetic stream producer and scoring consumer.

Wire format on `petosvahti.transactions`: key = customer id (so one customer's
payments stay ordered within a partition, which the stateful feature store
relies on), value = `Transaction` JSON, headers:

- ``replay``: ``1`` for historical traffic that only warms customer profiles,
  ``0`` for live traffic to score;
- ``synthetic-label``: generator ground truth, used **only** for the demo's
  detection counters, never passed to the model.

Decisions are published to `petosvahti.decisions` as `ScoreResult` JSON.
`confluent-kafka` is an optional dependency (``pip install -e ".[stream]"``).
"""

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from pydantic import ValidationError

from petosvahti.config import Settings
from petosvahti.domain import HELSINKI, LabelledTransaction, Transaction
from petosvahti.generator import Simulator
from petosvahti.scoring.scorer import Scorer, ScoreResult

log = logging.getLogger(__name__)

REPLAY_HEADER = "replay"
LABEL_HEADER = "synthetic-label"
LEGIT = "legit"

Headers = Sequence[tuple[str, bytes | None]]


def encode(lt: LabelledTransaction, *, replay: bool) -> tuple[bytes, bytes, list[tuple[str, bytes]]]:  # fmt: skip
    tx = lt.transaction
    label = lt.fraud_pattern.value if lt.fraud_pattern else LEGIT
    headers = [(REPLAY_HEADER, b"1" if replay else b"0"), (LABEL_HEADER, label.encode())]
    return tx.customer_id.encode(), tx.model_dump_json().encode(), headers


def decode(value: bytes, headers: Headers | None) -> tuple[Transaction, str | None, bool]:
    meta = {k: (v or b"").decode() for k, v in headers or ()}
    return (
        Transaction.model_validate_json(value),
        meta.get(LABEL_HEADER),
        meta.get(REPLAY_HEADER) == "1",
    )


def run_producer(
    settings: Settings,
    *,
    history_days: int,
    rate: float,
    stop: threading.Event | None = None,
    echo: Callable[[str], None] = print,
) -> None:
    """Replay `history_days` of history as fast as possible, then stream live at `rate` tx/s."""
    from confluent_kafka import Producer

    topic = settings.kafka_transactions_topic
    producer = Producer(
        {"bootstrap.servers": settings.kafka_bootstrap, "linger.ms": 20, "client.id": "petosvahti-producer"}  # fmt: skip
    )
    now = datetime.now(HELSINKI)
    sim = Simulator(
        settings.sim_customers,
        settings.sim_seed,
        now - timedelta(days=history_days),
        settings.sim_fraud_per_1000_per_day,
    )

    def send(lt: LabelledTransaction, replay: bool) -> None:
        key, value, headers = encode(lt, replay=replay)
        while True:
            try:
                producer.produce(topic, value=value, key=key, headers=headers)
                break
            except BufferError:  # local queue full: let it drain
                producer.poll(0.1)
        producer.poll(0)

    history = sim.take_until(now)
    for lt in history:
        send(lt, True)
    producer.flush(60)
    echo(f"replayed {len(history):,} historical transactions to {topic}; streaming live at {rate}/s")

    stop = stop or threading.Event()
    sent = 0
    while not stop.is_set():
        send(next(sim), False)
        sent += 1
        if sent % 200 == 0:
            echo(f"sent {sent:,} live transactions (sim time {sim.clock:%Y-%m-%d %H:%M})")
        stop.wait(1.0 / rate)
    producer.flush(10)


@dataclass
class ConsumerStatus:
    connected: bool = False
    replayed: int = 0
    scored: int = 0
    rejected: int = 0
    last_error: str | None = None


def consume_and_score(
    scorer: Scorer,
    settings: Settings,
    on_scored: Callable[[Transaction, ScoreResult, str | None], None],
    stop: threading.Event,
    status: ConsumerStatus,
) -> None:
    """Blocking consume → score → publish loop (run it in a thread)."""
    from confluent_kafka import Consumer, KafkaError, Producer

    consumer = Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap,
            # Fresh group each start: replay the topic from the beginning to rebuild
            # in-memory profiles (the log is the source of truth).
            "group.id": f"petosvahti-scorer-{uuid4().hex[:8]}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap, "linger.ms": 5})
    consumer.subscribe([settings.kafka_transactions_topic])
    try:
        while not stop.is_set():
            msg = consumer.poll(0.5)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    status.last_error = str(msg.error())
                continue
            status.connected = True
            try:
                tx, label, replay = decode(msg.value(), msg.headers())
            except (ValidationError, UnicodeDecodeError) as exc:  # poison message: skip, count
                status.rejected += 1
                status.last_error = f"rejected message: {exc.__class__.__name__}"
                continue
            if replay:
                scorer.observe(tx)
                status.replayed += 1
                continue
            result = scorer.score(tx)
            status.scored += 1
            on_scored(tx, result, label)
            producer.produce(
                settings.kafka_decisions_topic,
                key=tx.customer_id.encode(),
                value=result.model_dump_json().encode(),
            )
            producer.poll(0)
    finally:
        consumer.close()
        producer.flush(5)
