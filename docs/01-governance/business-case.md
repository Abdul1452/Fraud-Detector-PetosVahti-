# Business Case — Petosvahti

*Written as if pitching an internal product to a Finnish bank's steering group. The "business" framing is deliberately realistic; the actual project goal is learning + portfolio.*

## 1. Problem statement

Instant payments have removed the time window in which banks traditionally caught fraud. Since October 2025, euro-area PSPs must process SEPA instant credit transfers in under 10 seconds, around the clock. Meanwhile fraud liability is shifting from customers to institutions:

- **PSD3 / Payment Services Regulation** (political agreement Nov 2025, final texts Apr 2026): PSPs can be required to reimburse victims of authorised push payment (APP) fraud where the PSP did not meet expected detection standards. Liability also attaches for failing to flag payee-name/IBAN mismatches.
- **Instant Payments Regulation**: Verification of Payee mandatory since Oct 2025 — but VoP catches misdirection, not manipulation. Social-engineering fraud passes VoP checks.
- **EU AI Act**: AI systems for detecting financial fraud are explicitly *excepted* from the high-risk credit-scoring category (Annex III 5(b)) — regulation permits and effectively encourages ML-based fraud detection, provided systems avoid drifting into general creditworthiness profiling.

A bank that cannot score transactions in real time will pay for fraud it fails to stop.

## 2. Market context (Finland)

- Finnish e-commerce is dominated by **online bank transfers** (≈ 39 % of e-commerce payments), not cards — fraud models built on card-only assumptions miss the largest local channel.
- **Siirto** — since June 2026 an OP + Nordea joint venture embedded in their mobile apps — moves money by phone number in seconds.
- **Vipps MobilePay** dominates P2P and is expanding cross-border through the 2026 EPI/Bizum/Bancomat cooperation.
- Finnish transaction patterns are distinctive: high card-on-file trust, strong seasonal cycles (midsummer, Christmas), S-Group/K-Group merchant concentration, Wolt/HSL/VR micro-payments.

A fraud model localised to these rails and patterns is the product hypothesis.

## 3. Options considered

| Option | Description | Verdict |
|---|---|---|
| A — Do nothing | Rely on rules-based filters | Rejected: rules can't keep pace with instant rails; liability exposure grows under PSR |
| B — Buy | License Stripe Radar / Feedzai-class vendor | Realistic for a bank, but no learning value and vendor models under-fit Finnish A2A patterns |
| C — **Build (chosen)** | In-house real-time anomaly scoring, Finnish-localised | Full control, explainability, direct fit to local rails; as a learning project, maximum skill coverage |

## 4. Expected benefits

**Product-fiction benefits** (the realistic pitch): reduced fraud losses on instant rails, PSR liability defence via documented "expected detection standards" compliance, explainable scores for dispute handling.

**Actual project benefits** (the real ROI):

| Benefit | Evidence produced |
|---|---|
| End-to-end ML engineering skill (data → model → API → stream) | Working system + evaluation reports |
| Enterprise PM practice (charter, backlog, sprints, risk mgmt) | This documentation set, sprint records |
| Finnish fintech domain knowledge | Compliance notes, localised data generator |
| Portfolio differentiation for Finnish job market | Public repo with recruiter-readable docs |

## 5. Costs

~100 hours over 10 weeks. €0 cash (local Docker, free tiers, public dataset).

## 6. Risks to the business case

If time budget is cut, value is preserved by descoping from the end (streaming → stretch) rather than thinning quality everywhere. See `risk-register.md`.

## 7. Recommendation

Proceed with Option C under the charter's 10-week plan. Review at every sprint boundary; kill criteria: two consecutive sprints with < 50 % of committed points delivered forces a scope reset.
