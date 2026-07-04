# ADR-002: Isolation Forest as baseline model

- **Status**: Accepted
- **Date**: 2026-07-04
- **Deciders**: A. Abdulwasiu

## Context
The Kaggle credit-card fraud dataset is extremely imbalanced (~0.17 % fraud). Fraud patterns shift constantly in production, so anomaly detection (learning "normal") is a defensible framing alongside supervised learning. The project needs a model that trains in minutes, is explainable enough to generate reason codes, and leaves budget for the streaming work.

## Decision
Isolation Forest (scikit-learn) as the committed baseline. An autoencoder is an icebox stretch goal, not a commitment.

## Consequences
+ Trains fast, few hyperparameters, works unsupervised (matches real-world label scarcity)
+ Feature-level anomaly contributions approximable for reason codes
+ Frees time for the harder engineering (Kafka, latency)
− Likely lower PR-AUC ceiling than gradient boosting — accepted; O1 targets PR-AUC ≥ 0.70, and a documented comparison against a supervised XGBoost reference in the evaluation notebook keeps us honest
− EU AI Act note: keeping the model strictly fraud-focused (not creditworthiness profiling) preserves the Annex III 5(b) exception — a design constraint, not just a legal footnote

## Alternatives considered
- **XGBoost/LightGBM (supervised)**: better benchmark scores, but depends on labels that real fraud teams lack at day 0; kept as evaluation reference only.
- **Autoencoder (PyTorch)**: pedagogically rich, heavier; icebox.
- **Rules only**: no ML learning value; rules survive as a thin pre-filter layer idea.
