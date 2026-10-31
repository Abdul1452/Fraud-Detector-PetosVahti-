# Demo Guide — Petosvahti

*A 5–7 minute walkthrough for a sprint review, a lecturer or an interviewer. Everything runs locally; all data is synthetic.*

## Before you start

```bash
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
petosvahti demo                 # first run trains the model (~2 min); later runs start in seconds
```

The dashboard opens at <http://localhost:8000>. Give it ~5 seconds: the status pill goes from **Warming up** (profiles are being built from 35 days of simulated history) to **Live · simulator**.

Want a clean slate between rehearsals? Stop with `Ctrl+C` and start again — everything except the trained model lives in memory.

## The script

### 1. The problem (30 s)

> "Since October 2025 every euro-area bank must send instant payments in under ten seconds, and they can't be recalled. Under PSD3/PSR the bank can end up liable for scams it should have caught. So fraud has to be scored *inside* that ten-second window — that's what this does, for Finnish rails: card, online bank, SEPA Instant, Siirto and MobilePay."

### 2. Normal traffic (45 s)

Point at the **Live decisions** table: Prisma, K-Citymarket, Wolt, MobilePay to friends — nearly everything approved with risk ≈ 0. Point at the **Scoring latency p99** tile (around a millisecond).

> "Each of these 500 synthetic customers has their own habits — home city, usual shops, friends they pay, rent day. The model judges each payment against *that customer's* history, not a global average."

Click any row: the dialog shows the 12 features behind the score.

### 3. A "safe account" scam (90 s) — the headline case

In **Try a payment yourself**, keep the customer it shows and click **Everyday purchase → Score it**: risk ≈ 0, approve.

Switch to **"Safe account" scam → Score it**: same customer, same phone, €4 800 by Siirto to a stranger → **block**, with reasons such as *amount far above usual*, *first payment to this payee*, *high-value instant transfer*.

> "This is authorised push-payment fraud: the customer really is pressing the button, on their own phone, because someone pretending to be the bank told them to. Device checks and strong authentication don't help — only behaviour does. This is exactly the fraud PSR makes banks liable for."

Optional: score the scam a second time. It is still blocked — and now *rapid repeat* and *velocity* join the reasons, because a fraudster rarely stops at one transfer.

### 4. Live attacks (90 s)

Click **Launch an attack → Account takeover**. A toast names the victim; their rows get a blue edge in the feed. Within a few seconds the hijacked transfers appear as **block** — *unrecognised device*, *country not seen before*.

Click **Card testing**: a burst of €0.50–4 charges at random web shops from an unknown device. Once velocity builds, the burst is blocked. The first probe is the weak spot: on its own it looks like buying a coffee, so depending on the victim it is held for review or occasionally approved.

> "Those first-probe misses are real, and the evaluation report counts them — it's the most common false negative."

Switch the feed to **Flagged only** to show just the interesting rows.

### 5. Numbers and honesty (60 s)

Point at **Fraud caught** and **False alarms** (computed against the simulator's ground truth, which the model never sees), and at **Detection by pattern**.

Open [`docs/05-evaluation/model-evaluation-v1.md`](../05-evaluation/model-evaluation-v1.md):

- PR-AUC 0.94 on a 14-day test window replayed through the live scoring code; 95 % of fraud flagged, 82 % blocked outright at 98 % precision.
- Compared against a static rules baseline and a supervised reference.
- **Limitations**: synthetic data with fraud patterns I wrote myself, so these numbers prove the pipeline, not real-world performance.

### 6. Engineering (optional, 60 s)

- `http://localhost:8000/docs` — OpenAPI; try `POST /score`.
- `http://localhost:8000/metrics` — Prometheus counters and latency quantiles.
- `docker compose up --build` — the same scoring core behind Kafka: producer → `petosvahti.transactions` → scorer → `petosvahti.decisions`.
- The compiled Isolation Forest: scikit-learn takes ~30 ms per single prediction; flattening the trees made it ~0.05–0.4 ms with identical scores (a unit test proves equality).

## Likely questions

| Question | Short answer |
|---|---|
| Why not just train on Kaggle? | It's PCA-anonymised card data — no customer, payee, device or rail, so none of these behavioural features exist. `scripts/benchmark_kaggle.py` runs the algorithm on it as a sanity check. |
| Why unsupervised? | Real fraud labels arrive weeks late and incomplete. The forest works on unlabelled traffic; labels are only used to calibrate the score and pick thresholds. |
| What happens to `review`? | It's the human-in-the-loop band (GDPR Art. 22) — in a bank, an analyst queue or a step-up confirmation in the app. About one case per 1 000 payments. |
| Is the AI Act a problem? | Fraud detection is explicitly excepted from the high-risk credit-scoring category (Annex III 5(b)); the project still logs model version and reasons for every decision. |
| What would you build next? | A persistent decision log (PostgreSQL), a supervised challenger trained on confirmed review outcomes, drift monitoring, and authentication on the API. |

## If something goes wrong

| Symptom | Fix |
|---|---|
| `petosvahti` not found | Activate the venv, or use `python -m petosvahti demo` |
| Port 8000 in use | `petosvahti demo --port 8010` |
| Model error after pulling new code | Delete `models/fraud_model.joblib` (features changed) and run `petosvahti demo` again |
| Dashboard says *Disconnected* | The server stopped — check the terminal |
