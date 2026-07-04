# Product Backlog — Petosvahti

The backlog is organised as **epics → user stories → tasks**. Stories live as GitHub Issues (labels: `epic:E1`…`epic:E7`, `sprint:N`, `icebox`); this document defines the epics and the initial story set. Estimation in story points (1, 2, 3, 5, 8 — Fibonacci).

**Personas** used in stories:
- *Riikka* — fraud analyst at a Finnish bank (consumes scores & reasons)
- *Dev* — integrating engineer (consumes the API)
- *PM* — the project's own management viewpoint (docs, evidence)

## Epics

| Epic | Name | Outcome |
|---|---|---|
| E1 | Project foundation | Repo, environment, CI, governance docs |
| E2 | Data understanding & baseline model | Evaluated Isolation Forest on Kaggle data |
| E3 | Finnish synthetic data | Realistic localised transaction stream |
| E4 | Scoring service | Production-style FastAPI + decisions |
| E5 | Real-time streaming | Kafka replay & scoring consumer |
| E6 | Observability & hardening | Metrics, load behaviour, docs polish |
| E7 | Compliance & closure | Regulatory notes, demo, final report |

## Stories

### E1 — Project foundation (Sprint 0)
| ID | Story | Pts |
|---|---|---|
| S1.1 | As PM, I have the governance doc set (charter, business case, risk register, backlog, ways of working) committed, so the project starts like a real one | 3 |
| S1.2 | As Dev, I can clone the repo and get a working Python 3.12 env (uv/venv, ruff, pytest, pre-commit) with one documented command | 2 |
| S1.3 | As Dev, every push runs lint + tests in GitHub Actions | 2 |
| S1.4 | As Dev, the Kaggle dataset download is scripted and excluded from git | 1 |

### E2 — Data & baseline model (Sprint 1)
| ID | Story | Pts |
|---|---|---|
| S2.1 | As Riikka, I can read an EDA notebook that explains the dataset, its class imbalance and its limits | 3 |
| S2.2 | As Dev, a reproducible training script fits an Isolation Forest with a fixed seed and saves the artifact | 3 |
| S2.3 | As Riikka, an evaluation report shows PR-AUC, precision@k and a threshold-tradeoff curve, so decision thresholds are grounded | 5 |
| S2.4 | As PM, model choices are recorded in ADR-002 | 1 |

### E3 — Finnish synthetic data (Sprint 2)
| ID | Story | Pts |
|---|---|---|
| S3.1 | As Dev, a generator produces transactions with EUR amounts, valid-format FI IBANs, Finnish merchants (S/K-Group, Wolt, HSL, VR, Alko…), channels (card / A2A transfer / Siirto / MobilePay), Europe/Helsinki timestamps | 5 |
| S3.2 | As Riikka, the generator injects labelled fraud patterns (account takeover bursts, APP-fraud-like transfers, card testing) at a configurable rate | 5 |
| S3.3 | As Dev, feature engineering maps generated transactions into the model's feature space; approach documented | 5 |
| S3.4 | As PM, generator assumptions cite Nordic payment statistics | 2 |

### E4 — Scoring service (Sprint 3)
| ID | Story | Pts |
|---|---|---|
| S4.1 | As Dev, `POST /score` returns risk score, decision (approve/review/block) and reason codes in < 100 ms p99 locally | 5 |
| S4.2 | As Dev, the service is Dockerised and starts via docker-compose | 2 |
| S4.3 | As Riikka, decisions and scores persist to PostgreSQL for audit | 3 |
| S4.4 | As Dev, `pytest` coverage on `src/` ≥ 80 %, including API contract tests | 3 |
| S4.5 | As PM, ADR-001 (FastAPI) reviewed against reality; service design documented in architecture overview | 1 |

### E5 — Real-time streaming (Sprint 4)
| ID | Story | Pts |
|---|---|---|
| S5.1 | As Dev, a Kafka topic receives generator transactions via a producer at a configurable rate | 3 |
| S5.2 | As Dev, a consumer scores messages and writes decisions, sustaining ≥ 50 tx/s locally | 5 |
| S5.3 | As Riikka, end-to-end latency (produce → decision) is measured and reported | 3 |
| S5.4 | As Dev, the whole stack (Kafka, API, DB, producer, consumer) runs with one compose command | 3 |

### E6 — Observability & hardening (Sprint 5)
| ID | Story | Pts |
|---|---|---|
| S6.1 | As Riikka, a minimal dashboard (or notebook) shows score distributions, alert rates, latency | 3 |
| S6.2 | As Dev, README quickstart verified on a clean machine | 2 |

### E7 — Compliance & closure (Sprint 5)
| ID | Story | Pts |
|---|---|---|
| S7.1 | As PM, compliance notes are refreshed with "as of" dates | 2 |
| S7.2 | As PM, demo video (3–5 min) recorded and linked | 2 |
| S7.3 | As PM, final report + whole-project retrospective committed | 3 |

### Icebox (explicitly not committed)
Autoencoder model (PyTorch) · SHAP-based explanations · Grafana/Prometheus stack · Azure/AWS free-tier deployment · drift detection · VoP-mismatch simulation · Finnish-language API docs

## Ordering rationale

Model before API (the API is meaningless without something to serve); generator before streaming (the stream needs realistic content); observability last because it hardens what already works. Descope order under pressure: E6 → S5.3/S5.4 → autoencoder-class icebox items stay frozen.
