"""Runtime settings, from `PETOSVAHTI_*` environment variables (or `.env`)."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PETOSVAHTI_", env_file=".env", extra="ignore", protected_namespaces=()
    )

    model_path: Path = Path("models/fraud_model.joblib")
    auto_train: bool = Field(
        default=True, description="Train the quick model at startup if no artifact exists"
    )

    # Where transactions come from: in-process simulator, Kafka topic, or API calls only.
    source: Literal["simulator", "kafka", "none"] = "simulator"

    # Live simulator (demo). Fraud rate is higher than in training so attacks show up often.
    sim_customers: int = Field(default=500, ge=1)
    sim_seed: int = 7
    sim_rate: float = Field(default=4.0, gt=0, le=200, description="transactions per second")
    sim_history_days: int = Field(default=35, ge=0, description="warm-up history for profiles")
    sim_fraud_per_1000_per_day: float = Field(default=12.0, ge=0)

    kafka_bootstrap: str = "localhost:9092"
    kafka_transactions_topic: str = "petosvahti.transactions"
    kafka_decisions_topic: str = "petosvahti.decisions"
