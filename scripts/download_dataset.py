"""Download the Kaggle credit-card fraud dataset into data/ (S1.4).

Requires a Kaggle account and API token (~/.kaggle/kaggle.json):
https://www.kaggle.com/docs/api

Usage:
    pip install kaggle
    python scripts/download_dataset.py
"""

import subprocess
import sys
from pathlib import Path

DATASET = "mlg-ulb/creditcardfraud"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    target = DATA_DIR / "creditcard.csv"
    if target.exists():
        print(f"Already present: {target}")
        return 0
    cmd = ["kaggle", "datasets", "download", "-d", DATASET, "-p", str(DATA_DIR), "--unzip"]
    print(" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("Download failed — is your Kaggle API token configured?", file=sys.stderr)
        return result.returncode
    print(f"Done: {target} (git-ignored; never commit data files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
