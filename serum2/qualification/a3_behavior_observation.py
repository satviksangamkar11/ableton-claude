"""16.5.69.2-A3-16: Behavior / Causal Observation

Behavior gate is independent of all other gates. A receipt may have:

    Generation = PASS
    Persistence = FAIL
    Restoration = PASS
    Behavior = PASS

or:

    Generation = PASS
    Behavior = NO_OBSERVED_EFFECT

Neither combination produces any cascade into other gates.

Classifications (matches established evidence vocabulary):
    CAUSAL_VERIFIED      - mutation produced measurable, expected-direction effect
    NO_OBSERVED_EFFECT   - mutation did not produce detectable audio change
    WRONG_DIRECTION      - effect detected but opposite expected direction
    INCONCLUSIVE         - effect detected but direction/magnitude ambiguous
    UNKNOWN              - test could not execute (render error, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Dict


@dataclass(frozen=True)
class BehaviorObservation:
    """Single-target causal behavior observation."""

    status: str  # CAUSAL_VERIFIED | NO_OBSERVED_EFFECT | WRONG_DIRECTION | INCONCLUSIVE | UNKNOWN

    reason: Optional[str] = None

    # Raw audio metric values
    baseline_metric: Optional[float] = None
    mutated_metric: Optional[float] = None
    metric_name: Optional[str] = None

    # Expected direction: "increase" | "decrease" | "change" | None
    expected_direction: Optional[str] = None
    observed_direction: Optional[str] = None

    # Whether audio was produced
    baseline_rendered: bool = False
    mutated_rendered: bool = False

    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "CAUSAL_VERIFIED"

    @property
    def observed_effect(self) -> bool:
        return self.status not in ("NO_OBSERVED_EFFECT", "UNKNOWN")


# NOT_RUN sentinel — behavior test not yet executed
BEHAVIOR_NOT_RUN = BehaviorObservation(
    status="UNKNOWN",
    reason="Behavior test not executed",
)


def create_behavior_observation(
    *,
    status: str,
    reason: str = None,
    baseline_metric: float = None,
    mutated_metric: float = None,
    metric_name: str = None,
    expected_direction: str = None,
    observed_direction: str = None,
    baseline_rendered: bool = False,
    mutated_rendered: bool = False,
    details: Dict[str, Any] = None,
) -> BehaviorObservation:
    """Factory for behavior observations."""
    return BehaviorObservation(
        status=status,
        reason=reason,
        baseline_metric=baseline_metric,
        mutated_metric=mutated_metric,
        metric_name=metric_name,
        expected_direction=expected_direction,
        observed_direction=observed_direction,
        baseline_rendered=baseline_rendered,
        mutated_rendered=mutated_rendered,
        details=details or {},
    )
