"""Tests for the decision policy (S1.2 smoke + first real unit tests)."""

import pytest

from petosvahti import __version__
from petosvahti.scoring import Decision, decide


def test_version() -> None:
    assert __version__ == "0.1.0"


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.0, Decision.APPROVE),
        (59.9, Decision.APPROVE),
        (60.0, Decision.REVIEW),
        (85.0, Decision.REVIEW),
        (85.1, Decision.BLOCK),
        (100.0, Decision.BLOCK),
    ],
)
def test_decide_thresholds(score: float, expected: Decision) -> None:
    assert decide(score) == expected


@pytest.mark.parametrize("score", [-0.1, 100.1, float("nan")])
def test_decide_rejects_out_of_range(score: float) -> None:
    with pytest.raises(ValueError, match="risk_score"):
        decide(score)
