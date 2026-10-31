# Petosvahti 🇫🇮

**Real-time transaction fraud detection for the Finnish payments market.**

Petosvahti (*Finnish: "fraud guard"*) is a Stripe Radar-style fraud detection service: transactions stream in (in-process simulator or Kafka), an Isolation Forest scores each one for fraud risk in under a millisecond, and a FastAPI service returns `approve` / `review` / `block` with human-readable reason codes — watched live on an ops dashboard.

> Portfolio & learning project by [Abdullahi Olamilekan Abdulwasiu](https://github.com/Abdul1452) — Software Engineering & Project Management, Turku UAS. Run with the documentation and governance discipline of a real Finnish enterprise (Nordea/Wärtsilä-style).

## Run the demo (2 minutes)

```bash
git clone https://github.com/Abdul1452/petosvahti.git
cd petosvahti
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
petosvahti demo                   # trains the model on first run (~2 min), opens the dashboard
```

`petosvahti demo --quick` trains a small model in ~15 s instead. The dashboard is at <http://localhost:8000>, interactive API docs at <http://localhost:8000/docs>.

What to try — the full walkthrough is in [`docs/06-demo/demo-guide.md`](docs/06-demo/demo-guide.md):

1. **Watch the stream**: 500 simulated Finnish customers paying at Prisma, K-Citymarket, Wolt, by MobilePay and Siirto — almost all approved at risk ≈ 0.
2. **Launch an attack**: inject a "safe account" APP scam, an account takeover or a card-testing burst and watch it get held or blocked, with the reasons.
3. **Try a payment yourself**: score an everyday purchase vs. a €4 800 Siirto transfer to a stranger for the *same* customer.
4. **Check the numbers**: fraud caught, false alarms, p99 latency — and `/metrics` in Prometheus format.

### With Kafka (Docker)

```bash
docker compose up --build         # Kafka (KRaft) + producer + scoring API → http://localhost:8000
```

The producer replays 35 days of synthetic history to `petosvahti.transactions` (warms customer profiles), then streams live; the API consumes, scores and publishes every decision to `petosvahti.decisions`.

## Results

From the [model evaluation report](docs/05-evaluation/model-evaluation-v1.md) — 2 000 synthetic customers, time-ordered splits, the 14-day test window replayed through the real online scorer:

| | Petosvahti | Static rules baseline |
|---|---|---|
| PR-AUC | **0.943** (supervised reference: 0.906) | — |
| Fraud flagged (review + block) | **95.2 %** at 88.2 % precision | 84.9 % at 74.4 % precision |
| Fraud blocked outright | 81.6 % at 97.7 % precision | — |
| Legit payments blocked | 0.085 per 1 000 | — |
| Scoring latency p99 | **~1 ms** in-process · ~9 ms over HTTP | target < 100 ms |

These are numbers on **synthetic data whose fraud patterns I also wrote** — they show the pipeline works and the features carry signal, not what it would achieve on real bank traffic. The report's limitations section says this at length.

## Why Finland?

- **PSD3/PSR (agreed 2025–2026)** shifts liability for authorised push payment (APP) fraud onto payment service providers that fail to meet detection standards — real-time fraud scoring is becoming a regulatory necessity, not a nice-to-have.
- **SEPA Instant Payments Regulation**: since October 2025 all euro-area banks must send/receive instant credit transfers (≤10 s). Instant money means instant fraud — batch detection is obsolete.
- Finland's payment mix is distinctive: online bank transfers dominate e-commerce, Siirto (OP + Nordea joint venture) handles phone-number-based instant payments, and Vipps MobilePay is ubiquitous for P2P.

## How it works

```
 Simulator (in-process)  ─┐
                          ├─▶ Scorer ─▶ FeatureStore ─▶ IsolationForest ─▶ isotonic ─▶ policy ─▶ decision + reasons
 Kafka transactions topic ┘     │       (per-customer)    (compiled,       calibration   20 / 85
                                │                          <1 ms)          → P(fraud)
                                ├─▶ FastAPI  POST /score · /health · /metrics · dashboard
                                └─▶ Kafka decisions topic
```

- **Synthetic Finnish data** ([`generator/`](src/petosvahti/generator/)): seeded event simulation of customers with home cities, regular merchants, MobilePay/Siirto friends, monthly rent, trips abroad and Helsinki-time daily rhythms; format-valid FI IBANs on a synthetic bank code. Three injected fraud typologies: APP "safe account" scams, account takeover, card testing.
- **Features** ([`scoring/features.py`](src/petosvahti/scoring/features.py)): 12 per-customer signals — amount vs. the customer's own history, new payee / device / country, velocity, night-time, instant rail, and an APP-scam interaction term. Blocked payments never teach the profile, and new payees have a 24 h cooling-off.
- **Model** ([`scoring/model.py`](src/petosvahti/scoring/model.py)): unsupervised Isolation Forest; labels are used only to calibrate the score into a probability and pick thresholds. scikit-learn needs ~30 ms per single prediction, so [`scoring/forest.py`](src/petosvahti/scoring/forest.py) compiles the trees into flat arrays — identical scores, ~0.05–0.4 ms.
- **Decisions** ([`scoring/policy.py`](src/petosvahti/scoring/policy.py)): `review` ≥ 20, `block` > 85. The review band is the GDPR Art. 22 human-in-the-loop path.

Design decisions and trade-offs: [`docs/03-architecture/architecture-overview.md`](docs/03-architecture/architecture-overview.md).

## API

| Method & path | Purpose |
|---|---|
| `POST /score` | Score one transaction → `risk_score`, `decision`, `reasons`, `features`, `latency_ms` |
| `GET /health` | Liveness + model version + stream source status |
| `GET /metrics` | Prometheus: decisions, latency quantiles, model info |
| `GET /api/stats`, `/api/events`, `/api/model` | Dashboard feeds |
| `POST /api/simulator/inject`, `/api/simulator/control`, `GET /api/scenarios` | Demo controls (simulator mode) |

```bash
curl -X POST localhost:8000/score -H "Content-Type: application/json" -d '{
  "customer_id": "C00042", "amount_eur": 4800, "channel": "siirto",
  "payee_id": "FI2179900000000001", "payee_name": "Matti Virtanen", "device_id": "dev-0000000000"}'
```

Configuration is via `PETOSVAHTI_*` environment variables ([`config.py`](src/petosvahti/config.py)): `SOURCE` (`simulator` | `kafka` | `none`), `SIM_RATE`, `SIM_CUSTOMERS`, `KAFKA_BOOTSTRAP`, `MODEL_PATH`, …

## Commands

| Command | What it does |
|---|---|
| `petosvahti demo [--quick]` | Train if needed, serve with the live simulator, open the browser |
| `petosvahti train [--quick] [--report PATH]` | Simulate data, train, replay-evaluate, save `models/fraud_model.joblib` |
| `petosvahti serve [--source kafka]` | Run the API + dashboard |
| `petosvahti produce --bootstrap HOST:PORT` | Stream synthetic transactions into Kafka |
| `make check` | ruff + mypy (strict) + pytest with coverage — same as CI |
| `python scripts/benchmark_kaggle.py` | Same algorithm on the Kaggle credit-card set (after `make data`) |

If the `petosvahti` script is not on your PATH, `python -m petosvahti …` works the same.

## Tech stack

Python 3.12 · scikit-learn · NumPy · FastAPI · Apache Kafka (KRaft) · Docker Compose · pytest · ruff · mypy (strict) · GitHub Actions

## Repository map

| Path | Contents |
|---|---|
| `src/petosvahti/generator/` | Synthetic Finnish transaction simulator |
| `src/petosvahti/scoring/` | Features, compiled forest, model, reasons, policy, scorer (framework-free core) |
| `src/petosvahti/training/` | Training + replay evaluation + report rendering |
| `src/petosvahti/api/` | FastAPI app, live feed/metrics, stream sources, dashboard |
| `src/petosvahti/streaming/` | Kafka producer/consumer adapter |
| `docs/01-governance/` | Business case |
| `docs/02-planning/` | Sprint reviews and retrospectives |
| `docs/03-architecture/` | Architecture overview and decision log |
| `docs/04-compliance/` | Finnish/EU regulatory context (PSD2/PSD3, IPR, AI Act, GDPR) |
| `docs/05-evaluation/` | Generated model evaluation report |
| `docs/06-demo/` | Demo guide |
| `tests/` | 54 tests: generator, features, model parity, API, streaming, CLI |

## Project status

| Sprint | Goal | Status |
|---|---|---|
| 0 | Governance, repo, environment | ✅ |
| 1 | Baseline model | ✅ Isolation Forest + compiled inference |
| 2 | Training pipeline + Finnish data generator | ✅ Replay evaluation, report, threshold tuning |
| 3 | FastAPI scoring service | ✅ `/score`, `/health`, `/metrics` |
| 4 | Kafka real-time streaming | ✅ Producer, consumer, decisions topic, Compose |
| 5 | Hardening, metrics dashboard, demo | ✅ Live dashboard, attack injection, demo guide |

Not built (stretch / production gaps): autoencoder challenger, PostgreSQL decision audit log, authentication on the API, persistent feature store. See the architecture overview.

## License

MIT
