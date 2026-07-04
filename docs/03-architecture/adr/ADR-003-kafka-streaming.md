# ADR-003: Apache Kafka for the streaming backbone

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: A. Abdulwasiu

## Context
"Real time" must be real: transactions should flow as events, decoupled from the scorer, with measurable lag. Kafka is the de facto event backbone in Nordic banking (used at Nordea and across the sector) — high CV value. But Kafka is operationally heavy for a solo laptop project.

## Decision
Apache Kafka, single broker in KRaft mode (no ZooKeeper), via Docker Compose. `confluent-kafka` Python client. One topic (`transactions.raw`) to start.

## Consequences
+ Authentic event-streaming experience: consumer groups, offsets, lag — the vocabulary Finnish fintech interviews use
+ KRaft single-broker keeps the footprint manageable
− Still the riskiest dependency (risk R2); mitigated by a spike in Sprint 3 and a file-replay fallback that implements the same producer/consumer interfaces
− No schema registry: JSON with a documented schema; drift discipline is manual

## Alternatives considered
- **Redpanda**: Kafka-API-compatible, single binary, easier ops — strong candidate; rejected only because operating *actual* Kafka is part of the learning goal. Fallback if R2 fires.
- **RabbitMQ**: queueing, not log semantics; weaker fit for replay + lag metrics.
- **File/loop replay**: zero infra, zero credibility as "real time"; retained as fallback interface.
