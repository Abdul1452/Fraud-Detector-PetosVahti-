"""Scoring core: features, model wrapper, decision policy.

Framework-free by design (see architecture-overview.md): the FastAPI service
and the Kafka consumer are both thin adapters around this package.
"""

from petosvahti.scoring.policy import Decision, decide

__all__ = ["Decision", "decide"]
