# Architecture Overview — Petosvahti

*Status: baseline v1.0 (2026-07-04). Updated at each sprint review; decisions recorded as ADRs.*

## 1. System context (C4 level 1)

```
                        ┌────────────────────────────────────┐
  Synthetic Finnish     │            PETOSVAHTI              │     Fraud analyst
  transaction sources ─▶│  real-time fraud scoring service   │───▶ (scores, decisions,
  (generator/replay)    │                                    │      reason codes)
                        └────────────────────────────────────┘
```

In a real deployment the "sources" would be a bank's payment switch (card authorisations, SEPA instant transfers, Siirto/MobilePay events). Here, a generator produces statistically Finnish-flavoured synthetic traffic.

## 2. Container view (C4 level 2)

```
┌ docker-compose ───────────────────────────────────────────────────────────┐
│                                                                           │
│  producer            Kafka (KRaft, 1 broker)          scoring-consumer    │
│  (tx generator) ───▶  topic: transactions.raw  ───▶   loads model,        │
│                                                       calls scoring core  │
│                                                            │              │
│                       FastAPI service ◀──── shared scoring core (lib)     │
│                       /score /health /metrics              │              │
│                            │                               ▼              │
│                            └────────────▶ PostgreSQL: scores, decisions   │
└───────────────────────────────────────────────────────────────────────────┘
```

Key idea: **the scoring logic is a plain Python library** (`src/petosvahti/scoring/`). Both the REST API (synchronous, request/response) and the Kafka consumer (asynchronous, streaming) are thin adapters around it. One model, two entry points — hexagonal-architecture thinking.

## 3. Scoring flow

1. Transaction arrives (HTTP body or Kafka message) — validated by Pydantic schema
2. Feature pipeline maps raw fields → model feature vector
3. Isolation Forest produces anomaly score, normalised to 0–100 risk
4. Decision policy applies thresholds: `< 60 approve`, `60–85 review`, `> 85 block` (tuned in S2.3)
5. Reason codes attached (top contributing features / rule hits)
6. Result persisted (PostgreSQL) and returned/published; structured log with correlation ID

## 4. Data model (initial)

`transactions_scored`: id (UUID) · ts (timestamptz) · channel (card|a2a|siirto|mobilepay) · amount_eur · merchant · payer_iban_masked · score · decision · reason_codes (jsonb) · model_version · latency_ms

## 5. Non-functional requirements

| NFR | Target | Verified in |
|---|---|---|
| Scoring latency | p99 < 100 ms (local) | S4.1, S5.3 |
| Throughput | ≥ 50 tx/s sustained | S5.2 |
| Reproducibility | model retrainable from seed, same metrics ±1 % | S2.2 |
| Auditability | every decision persisted with model version + reasons | S4.3 |
| Startability | one command, < 15 min on clean machine | S6.2 |

## 6. Technology choices

See ADRs: [ADR-001](adr/ADR-001-python-fastapi.md) Python + FastAPI · [ADR-002](adr/ADR-002-isolation-forest-baseline.md) Isolation Forest first · [ADR-003](adr/ADR-003-kafka-streaming.md) Kafka for streaming

## 7. Source layout (target)

```
src/petosvahti/
├── scoring/        # core: features, model wrapper, decision policy
├── api/            # FastAPI app
├── streaming/      # Kafka producer & consumer
├── datagen/        # Finnish synthetic transaction generator
└── persistence/    # DB models & repository
tests/              # mirrors src/
notebooks/          # EDA, evaluation (outputs stripped)
```

## 8. Deliberate simplifications

Single Kafka broker, no schema registry (documented JSON schema instead), no model registry (versioned artifact files), threshold-based decisions rather than a rules engine. Each is an honest trade-off for a 100-hour project — and each is called out so reviewers see the simplification was *chosen*, not overlooked.
