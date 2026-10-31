"""Domain types shared by the generator, scoring core, API and stream adapters."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import uuid4
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

HELSINKI = ZoneInfo("Europe/Helsinki")
HOME_COUNTRY = "FI"


class Channel(StrEnum):
    """Payment rail the transaction travels on."""

    CARD = "card"
    ONLINE_BANK = "online_bank"
    SEPA_INSTANT = "sepa_instant"
    SIIRTO = "siirto"
    MOBILEPAY = "mobilepay"


# Rails where funds settle in seconds and cannot be recalled (IPR, ≤ 10 s).
INSTANT_CHANNELS = frozenset({Channel.SEPA_INSTANT, Channel.SIIRTO, Channel.MOBILEPAY})


class Transaction(BaseModel):
    """A payment attempt as seen by the scoring service.

    Deliberately carries no label: ground truth never reaches the model at
    scoring time (see `LabelledTransaction`).
    """

    model_config = ConfigDict(frozen=True)

    transaction_id: str = Field(default_factory=lambda: uuid4().hex, min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    timestamp: AwareDatetime
    amount_eur: float = Field(gt=0, le=1_000_000)
    channel: Channel
    payee_id: str = Field(min_length=1, max_length=64, description="IBAN or merchant id")
    payee_name: str = Field(min_length=1, max_length=120)
    country: str = Field(default=HOME_COUNTRY, pattern=r"^[A-Z]{2}$")
    device_id: str = Field(min_length=1, max_length=64)


class FraudPattern(StrEnum):
    """Fraud typologies the synthetic generator injects."""

    APP_SCAM = "app_scam"
    ACCOUNT_TAKEOVER = "account_takeover"
    CARD_TESTING = "card_testing"


@dataclass(frozen=True, slots=True)
class LabelledTransaction:
    """A generated transaction plus its synthetic ground truth."""

    transaction: Transaction
    fraud_pattern: FraudPattern | None = None

    @property
    def is_fraud(self) -> bool:
        return self.fraud_pattern is not None
