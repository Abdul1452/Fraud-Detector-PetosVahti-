# Petosvahti 🇫🇮

**Real-time transaction fraud detection for the Finnish payments market.**

Petosvahti (*Finnish: "fraud guard"*) is a Stripe Radar-style fraud detection service: transactions stream through Kafka, an ML anomaly-detection model scores each one for fraud risk in real time, and a FastAPI service exposes the scores with explanations.

> Portfolio & learning project by [Abdullahi Olamilekan Abdulwasiu](https://github.com/Abdul1452) — Software Engineering & Project Management, Turku UAS. Run with the documentation and governance discipline of a real Finnish enterprise (Nordea/Wärtsilä-style).

## Why Finland?

- **PSD3/PSR (agreed 2025–2026)** shifts liability for authorised push payment (APP) fraud onto payment service providers that fail to meet detection standards — real-time fraud scoring is becoming a regulatory necessity, not a nice-to-have.
- **SEPA Instant Payments Regulation**: since October 2025 all euro-area banks must send/receive instant credit transfers (≤10 s). Instant money means instant fraud — batch detection is obsolete.
- Finland's payment mix is distinctive: online bank transfers dominate e-commerce, Siirto (OP + Nordea joint venture) handles phone-number-based instant payments, and Vipps MobilePay is ubiquitous for P2P.

## What it does

```
Synthetic Finnish transaction stream ──▶ Kafka ──▶ Scoring consumer ──▶ Risk score + decision
   (EUR, FI IBANs, Siirto/MobilePay/card,              │
    Finnish merchants, Europe/Helsinki time)           ▼
                                              FastAPI  /score  /health  /metrics
```

- **Model**: Isolation Forest baseline (trained on the Kaggle credit-card fraud dataset), autoencoder as stretch goal
- **Serving**: FastAPI, Dockerised, < 100 ms p99 scoring latency target
- **Streaming**: Kafka replay of synthetic Finnish transactions at realistic rates
- **Decisions**: `approve` / `review` / `block` with score thresholds and reason codes

## Tech stack

Python 3.12 · scikit-learn · FastAPI · Apache Kafka · PostgreSQL · Docker Compose · pytest · GitHub Actions

## Repository map

| Path | Contents |
|---|---|
| `docs/00-docs-strategy.md` | Where every document lives (GitHub vs Google Drive) |
| `docs/01-governance/` | Project charter, business case, risk register |
| `docs/02-planning/` | Product backlog, sprint plan, ways of working |
| `docs/03-architecture/` | Architecture overview + ADRs (decision log) |
| `docs/04-compliance/` | Finnish/EU regulatory context (PSD2/PSD3, IPR, AI Act, GDPR) |
| `src/` | Application code *(created from Sprint 1)* |
| `tests/` | Test suite |
| `notebooks/` | EDA and model experiments |

## Project status

| Sprint | Dates | Goal | Status |
|---|---|---|---|
| 0 | Week 1 | Governance, repo, environment | 🔄 |
| 1 | Weeks 2–3 | EDA + baseline model | ⬜ |
| 2 | Weeks 4–5 | Training pipeline + Finnish data generator | ⬜ |
| 3 | Weeks 6–7 | FastAPI scoring service | ⬜ |
| 4 | Weeks 8–9 | Kafka real-time streaming | ⬜ |
| 5 | Week 10 | Hardening, metrics dashboard, demo | ⬜ |

## Getting started

```bash
git clone https://github.com/Abdul1452/petosvahti.git
cd petosvahti
# full setup instructions land in Sprint 0
```

## License

MIT
