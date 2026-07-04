# Risk Register — Petosvahti

Scoring: Probability × Impact, each 1–5. Exposure = P × I. Review at every sprint retrospective; owner is PM (solo project — the point is practising the discipline).

| ID | Risk | Cat. | P | I | Exp. | Response | Mitigation / trigger |
|----|------|------|---|---|------|----------|----------------------|
| R1 | Time budget slips (studies/work take priority) | Schedule | 4 | 4 | 16 | Reduce | Fixed sprint cadence; descope stretch items first; kill criterion in business case. Trigger: < 50 % of sprint points done at mid-sprint |
| R2 | Kafka + Docker complexity stalls Sprint 4 | Technical | 3 | 4 | 12 | Mitigate | Use single-broker KRaft mode or Redpanda; spike ticket in Sprint 3 to de-risk early. Fallback: file-based replay simulating the stream interface |
| R3 | Model performs poorly on extreme class imbalance (0.17 % fraud) | Technical | 3 | 3 | 9 | Mitigate | PR-AUC (never accuracy) as metric; threshold tuning; documented failure analysis is an acceptable learning outcome even if PR-AUC target missed |
| R4 | Scope creep (dashboards, more models, UI) | Scope | 4 | 3 | 12 | Avoid | Everything new goes to backlog as `icebox`; only sprint planning can pull it in |
| R5 | Synthetic Finnish data too naive → weakens the localisation story | Product | 3 | 3 | 9 | Mitigate | Base generator parameters on published Bank of Finland / Nordic payment statistics; document assumptions in the generator README |
| R6 | GDPR misstep (accidentally committing real-looking personal data) | Compliance | 2 | 5 | 10 | Avoid | Synthetic-only policy; IBANs generated with valid format but reserved test bank codes; pre-commit check for data files |
| R7 | Regulatory facts go stale (PSD3 dates, AI Act Omnibus) | Compliance | 3 | 2 | 6 | Accept | Compliance doc carries "as of" dates and links to primary sources; refresh at Sprint 5 |
| R8 | Solo-Scrum degenerates into no process | Process | 3 | 3 | 9 | Mitigate | Ceremonies are calendar-blocked; sprint review notes are mandatory artifacts committed to the repo |
| R9 | Laptop loss / environment breakage | Technical | 2 | 3 | 6 | Mitigate | Everything in git incl. docs; Docker Compose rebuilds environment; model artifacts reproducible from seed |
| R10 | Motivation dip mid-project | Personal | 3 | 4 | 12 | Mitigate | Sprint 3 delivers a visible, demoable API early; learning journal records wins; each sprint has a shippable outcome |

## Top risks by exposure

R1 (16) — schedule; R2, R4, R10 (12) — Kafka complexity, scope creep, motivation. All four have the same structural answer: **small sprints with shippable outcomes and ruthless descoping from the end of the plan.**

## Risk log

| Date | Change |
|---|---|
| 2026-07-04 | Register created, 10 risks baselined |
