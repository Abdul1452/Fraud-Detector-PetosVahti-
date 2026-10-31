"""Human-readable reason codes for a score.

Isolation Forest has no native per-feature attribution, so reasons are
descriptive, model-agnostic rules over the same features the model sees,
ranked by how *rare* each condition was in training data (surprisal,
-ln p). They explain what is unusual about a transaction, which is what a
fraud analyst or a disputing customer needs; they are not SHAP values and do
not claim to decompose the score.
"""

import math
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from petosvahti.scoring.features import FeatureVector, as_dict

_LOG_500 = math.log1p(500.0)
_LOG_120S = math.log1p(120.0)


@dataclass(frozen=True, slots=True)
class ReasonRule:
    code: str
    description: str
    applies: Callable[[Mapping[str, float]], bool]


REASON_RULES: tuple[ReasonRule, ...] = (
    ReasonRule(
        "AMOUNT_UNUSUAL",
        "Amount far above this customer's usual spending",
        lambda f: f["amount_z"] >= 2.5,
    ),
    ReasonRule("NEW_PAYEE", "First payment to this payee", lambda f: f["new_payee"] > 0),
    ReasonRule(
        "NEW_DEVICE", "Initiated from an unrecognised device", lambda f: f["new_device"] > 0
    ),
    ReasonRule(
        "NEW_COUNTRY",
        "Initiated from a country not seen before for this customer",
        lambda f: f["new_country"] > 0,
    ),
    ReasonRule("NIGHT_TIME", "Initiated at night (00-06 Helsinki time)", lambda f: f["night"] > 0),
    ReasonRule(
        "HIGH_VELOCITY",
        "Fourth or later attempt within one hour",
        lambda f: f["tx_count_1h"] >= 3,
    ),
    ReasonRule(
        "RAPID_SUCCESSION",
        "Less than two minutes after the previous attempt",
        lambda f: f["log_secs_since_last"] < _LOG_120S,
    ),
    ReasonRule(
        "INSTANT_HIGH_VALUE",
        "High-value instant transfer: irrevocable within seconds",
        lambda f: f["instant_rail"] > 0 and f["log_amount"] >= _LOG_500,
    ),
)


class Reason(BaseModel):
    code: str
    description: str


def active_codes(features: FeatureVector) -> list[str]:
    named = as_dict(features)
    return [rule.code for rule in REASON_RULES if rule.applies(named)]


def base_rates(rows: Iterable[FeatureVector]) -> dict[str, float]:
    """Laplace-smoothed frequency of each reason in a reference population."""
    counts = dict.fromkeys((r.code for r in REASON_RULES), 0)
    total = 0
    for row in rows:
        total += 1
        for code in active_codes(row):
            counts[code] += 1
    return {code: (n + 1) / (total + 2) for code, n in counts.items()}


def explain(features: FeatureVector, rates: Mapping[str, float], limit: int = 4) -> list[Reason]:
    """Active reasons, rarest first."""
    by_code = {r.code: r for r in REASON_RULES}
    codes = sorted(active_codes(features), key=lambda c: -math.log(rates.get(c, 0.5)), reverse=True)
    return [Reason(code=c, description=by_code[c].description) for c in codes[:limit]]
