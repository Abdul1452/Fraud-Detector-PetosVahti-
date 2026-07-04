.PHONY: setup lint type test check data

setup:            ## create venv + install dev deps + pre-commit hooks
	python3.12 -m venv .venv && . .venv/bin/activate && \
	pip install -e ".[dev]" && pre-commit install

lint:
	ruff check . && ruff format --check .

type:
	mypy

test:
	pytest

check: lint type test  ## full local CI

data:
	python scripts/download_dataset.py
