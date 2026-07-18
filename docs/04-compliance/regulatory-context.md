# Regulatory Context — Finnish / EU Payments & AI

*Documentation-only: this project handles zero real personal data and needs no licence. This file exists because a fraud product's design is shaped by regulation, and demonstrating that understanding is a project objective. **Facts as of July 2026** — refresh at Sprint 5 (risk R7). Citations `[Rn]` resolve in [`docs/references.md`](../references.md).*

## 1. Instant Payments Regulation (IPR, Reg. 2024/886) [R1][R2]

- Euro-area PSPs must **receive** instant credit transfers (since Jan 2025) and **send** them (since Oct 2025), 24/7/365, funds available ≤ 10 s [R1][R2].
- **Verification of Payee (VoP)** mandatory since 9 Oct 2025 for euro-area PSPs — payee name vs IBAN check (match / close match / no match), free of charge, applying to *all* SEPA credit transfers, not only instant ones [R3][R4]. Non-euro-area PSPs: July 2027 [R2]. From Nov 2026 only structured/hybrid address formats are accepted in SEPA Instant [R3].
- **Design consequence for Petosvahti**: the fraud window is ≤ 10 seconds; scoring must be synchronous and fast (NFR: p99 < 100 ms leaves budget for the rest of the payment chain). VoP removes misdirection fraud but not manipulation (APP) fraud — exactly the gap ML scoring addresses.

## 2. PSD2 → PSD3 / PSR [R5][R6]

- PSD2 (in force): SCA (strong customer authentication), fraud reporting to the national authority — in Finland, **Finanssivalvonta (FIN-FSA)** supervises PSPs and collects fraud statistics [R10].
- **PSD3 + Payment Services Regulation (PSR)**: political agreement 27 Nov 2025; final compromise texts published Apr 2026; Official Journal publication expected ~Q2 2026, PSR applying ~18 months after entry into force, PSD3 transposed nationally (~2028 in practice) [R5][R6].
- PSR fraud provisions: PSPs face **reimbursement liability for APP/impersonation fraud** where they failed to meet expected detection standards; liability also attaches to missed payee-name/identifier mismatch warnings; platforms that ignore fraud-content notices become liable to PSPs [R5][R6].
- **Design consequence**: "expected detection standards" is the product's reason to exist. The auditability NFR (every decision persisted with model version and reason codes) is what a PSP would show a supervisor.

## 3. EU AI Act (Reg. 2024/1689) [R7][R8]

- Creditworthiness assessment / credit scoring of natural persons is **high-risk** (Annex III 5(b)) — but the same clause **excepts AI systems used to detect financial fraud** [R7].
- The **Digital Omnibus** provisional agreement (May 2026) defers Annex III high-risk obligations to ~Dec 2027, pending formal adoption [R8].
- **Design consequences**: (a) keep the model strictly fraud-scoped — the moment it profiles general creditworthiness or broad economic behaviour, the high-risk regime attaches [R7]; (b) even under the exception, we *voluntarily* adopt high-risk-style hygiene because it is good engineering: logging of every decision, documented training data, human-review path (`review` decision class), model versioning.

## 4. GDPR (Reg. 2016/679) [R9]

- Fraud prevention is a recognised legitimate-interest basis (Recital 47), but profiling still triggers Art. 22 considerations (automated decisions with significant effects → human intervention rights) and DPIA duties for systematic monitoring [R9].
- **Project policy**: synthetic data only. Generated IBANs use valid Finnish format with non-allocated bank codes; merchant names from public lists; no re-identifiable patterns. A pre-commit hook blocks accidental data-file commits (risk R6).
- The `review` decision class models the Art. 22 human-in-the-loop requirement [R9].

## 5. AML (context only)

AMLD5/6 and the incoming EU AMLA authority govern money-laundering detection — adjacent to, but distinct from, transaction fraud scoring. Out of scope; noted because interviewers routinely probe the difference: **fraud = protecting the customer's money; AML = stopping the customer's (or mule's) crime.**

## 6. Finnish market notes [R11]–[R16]

- Supervisor: **Finanssivalvonta (FIN-FSA)** [R10]; consumer disputes: FINE; central-bank statistics: Bank of Finland — the calibration source for the data generator [R16].
- Payment mix: online-bank-transfer-dominant e-commerce (≈ 39 % by 2026) [R15]; **Siirto** (OP + Nordea JV; standalone app retired 3 Jun 2026, now embedded in bank apps) for phone-number instant payments [R12][R13]; **Vipps MobilePay** for P2P, joining the pan-European EPI/Bizum/Bancomat/MB WAY interoperability effort (Feb 2026) [R14].
- Strong-authentication culture: Finnish bank identifiers (TUPAS legacy → strong e-ID) make identity fraud harder and push criminals toward manipulation/APP fraud — reinforcing the product thesis [R11].

---
*Version 1.1 — added full referencing. Supersedes v1.0 (baseline). All citations: [`docs/references.md`](../references.md).*
