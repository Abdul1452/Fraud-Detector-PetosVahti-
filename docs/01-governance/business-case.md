# Business Case — Petosvahti

*Written as if pitching an internal product to a Finnish bank's steering group. The "business" framing is deliberately realistic; the actual project goal is learning + portfolio. Citations `[Rn]` resolve in [`docs/references.md`](../references.md).*

## 1. Problem statement

Instant payments have removed the time window in which banks traditionally caught fraud. Since October 2025, euro-area PSPs must process SEPA instant credit transfers in under 10 seconds, around the clock [R1][R2]. Meanwhile fraud liability is shifting from customers to institutions:

- **PSD3 / Payment Services Regulation** (political agreement Nov 2025, final texts Apr 2026): PSPs can be required to reimburse victims of authorised push payment (APP) fraud where the PSP did not meet expected detection standards; liability also attaches for failing to flag payee-name/IBAN mismatches [R5][R6].
- **Instant Payments Regulation**: Verification of Payee mandatory since Oct 2025 [R3][R4] — but VoP catches misdirection, not manipulation. Social-engineering fraud passes VoP checks.
- **EU AI Act**: AI systems for detecting financial fraud are explicitly *excepted* from the high-risk credit-scoring category (Annex III 5(b)) [R7] — regulation permits and effectively encourages ML-based fraud detection, provided systems avoid drifting into general creditworthiness profiling.

A bank that cannot score transactions in real time will pay for fraud it fails to stop.

## 2. Market context (Finland)

- Finnish e-commerce is dominated by **online bank transfers** (≈ 37 % in 2021, projected ≈ 39 % by 2026), not cards [R15] — fraud models built on card-only assumptions miss the largest local channel.
- **Siirto** — since June 2026 an OP + Nordea joint venture embedded in their mobile apps [R12][R13] — moves money by phone number in seconds.
- **Vipps MobilePay** dominates Nordic P2P and is expanding cross-border through the 2026 cooperation with EPI, Bizum, Bancomat and MB WAY [R14].
- Nordic payment behaviour is well documented and distinctive (high digitalisation, low cash use, strong bank-ID culture) [R11]; Finnish specifics for the data generator are calibrated from Bank of Finland statistics [R16].

A fraud model localised to these rails and patterns is the product hypothesis. The product archetype is Stripe Radar [R21].

## 3. Options considered

| Option | Description | Verdict |
|---|---|---|
| A — Do nothing | Rely on rules-based filters | Rejected: rules can't keep pace with instant rails [R1]; liability exposure grows under PSR [R5] |
| B — Buy | License Stripe Radar / Feedzai-class vendor [R21] | Realistic for a bank, but no learning value and vendor models under-fit Finnish A2A patterns [R15] |
| C — **Build (chosen)** | In-house real-time anomaly scoring, Finnish-localised | Full control, explainability, direct fit to local rails; as a learning project, maximum skill coverage |

## 4. Expected benefits

**Product-fiction benefits** (the realistic pitch): reduced fraud losses on instant rails; PSR liability defence via documented "expected detection standards" compliance [R5][R6]; explainable scores for dispute handling.

**Actual project benefits** (the real ROI):

| Benefit | Evidence produced |
|---|---|
| End-to-end ML engineering skill (data → model [R17][R18] → API → stream [R22]) | Working system + evaluation reports |
| Enterprise PM practice (Scrum [R23], ADRs [R24], risk management) | This documentation set, sprint records |
| Finnish fintech domain knowledge [R11][R15] | Compliance notes, localised data generator |
| Portfolio differentiation for the Finnish job market | Public repo with recruiter-readable docs |

## 5. Costs

~100 hours over 10 weeks. €0 cash (local Docker, free tiers, public dataset [R17]).

## 6. Risks to the business case

If the time budget is cut, value is preserved by descoping from the end (streaming → stretch) rather than thinning quality everywhere. See `risk-register.md`.

## 7. Recommendation

Proceed with Option C under the charter's 10-week plan. Review at every sprint boundary; kill criteria: two consecutive sprints with < 50 % of committed points delivered forces a scope reset.

---
*Version 1.1 — added full referencing. Supersedes v1.0 (baseline).*
