# Model Evaluation Report — <model name & version>

**Date:** · **Dataset:** <name, split, size, fraud rate> · **Seed:** <n> · **Artifact:** <path/hash>

## Headline metrics

| Metric | Value | Target | Baseline comparison |
|---|---|---|---|
| PR-AUC | | ≥ 0.70 (O1) | <vs previous model / XGBoost reference> |
| Precision @ top-1 % | | | |
| Recall @ threshold | | | |

*Why PR-AUC and not accuracy: at 0.17 % fraud, predicting "all legit" scores 99.8 % accuracy and catches nothing.*

## Threshold analysis
<table or curve: threshold → precision/recall/alert-rate. Chosen approve/review/block cut-offs + justification. Alert rate must be operationally sane: how many `review` cases per 1 000 tx?>

## Error analysis
<what does the model miss (false negatives)? what does it flag wrongly (false positives)? patterns?>

## Limitations & honesty section
<dataset limits, leakage risks, what this metric does NOT prove about production performance>

## Decision
<ship as baseline / iterate / abandon — and the ADR to update if architectural>
