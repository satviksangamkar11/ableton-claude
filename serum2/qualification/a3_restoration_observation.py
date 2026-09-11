"""16.5.69.2-A3-15: Restoration Observation

Restoration is independent of persistence.

Lifecycle:
  1. Capture baseline state
  2. Apply mutation
  3. Verify mutation (generation gate)
  4. Restore baseline
  5. Read target value
  6. Verify target matches baseline (restoration gate)
  7. Verify no unintended collateral changes (collateral gate)

Restoration observation must not depend on P1/P2/P3 results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Dict


@dataclass(frozen=True)
class RestorationObservation:
    """Restoration lifecycle result: can baseline be restored after mutation?"""

    status: str  # PASS | FAIL | NOT_RUN
    reason: Optional[str] = None

    # Baseline state before mutation
    baseline_value: Optional[Any] = None

    # Target value after mutation (for verification)
    value_after_mutation: Optional[Any] = None

    # Target value after restoration attempt
    value_after_restore: Optional[Any] = None

    # Whether restoration matched baseline
    target_restored: bool = False
    collateral_restored: bool = False

    # Details dict
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


# NOT_RUN sentinel for unexecuted restoration tests
RESTORATION_NOT_RUN = RestorationObservation(
    status="NOT_RUN",
    reason="Restoration test not executed",
)


def create_restoration_observation(
    *,
    status: str,
    reason: str = None,
    baseline_value: Any = None,
    value_after_mutation: Any = None,
    value_after_restore: Any = None,
    target_restored: bool = False,
    collateral_restored: bool = False,
    details: Dict[str, Any] = None,
) -> RestorationObservation:
    """Factory for restoration observations."""

    return RestorationObservation(
        status=status,
        reason=reason,
        baseline_value=baseline_value,
        value_after_mutation=value_after_mutation,
        value_after_restore=value_after_restore,
        target_restored=target_restored,
        collateral_restored=collateral_restored,
        details=details or {},
    )
