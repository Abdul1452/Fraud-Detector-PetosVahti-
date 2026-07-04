# Regulatory Context — Finnish / EU Payments & AI

*Documentation-only: this project handles zero real personal data and needs no licence. This file exists because a fraud product's design is shaped by regulation, and demonstrating that understanding is a project objective. **Facts as of July 2026** — refresh at Sprint 5 (risk R7).*

## 1. Instant Payments Regulation (IPR, Reg. 2024/886)

- Euro-area PSPs must **receive** instant credit transfers (since Jan 2025) and **send** them (since Oct 2025), 24/7/365, funds available ≤ 10 s.
- **Verification of Payee (VoP)** mandatory since 9 Oct 2025 for euro-area PSPs — payee name vs IBAN check (match / close match / no match), free of charge, and it applies to *all* SEPA credit transfers, not only instant ones. Non-euro-area PSPs: July 2027. From Nov 2026 only structured/hybrid address formats are accepted in SEPA Instant.
- **Design consequence for Petosvahti**: the fraud window is ≤ 10 seconds; scoring must be synchronous and fast (NFR: p99 < 100 ms leaves budget for the rest of the payment chain). VoP removes misdirection fraud but not manipulation (APP) fraud — which is exactly the gap ML scoring addresses.

## 2. PSD2 → PSD3 / PSR

- PSD2 (in force): SCA (strong customer authentication), fraud reporting to the national authority — in Finland, **Finanssivalvonta (FIN-FSA)** supervises PSPs and collects fraud statistics.
- **PSD3 + Payment Services Regulation (PSR)**: political agreement 27 Nov 2025; final compromise texts published Apr 2026; Official Journal publication expected ~Q2 2026, with PSR applying ~18 months after entry into force and PSD3 transposed nationally (~2028 in practice).
- PSR's fraud provisions: PSPs face **reimbursement liability for APP/impersonation fraud** where they failed to meet expected detection standards; liability also attaches to missed payee-name/identifier mismatch warnings; platforms that ignore fraud-content notices become liable to PSPs.
- **Design consequence**: "expected detection standards" is the product's reason to exist. Auditability NFR (every decision persisted with model version and reason codes) is what a PSP would show a supervisor.

## 3. EU AI Act (Reg. 2024/1689)

- Creditworthiness assessment / credit scoring of natural persons is **high-risk** (Annex III 5(b)) — but the same clause **excepts AI systems used to detect financial fraud**.
- The **Digital Omnibus** provisional agreement (May 2026) defers Annex III high-risk obligations to ~Dec 2027 (pending formal adoption).
- **Design consequences**: (a) keep the model strictly fraud-scoped — the moment it profiles general creditworthiness or broad economic behaviour, the high-risk regime attaches; (b) even under the exception, we *voluntarily* adopt high-risk-style hygiene because it's good engineering: logging of every decision, documented training data, human-review path (`review` decision class), model versioning.

## 4. GDPR

- Fraud prevention is a recognised legitimate-interest basis (Recital 47), but profiling still triggers Art. 22 considerations (automated decisions with significant effects → human intervention rights) and DPIA duties for systematic monitoring.
- **Project policy**: synthetic data only. Generated IBANs use valid Finnish format with non-allocated bank codes; names/merchants from public lists; no re-identifiable patterns. A pre-commit hook blocks accidental data-file commits (risk R6).
- The `review` decision class models the Art. 22 human-in-the-loop requirement.

## 5. AML (context only)

AMLD5/6 and the incoming EU AMLA authority govern money-laundering detection — adjacent to, but distinct from, transaction fraud scoring. Out of scope; noted because interviewers routinely probe the difference: **fraud = protecting the customer's money; AML = stopping the customer's (or mule's) crime.**

## 6. Finnish market notes

- Supervisor: **Finanssivalvonta (FIN-FSA)**; consumer disputes: FINE; central bank statistics: Bank of Finland (Suomen Pankki) — source for generator calibration.
- Payment mix: online-bank-transfer-dominant e-commerce (≈ 39 %), **Siirto** (OP + Nordea JV; app retired Jun 2026, now embedded in bank apps) for phone-number instant payments, **Vipps MobilePay** for P2P (joining the pan-European EPI/Bizum/Bancomat interoperability effort, Feb 2026).
- Strong customer authentication culture: Finnish bank identifiers (TUPAS legacy → strong e-ID) make identity fraud harder and push criminals toward manipulation/APP fraud — reinforcing the product thesis.

## Primary sources

- ECB, Instant Payments Regulation overview — ecb.europa.eu
- European Payments Council, Verification of Payee scheme — europeanpaymentscouncil.eu
- Norton Rose Fulbright / Morrison Foerster PSD3-PSR trackers (2026)
- EU AI Act, Annex III — artificialintelligenceact.eu
- Norges Bank, *Payments in the Nordics* (Dec 2025)
- siirto.fi — OP/Nordea joint venture announcement (2026)
