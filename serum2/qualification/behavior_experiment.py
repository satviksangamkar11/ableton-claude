"""BehaviorExperiment — structured specification for a behavioral experiment.

What we want to run: target, context, intervention, measurement plan,
expected outcome. This is the specification layer, not execution.

Execution is separate (in experiment_orchestrator.py, which runs one
experiment in a fresh subprocess).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MeasurementPlan:
    """One measurement dimension to capture."""
    name: str                           # user-facing name (e.g., "spectral_centroid_hz")
    kernel: str                         # kernel function (e.g., "spectral_centroid")
    threshold: Optional[float] = None   # meaningful effect size for this dimension


@dataclass(frozen=True)
class BehaviorExperiment:
    """Specification for one behavioral experiment.

    What to run: target, context, intervention, measurement dimensions.
    How to interpret results: expected_outcome.

    This is NOT execution. Execution happens in experiment_orchestrator.py.
    """

    experiment_id: str

    # What we're testing
    semantic_target: str                # e.g., "Filter1.Cutoff"
    operation: str                      # e.g., "SET_PARAMETER"

    # Context (applied to BOTH arms identically)
    context: Dict[str, Any]             # e.g., {"Filter1On": 1.0}
    context_provenance: str             # why this context (e.g., "filter must be active")

    # Intervention (what differs between arms)
    baseline_override: Optional[Dict[str, Any]] = None  # CBOR path → value
    baseline_host_context: Optional[List[Tuple[str, float]]] = None  # host params for baseline arm
    treatment_cbor_path: Optional[str] = None  # CBOR path to mutate
    treatment_cbor_value: Optional[Any] = None  # treatment value
    treatment_host_context: Optional[List[Tuple[str, float]]] = None  # host params for treatment arm
    treatment_host_param_name: Optional[str] = None  # if mutating via host param
    treatment_host_param_value: Optional[float] = None  # host param treatment value

    # Measurements (what to capture from both renders)
    measurement_plan: Tuple[MeasurementPlan, ...] = field(default_factory=tuple)

    # Expectation
    expected_outcome: str               # EFFECT_OBSERVED | NO_OBSERVED_EFFECT | CONDITIONAL | UNKNOWN
    expected_direction: Optional[str] = None  # "increase" | "decrease" | "change" | None

    # Metadata
    notes: Optional[str] = None
    fx_preset_path: Optional[str] = None  # if using preset for FX context

    def validate(self) -> None:
        """Check internal consistency."""
        # Either CBOR or host_param mutation, not both
        cbor_mutation = self.treatment_cbor_path is not None
        host_param_mutation = self.treatment_host_param_name is not None

        if cbor_mutation and host_param_mutation:
            raise ValueError("Specify either CBOR path or host param, not both")

        if not (cbor_mutation or host_param_mutation):
            if self.baseline_override is None:
                raise ValueError("No mutation specified (CBOR, host_param, or baseline_override)")

        # Measurement plan required
        if not self.measurement_plan:
            raise ValueError("measurement_plan cannot be empty")

        # Expected outcome must be one of the known values
        valid_outcomes = {
            "EFFECT_OBSERVED",
            "NO_OBSERVED_EFFECT",
            "CONDITIONAL",
            "UNKNOWN",
            "AMBIGUOUS",
            "EXPERIMENT_FAILURE",
        }
        if self.expected_outcome not in valid_outcomes:
            raise ValueError(
                f"expected_outcome must be one of {valid_outcomes}, got {self.expected_outcome!r}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "experiment_id": self.experiment_id,
            "semantic_target": self.semantic_target,
            "operation": self.operation,
            "context": self.context,
            "context_provenance": self.context_provenance,
            "baseline_override": self.baseline_override,
            "baseline_host_context": self.baseline_host_context,
            "treatment_cbor_path": self.treatment_cbor_path,
            "treatment_cbor_value": self.treatment_cbor_value,
            "treatment_host_context": self.treatment_host_context,
            "treatment_host_param_name": self.treatment_host_param_name,
            "treatment_host_param_value": self.treatment_host_param_value,
            "measurement_plan": [
                {
                    "name": m.name,
                    "kernel": m.kernel,
                    "threshold": m.threshold,
                }
                for m in self.measurement_plan
            ],
            "expected_outcome": self.expected_outcome,
            "expected_direction": self.expected_direction,
            "notes": self.notes,
            "fx_preset_path": self.fx_preset_path,
        }
