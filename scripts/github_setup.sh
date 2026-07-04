#!/usr/bin/env bash
# One-time GitHub setup for Petosvahti (S1.1).
# Prereqs: git, GitHub CLI (`gh auth login` done), run from the repo root.
set -euo pipefail

REPO="Abdul1452/petosvahti"

# --- 1. Repo -----------------------------------------------------------------
git init -b main 2>/dev/null || true
git add -A
git commit -m "feat: project foundation — governance docs, scaffolding, CI (S1.1-S1.3)" || true
gh repo create "$REPO" --public --source=. --push \
  --description "Real-time fraud detection for the Finnish payments market — FastAPI + Kafka + Isolation Forest. Run like a real Finnish enterprise project." || git push -u origin main

# --- 2. Labels ---------------------------------------------------------------
for e in E1 E2 E3 E4 E5 E6 E7; do gh label create "epic:$e" -R "$REPO" --color 1D76DB --force; done
for s in 0 1 2 3 4 5;          do gh label create "sprint:$s" -R "$REPO" --color 0E8A16 --force; done
gh label create "icebox" -R "$REPO" --color BFBFBF --force
gh label create "spike"  -R "$REPO" --color D93F0B --force

# --- 3. Issues (backlog stories) ----------------------------------------------
mk() { gh issue create -R "$REPO" -t "$1" -l "$2" -b "$3"; }

mk "S1.1: Governance doc set committed"                    "epic:E1,sprint:0" "AC: charter, business case, risk register, backlog, ways of working in docs/. Pts: 3"
mk "S1.2: One-command dev environment"                     "epic:E1,sprint:0" "AC: make setup gives Python 3.12 venv with ruff, mypy, pytest, pre-commit. Pts: 2"
mk "S1.3: CI runs lint + types + tests on every push"      "epic:E1,sprint:0" "AC: GitHub Actions green on main. Pts: 2"
mk "S1.4: Scripted Kaggle dataset download, git-ignored"   "epic:E1,sprint:0" "AC: python scripts/download_dataset.py; data/ never committed. Pts: 1"
mk "S2.1: EDA notebook — dataset, imbalance, limits"       "epic:E2,sprint:1" "AC: notebook explains class imbalance (~0.17%) and PCA feature limits. Pts: 3"
mk "S2.2: Reproducible Isolation Forest training script"   "epic:E2,sprint:1" "AC: fixed seed, saved artifact, same metrics ±1%. Pts: 3"
mk "S2.3: Evaluation report with PR-AUC + threshold curve" "epic:E2,sprint:1" "AC: PR-AUC ≥ 0.70 target; precision@k; threshold tradeoffs documented. Pts: 5"
mk "S2.4: ADR-002 reviewed against results"                "epic:E2,sprint:1" "AC: ADR updated or superseded with evidence. Pts: 1"
mk "S3.1: Finnish transaction generator (channels, IBANs, merchants)" "epic:E3,sprint:2" "AC: EUR, valid-format FI IBANs, S/K-Group-Wolt-HSL-VR-Alko merchants, card/A2A/Siirto/MobilePay, Europe/Helsinki patterns. Pts: 5"
mk "S3.2: Labelled fraud pattern injection"                "epic:E3,sprint:2" "AC: ATO bursts, APP-like transfers, card testing; configurable rate. Pts: 5"
mk "S3.3: Feature mapping generator → model space"         "epic:E3,sprint:2" "AC: documented approach; tests. Pts: 5"
mk "S3.4: Generator assumptions cite Nordic statistics"    "epic:E3,sprint:2" "AC: sources in generator README. Pts: 2"
mk "S4.1: POST /score endpoint <100ms p99"                 "epic:E4,sprint:3" "AC: score + decision + reason codes; latency measured locally. Pts: 5"
mk "S4.2: Dockerised service via compose"                  "epic:E4,sprint:3" "AC: docker compose up serves API. Pts: 2"
mk "S4.3: Decisions persisted to PostgreSQL"               "epic:E4,sprint:3" "AC: audit table with model_version, reasons, latency. Pts: 3"
mk "S4.4: Coverage ≥80% incl. API contract tests"          "epic:E4,sprint:3" "AC: pytest-cov gate. Pts: 3"
mk "S4.5: ADR-001 reality check + architecture update"     "epic:E4,sprint:3" "AC: docs updated. Pts: 1"
mk "SPIKE: Kafka KRaft single-broker de-risk"              "epic:E5,sprint:3,spike" "Timebox 3h: broker up in compose, produce/consume hello. Mitigates R2. Pts: 2"
mk "S5.1: Producer streams generator output to Kafka"      "epic:E5,sprint:4" "AC: transactions.raw topic, configurable rate. Pts: 3"
mk "S5.2: Scoring consumer sustains ≥50 tx/s"              "epic:E5,sprint:4" "AC: throughput measured and reported. Pts: 5"
mk "S5.3: End-to-end latency measured"                     "epic:E5,sprint:4" "AC: produce→decision latency distribution reported. Pts: 3"
mk "S5.4: Full stack one-command startup"                  "epic:E5,sprint:4" "AC: kafka+api+db+producer+consumer via single compose command. Pts: 3"
mk "S6.1: Minimal monitoring dashboard/notebook"           "epic:E6,sprint:5" "AC: score distribution, alert rate, latency view. Pts: 3"
mk "S6.2: README quickstart verified on clean machine"     "epic:E6,sprint:5" "AC: stranger-test <15 min. Pts: 2"
mk "S7.1: Compliance notes refreshed (as-of dates)"        "epic:E7,sprint:5" "AC: regulatory-context.md updated; risk R7 closed. Pts: 2"
mk "S7.2: Demo video recorded and linked"                  "epic:E7,sprint:5" "AC: 3-5 min, linked from README. Pts: 2"
mk "S7.3: Final report + whole-project retrospective"      "epic:E7,sprint:5" "AC: committed to docs/02-planning/. Pts: 3"

echo "Done. Repo: https://github.com/$REPO"
