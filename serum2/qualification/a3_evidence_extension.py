"""16.5.69.2-A3-13: Evidence Record Extension for P1/P2/P3 Lifecycle

Extends EvidenceRecord to carry independent P1/P2/P3 persistence observations
while preserving backward compatibility with existing aggregate persistence.

This module provides:
1. PersistenceLifecycleEvidence dataclass
2. Integration pattern for EvidenceRecord extension
3. NOT_RUN sentinels for unexecuted lifecycles
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, Tuple

from serum2.qualification.a3_persistence_lifecycle import (
    P2PersistenceObservation,
    P3PersistenceObservation,
    P2_NOT_RUN,
    P3_NOT_RUN,
)


@dataclass(frozen=True)
class P1PersistenceObservation:
    """Same-lifecycle persistence: mutate → save → reload (same instance)."""

    status: str  # PASS | FAIL | NOT_RUN
    reason: Optional[str] = None
    target_value_before: Optional[Any] = None
    target_value_after_mutation: Optional[Any] = None
    target_value_after_reload: Optional[Any] = None
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


# NOT_RUN sentinel for P1
P1_NOT_RUN = P1PersistenceObservation(
    status="NOT_RUN",
    reason="P1 lifecycle test not executed (same-lifecycle persistence not measured)",
)


@dataclass(frozen=True)
class PersistenceLifecycleEvidence:
    """Container for independent P1/P2/P3 lifecycle observations.

    These are separate from the aggregate persistence_observation.
    Each represents an independently executed lifecycle test.
    """

    p1: P1PersistenceObservation = field(default_factory=lambda: P1_NOT_RUN)
    p2: P2PersistenceObservation = field(default_factory=lambda: P2_NOT_RUN)
    p3: P3PersistenceObservation = field(default_factory=lambda: P3_NOT_RUN)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "p1": {
                "status": self.p1.status,
                "reason": self.p1.reason,
                "target_value_before": self.p1.target_value_before,
                "target_value_after_mutation": self.p1.target_value_after_mutation,
                "target_value_after_reload": self.p1.target_value_after_reload,
            },
            "p2": {
                "status": self.p2.status,
                "reason": self.p2.reason,
                "fresh_instance_created": self.p2.fresh_instance_created,
            },
            "p3": {
                "status": self.p3.status,
                "reason": self.p3.reason,
                "process_boundary_crossed": self.p3.process_boundary_crossed,
            },
        }


def create_p1_observation(
    *,
    status: str,
    reason: str = None,
    target_value_before: Any = None,
    target_value_after_mutation: Any = None,
    target_value_after_reload: Any = None,
    details: Dict[str, Any] = None,
) -> P1PersistenceObservation:
    """Factory for P1 observations."""

    return P1PersistenceObservation(
        status=status,
        reason=reason,
        target_value_before=target_value_before,
        target_value_after_mutation=target_value_after_mutation,
        target_value_after_reload=target_value_after_reload,
        details=details or {},
    )


def create_evidence_record_extension(
    *,
    p1_observation: Optional[P1PersistenceObservation] = None,
    p2_observation: Optional[P2PersistenceObservation] = None,
    p3_observation: Optional[P3PersistenceObservation] = None,
) -> PersistenceLifecycleEvidence:
    """Factory for creating PersistenceLifecycleEvidence.

    Args:
        p1_observation: P1 lifecycle result (defaults to NOT_RUN)
        p2_observation: P2 lifecycle result (defaults to NOT_RUN)
        p3_observation: P3 lifecycle result (defaults to NOT_RUN)

    Returns:
        PersistenceLifecycleEvidence with lifecycle observations
    """

    return PersistenceLifecycleEvidence(
        p1=p1_observation or P1_NOT_RUN,
        p2=p2_observation or P2_NOT_RUN,
        p3=p3_observation or P3_NOT_RUN,
    )


# For backward compatibility with existing EvidenceRecord
# This is what old records will get when accessing persistence_lifecycle
DEFAULT_PERSISTENCE_LIFECYCLE = PersistenceLifecycleEvidence()
