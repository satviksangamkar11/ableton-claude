"""16.5.69.2-A3-12B/C: P2/P3 Persistence Lifecycle Observations

Extends A3 qualification with independent P2 (fresh instance) and P3 (fresh process)
persistence measurements.

These are separate from the aggregate persistence_observation in EvidenceRecord.
Each represents a distinct lifecycle test:

  P1: mutate → verify → save → reload (same instance)
  P2: mutate → verify → save → new instance → load
  P3: process A (mutate+save) → process B (load+inspect)

Critical: P1/P2/P3 results do NOT propagate. Each is independently measured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class P2PersistenceObservation:
    """Fresh-instance persistence: mutate → save → destroy → new instance → load.

    Represents whether a mutation persists across a fresh Serum instance
    created after serialization.
    """

    status: str  # PASS | FAIL | NOT_RUN
    reason: Optional[str] = None

    # Before mutation (baseline)
    target_value_before: Optional[Any] = None

    # After mutation in original instance
    target_value_after_mutation: Optional[Any] = None

    # After load into fresh instance
    target_value_in_fresh_instance: Optional[Any] = None

    # Metadata
    saved_state_identity: Optional[str] = None
    fresh_instance_created: bool = False
    fresh_instance_identity: Optional[str] = None

    # Details dict for additional context
    details: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.details is None:
            object.__setattr__(self, "details", {})

    @property
    def passed(self) -> bool:
        """P2 passes if value survived fresh instance load."""
        return self.status == "PASS"


@dataclass(frozen=True)
class P3PersistenceObservation:
    """Fresh-process persistence: process A (mutate+save) → process B (load+inspect).

    Represents whether a mutation persists across a process boundary.
    Process B is a genuinely separate Python process, not a reused instance.
    """

    status: str  # PASS | FAIL | NOT_RUN
    reason: Optional[str] = None

    # Before mutation (baseline)
    target_value_before: Optional[Any] = None

    # After mutation in process A
    target_value_after_mutation: Optional[Any] = None

    # After load in process B
    target_value_in_fresh_process: Optional[Any] = None

    # Metadata
    saved_state_identity: Optional[str] = None
    process_a_pid: Optional[int] = None
    process_b_pid: Optional[int] = None
    process_boundary_crossed: bool = False

    # Details dict for additional context
    details: dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.details is None:
            object.__setattr__(self, "details", {})

    @property
    def passed(self) -> bool:
        """P3 passes if value survived process boundary."""
        return self.status == "PASS"


def create_p2_observation(
    *,
    status: str,
    reason: str,
    target_value_before: Any = None,
    target_value_after_mutation: Any = None,
    target_value_in_fresh_instance: Any = None,
    saved_state_identity: str = None,
    fresh_instance_created: bool = False,
    fresh_instance_identity: str = None,
    details: dict[str, Any] = None,
) -> P2PersistenceObservation:
    """Factory for P2 observations."""

    return P2PersistenceObservation(
        status=status,
        reason=reason,
        target_value_before=target_value_before,
        target_value_after_mutation=target_value_after_mutation,
        target_value_in_fresh_instance=target_value_in_fresh_instance,
        saved_state_identity=saved_state_identity,
        fresh_instance_created=fresh_instance_created,
        fresh_instance_identity=fresh_instance_identity,
        details=details or {},
    )


def create_p3_observation(
    *,
    status: str,
    reason: str,
    target_value_before: Any = None,
    target_value_after_mutation: Any = None,
    target_value_in_fresh_process: Any = None,
    saved_state_identity: str = None,
    process_a_pid: int = None,
    process_b_pid: int = None,
    process_boundary_crossed: bool = False,
    details: dict[str, Any] = None,
) -> P3PersistenceObservation:
    """Factory for P3 observations."""

    return P3PersistenceObservation(
        status=status,
        reason=reason,
        target_value_before=target_value_before,
        target_value_after_mutation=target_value_after_mutation,
        target_value_in_fresh_process=target_value_in_fresh_process,
        saved_state_identity=saved_state_identity,
        process_a_pid=process_a_pid,
        process_b_pid=process_b_pid,
        process_boundary_crossed=process_boundary_crossed,
        details=details or {},
    )


# NOT_RUN sentinel for unexecuted lifecycle tests
P2_NOT_RUN = create_p2_observation(
    status="NOT_RUN",
    reason="P2 lifecycle test not executed (fresh instance persistence not measured)",
)

P3_NOT_RUN = create_p3_observation(
    status="NOT_RUN",
    reason="P3 lifecycle test not executed (fresh process persistence not measured)",
)
