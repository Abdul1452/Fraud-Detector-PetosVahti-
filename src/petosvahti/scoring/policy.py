"""Decision policy: map a 0-100 risk score to a decision.

Thresholds are provisional; they get tuned with real evaluation data in S2.3
(threshold-tradeoff curve). The `REVIEW` class exists deliberately: it models
the GDPR Art. 22 human-in-the-loop requirement (see regulatory-context.md).
"""

from enum import StrEnum

APPROVE_BELOW: float = 60.0
BLOCK_ABOVE: float = 85.0


class Decision(StrEnum):
    """Outcome of scoring a transaction."""

    APPROVE = "approve"
    REVIEW = "review"
    BLOCK = "block"


def decide(risk_score: float) -> Decision:
    """Map a normalised risk score (0-100) to a decision.

    Args:
        risk_score: Normalised anomaly score, 0 (safe) to 100 (certain fraud).

    Raises:
        ValueError: If the score is outside [0, 100].
    """
    if not 0.0 <= risk_score <= 100.0:
        msg = f"risk_score must be within [0, 100], got {risk_score}"
        raise ValueError(msg)
    if risk_score < APPROVE_BELOW:
        return Decision.APPROVE
    if risk_score <= BLOCK_ABOVE:
        return Decision.REVIEW
    return Decision.BLOCK
