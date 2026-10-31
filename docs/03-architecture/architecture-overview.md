# Architecture Overview — Petosvahti

*Audience: engineers and reviewers who want to know how the system fits together and why. Citations `[Rn]` resolve in [`docs/references.md`](../references.md).*

## 1. Shape of the system

```
                       ┌──────────────────────── petosvahti.scoring (framework-free core) ───────────────────────┐
 Transaction ─────────▶│ FeatureStore ──▶ CompiledForest ──▶ isotonic map ──▶ decide() ──▶ ScoreResult + reasons │
                       │ (per customer)    (Isolation Forest)  (→ P(fraud))     (20 / 85)                          │
                       └──────────────────────────────────────────────▲──────────────────────────────────────────┘
                                                                      │ Scorer.score(tx)
          ┌───────────────────────────────┬───────────────────────────┼──────────────────────────────┐
   api/app.py (POST /score)     api/sources.SimulatorSource   api/sources.KafkaSource       training/train.py
   HTTP adapter                 in-process demo stream        petosvahti.transactions →     offline replay
                                                              petosvahti.decisions          evaluation
```

The scoring package knows nothing about HTTP, Kafka or threads beyond one lock. Every adapter — the API, the simulator loop, the Kafka consumer and the training replay — calls the same `Scorer.score(tx)`. The evaluation therefore measures exactly the code path that serves traffic.

## 2. Components

| Module | Responsibility |
|---|---|
| `domain.py` | `Transaction` (validated, label-free), `Channel`, `FraudPattern`, Helsinki time zone |
| `generator/` | Seeded event simulation of Finnish customers and three fraud typologies |
| `scoring/features.py` | Per-customer profile store and the 12-feature vector |
| `scoring/forest.py` | Isolation Forest compiled to flat arrays for sub-millisecond single-row inference |
| `scoring/model.py` | Forest + calibration + reason base rates; joblib persistence with a feature-schema check |
| `scoring/reasons.py` | Reason-code rules, ranked by rarity |
| `scoring/policy.py` | Risk → `approve` / `review` / `block` |
| `scoring/scorer.py` | Thread-safe extract → predict → decide → learn |
| `training/` | Time-ordered splits, fit, calibrate, replay-evaluate, render the report |
| `api/` | FastAPI app, live feed + Prometheus metrics, stream sources, dashboard |
| `streaming/kafka.py` | Wire format, topic creation, producer, consume-score-publish loop |

## 3. Key decisions

Each entry records the decision, the alternative and the reason — a lightweight decision log in the spirit of ADRs [R24].

**D1 — Synthetic Finnish data instead of training on Kaggle.** The Kaggle set [R17] is PCA-anonymised card data: no customer, payee, device, rail or local time, so none of the behavioural features this product is about can be computed on it. A seeded generator gives Finnish rails, labelled typologies and unlimited, GDPR-free data. *Cost:* circularity — I wrote both the fraud and the detector. Mitigated, not removed, by realistic legit look-alikes (new merchants, second-hand purchases, travel, rent, family transfers) and by a separate Kaggle sanity check (`scripts/benchmark_kaggle.py`).

**D2 — Unsupervised Isolation Forest [R18][R19] as the baseline.** Real fraud labels arrive weeks late and incomplete; an anomaly model works from day one on unlabelled traffic. Labels are used only on a held-out window to calibrate and choose thresholds. A supervised model is the natural challenger once analysts confirm `review` outcomes; the report includes an untuned gradient-boosting reference for scale.

**D3 — Stateful per-customer features.** "€4 800" means nothing; "€4 800 by Siirto to someone this customer has never paid, 40× their usual amount" is the signal. The store is in-memory for the demo. Production would use a keyed state store (Kafka Streams / Flink) or Redis, partitioned by customer id — which is why Kafka messages are keyed by customer.

**D4 — Learn only from approved payments, with a 24 h beneficiary cooling-off.** Without this, a blocked transfer would teach the profile that the mule's IBAN is a known payee, and an approved first APP-scam transfer would whitelist the mule for the second. Found through error analysis; it lifted APP-scam detection substantially (see the evaluation report).

**D5 — Compile the forest instead of calling `score_samples`.** scikit-learn costs ~30 ms per single-row call (Python loop over trees) — a third of the p99 < 100 ms budget that IPR's ≤ 10 s instant-payment window leaves us. Flattening the trees and walking all of them in ~10 vectorised numpy steps gives identical scores (tested to 1e-12) in ~0.05–0.4 ms. Batches still use scikit-learn, which is faster there.

**D6 — Isotonic, not Platt, calibration.** At a ~0.4 % base rate the logistic curve was badly under-confident in the tail: at the provisional review threshold of 60 it flagged only a third of fraud, while transactions it scored ≥ 20 were ~89 % fraud. Isotonic regression is monotone (ranking unchanged) and fits the actual shape.

**D7 — Thresholds 20 / 85, chosen on the calibration window.** Review ≥ 20 (one-in-five or better odds of fraud is worth an analyst's minute; ≈ 1 review case per 1 000 tx). Block > 85 (precision ≈ 98 % on test). The review band is the GDPR Art. 22 human-in-the-loop path [R9].

**D8 — Reason codes are descriptive rules, not SHAP.** Isolation Forest has no native attribution. Rules over the model's own features, ranked by surprisal in training data, tell an analyst or a disputing customer *what was unusual*. They do not claim to decompose the score; this is stated in the code and the report.

**D9 — Kafka consumer replays the topic on start.** Profiles are in memory, so on startup the API consumes from the earliest offset with a fresh group id: `replay=1` messages only warm profiles, live ones are scored. The log is the source of truth. Fine for a demo; production would checkpoint state instead of replaying history.

**D10 — Polling dashboard, no front-end build.** One static HTML file with vanilla JS polls `/api/events?since=N` every second. No bundler, no CDN, works offline; all user-supplied strings are rendered with `textContent`.

## 4. Non-functional properties

| Property | Status |
|---|---|
| Latency | p99 ≈ 1 ms in-process, ≈ 9 ms through HTTP on a laptop (target < 100 ms) |
| Throughput | Scoring is serialised by one lock: ≈ 1 900 tx/s in-process on a laptop (0.5 ms average, including Pydantic result building); scale out by partitioning on customer id |
| Reproducibility | Every number in the evaluation report regenerates from the seed; the Docker image trains at build time |
| Auditability | Each decision carries model version, reasons and feature values; streamed to `petosvahti.decisions` |
| Observability | `/health`, Prometheus `/metrics` (decisions, latency quantiles, model info) |
| Privacy | Synthetic data only; data and model files are git-ignored and docker-ignored |

## 5. Known gaps (deliberately out of scope)

- **No authentication or rate limiting** on the API — run it locally only.
- **No persistent decision store** — PostgreSQL audit log was planned; decisions currently go to Kafka and an in-memory ring buffer.
- **In-memory feature store** — lost on restart (rebuilt from Kafka replay in streaming mode).
- **No drift monitoring or retraining loop** — one stationary month of simulated behaviour.
- **Autoencoder challenger** — stretch goal, not started.
