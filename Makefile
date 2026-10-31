.PHONY: setup lint type test check data train report demo serve docker

setup:            ## create venv + install dev deps + pre-commit hooks
	python3.12 -m venv .venv && . .venv/bin/activate && \
	pip install -e ".[dev,stream]" && pre-commit install

lint:
	ruff check . && ruff format --check .

type:
	mypy

test:
	pytest

check: lint type test  ## full local CI

data:
	python scripts/download_dataset.py

train:            ## simulate, train, replay-evaluate -> models/fraud_model.joblib
	petosvahti train

report:           ## train + regenerate the committed evaluation report
	petosvahti train --report docs/05-evaluation/model-evaluation-v1.md

demo:             ## live dashboard with the in-process simulator (trains first if needed)
	petosvahti demo

serve:
	petosvahti serve

docker:           ## Kafka + producer + API in Docker -> http://localhost:8000
	docker compose up --build
