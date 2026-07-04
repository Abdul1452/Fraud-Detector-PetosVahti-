# Project Charter — Petosvahti

| Field | Value |
|---|---|
| Project name | Petosvahti — Real-time fraud detection for the Finnish payments market |
| Version | 1.0 (baseline) |
| Date | 2026-07-04 |
| Project owner / sponsor | Abdullahi Olamilekan Abdulwasiu (acting as sponsor, PM and engineer — roles kept explicit for learning) |
| Duration | 10 weeks (5 × 2-week sprints + Sprint 0), ~10 h/week ≈ 100 h |
| Methodology | Scrum (solo-adapted), governance artifacts per Finnish enterprise practice |

## 1. Purpose & background

EU payments are moving to instant-by-default. The Instant Payments Regulation has required euro-area PSPs to receive and send SEPA instant credit transfers since 2025, and PSD3/PSR (final texts published 2026) makes PSPs financially liable for authorised push payment fraud when their detection controls fall short. Fraud must therefore be caught **in the seconds before settlement**. This project builds a working, documented real-time fraud scoring service targeted at the Finnish market's payment mix (account-to-account transfers, Siirto, Vipps MobilePay, cards).

It is simultaneously a **learning vehicle**: every governance, planning and architecture artifact is produced to the standard of a large Finnish employer (Nordea, Wärtsilä, OP), so the repository doubles as a portfolio demonstrating both software engineering and project management competence.

## 2. Objectives (SMART)

| # | Objective | Measure | Deadline |
|---|---|---|---|
| O1 | Working anomaly-detection model on the Kaggle credit-card fraud dataset | PR-AUC ≥ 0.70 for Isolation Forest baseline; documented evaluation notebook | End Sprint 1 |
| O2 | Synthetic Finnish transaction generator | Configurable stream: EUR, FI IBANs, Finnish merchants, Siirto/MobilePay/card channels, Europe/Helsinki temporal patterns | End Sprint 2 |
| O3 | Production-style scoring API | FastAPI `/score` endpoint, Dockerised, p99 latency < 100 ms, test coverage ≥ 80 % on `src/` | End Sprint 3 |
| O4 | Real-time streaming pipeline | Kafka replay at ≥ 50 tx/s scored end-to-end; lag and latency metrics captured | End Sprint 4 |
| O5 | Enterprise-grade documentation | Charter, business case, backlog, sprint records, ADRs, risk register and compliance notes complete and current in repo | End Sprint 5 |
| O6 | Demonstrable outcome | 3–5 min recorded demo + final report; retrospective written | End Sprint 5 |

## 3. Scope

**In scope**
- Batch model training on Kaggle dataset; Isolation Forest baseline, autoencoder stretch
- Synthetic Finnish transaction data generator (no real personal data)
- FastAPI scoring service with decision logic (approve / review / block) and reason codes
- Kafka-based streaming replay and scoring consumer
- PostgreSQL persistence of scores and decisions
- CI with GitHub Actions (lint, test, build)
- Compliance *documentation* (GDPR, PSD2/PSD3, IPR, AI Act positioning)

**Out of scope**
- Real customer or production data of any kind
- Actual regulatory certification, PSD2 licensing, or FIN-FSA filings
- Production deployment / SLA operation (cloud deploy is a stretch goal, not committed)
- Case-management UI (API + minimal dashboard only)
- Model retraining automation / full MLOps platform

## 4. Deliverables

1. `petosvahti` GitHub repository: code, tests, CI, full documentation set
2. Trained model artifacts + evaluation report
3. Docker Compose environment (API + Kafka + PostgreSQL) that starts with one command
4. Master Project Plan (DOCX) and PDF exports in Google Drive
5. Demo recording and final project report with retrospective

## 5. Success criteria

- All six objectives met by their sprint deadlines (allowing scope re-negotiation via the backlog, never silent slippage)
- A stranger with Docker installed can run the full pipeline from README instructions in < 15 minutes
- The documentation alone is sufficient for a hiring manager to assess both PM and engineering skill

## 6. Stakeholders

| Stakeholder | Role | Interest / interaction |
|---|---|---|
| Abdullahi O. Abdulwasiu | Sponsor, PM, engineer | Learning outcomes, portfolio value; plays each role deliberately |
| Future employers (Nordea, OP, Wärtsilä-class) | Audience | Evidence of enterprise-grade working practice |
| Turku UAS network | Audience/support | Possible course credit, feedback, thesis seed |
| Open-source community | Audience | Reusable Finnish synthetic transaction generator |

## 7. High-level schedule

| Phase | Weeks | Gate |
|---|---|---|
| Sprint 0 — Foundation | 1 | Charter baselined, repo + environment ready |
| Sprint 1 — Model baseline | 2–3 | O1 met |
| Sprint 2 — Data & pipeline | 4–5 | O2 met |
| Sprint 3 — Scoring service | 6–7 | O3 met |
| Sprint 4 — Streaming | 8–9 | O4 met |
| Sprint 5 — Hardening & closure | 10 | O5, O6 met; project retrospective |

Each sprint ends with a **sprint review note** (what shipped, evidence) and a **retrospective entry** committed to `docs/02-planning/`. These play the role of Nordea-style steering-group gate checks.

## 8. Budget & resources

Zero cash budget. Local development (Docker Compose). GitHub free tier, Kaggle public dataset. Optional stretch: free-tier cloud deployment.

## 9. Constraints & assumptions

- Solo project, ~10 h/week; university/work commitments take precedence — schedule risk is managed by scope, not overtime
- Kaggle dataset features are PCA-anonymised; feature engineering realism comes from the synthetic generator instead
- All documentation in English (Finnish terms where they add market authenticity)

## 10. Approval

Baselined 2026-07-04. Changes to objectives or scope require a new charter version and a git tag.
