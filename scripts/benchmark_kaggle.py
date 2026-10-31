"""Sanity-check the Isolation Forest on the public Kaggle credit-card set [R17].

The Kaggle data is PCA-anonymised (V1..V28 + Amount): no customer, payee,
device or rail, so the Petosvahti feature store cannot run on it. This script
answers a narrower question — does the same algorithm, with the same
hyper-parameters, find fraud in real (if anonymised) card data? — using a
time-ordered split and no labels during fitting.

Usage:
    python scripts/download_dataset.py      # needs a Kaggle API token
    python scripts/benchmark_kaggle.py [path/to/creditcard.csv]
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, roc_auc_score

from petosvahti.training import TrainConfig

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "creditcard.csv"


def main(csv: Path) -> int:
    if not csv.exists():
        print(f"{csv} not found — run scripts/download_dataset.py first.", file=sys.stderr)
        return 1
    df = pd.read_csv(csv).sort_values("Time")
    features = [c for c in df.columns if c.startswith("V")] + ["Amount"]
    x = df[features].to_numpy(dtype=np.float64, copy=True)
    x[:, -1] = np.log1p(x[:, -1])
    y = df["Class"].to_numpy(dtype=bool)

    split = int(len(df) * 0.6)  # first 60 % of the timeline trains, the rest tests
    cfg = TrainConfig()
    forest = IsolationForest(
        n_estimators=cfg.n_estimators, max_samples=cfg.max_samples, random_state=cfg.seed
    ).fit(x[:split])
    anomaly = -forest.score_samples(x[split:])
    y_test = y[split:]

    top = np.argsort(-anomaly)[: max(1, len(anomaly) // 100)]
    print(f"Kaggle credit-card benchmark — {len(df):,} tx, {y.mean():.3%} fraud")
    print(f"  test tx            {len(y_test):,} ({y_test.sum()} fraud)")
    print(f"  PR-AUC             {average_precision_score(y_test, anomaly):.3f}")
    print(f"  ROC-AUC            {roc_auc_score(y_test, anomaly):.3f}")
    print(f"  recall @ top 1 %   {y_test[top].sum() / max(y_test.sum(), 1):.1%}")
    print(f"  precision @ top 1% {y_test[top].mean():.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV))
