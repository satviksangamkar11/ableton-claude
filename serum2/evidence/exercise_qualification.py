"""ExerciseQualification — binding between exercise evidence, frozen context, and target claim.

Phase 3c minimum-viable implementation for the Filter1.Cutoff pilot.

INVARIANT (from Phase 3b audit):
  Exercise evidence is NEVER reusable by default.
  scope='single_run_non_reusable' means this instance proves ONLY that
  target_semantic_id is exercisable when frozen_context is applied.
  It does NOT prove any other target is exercisable under the same context.

Schema design answers (Phase 3c):
  1. Who creates: pilot runner after run_behavior_test() returns CAUSAL_VERIFIED
  2. Who validates: ExerciseQualification.is_valid property
  3. Scope: 'single_run_non_reusable' — no auto-generalization
  4. Placement: Claim/Qualification layer; does NOT mutate EvidenceRecord
  5. ClaimGroup: not yet integrated (pilot scope)
  6. CapabilityContract: not yet integrated (pilot scope)
  7. Runtime Admission: not yet integrated (pilot scope)
  8. Invariants: empty context → invalid; non-EFFECT_OBSERVED → invalid
  9. Serialization: JSON via .to_dict(); backward compat: no existing records affected
  10. Kill gate: is_valid must be True before any downstream use
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, Optional

from serum2.evidence.record import CausalMeasurement, EFFECT_OBSERVED
from serum2.evidence.spec import SINGLE_FIELD


@dataclass(frozen=True)
class ExerciseQualification:
    """Records that a specific target was causally exercised in a specific context.

    frozen_context maps host parameter name → normalized value applied identically
    to both arms of the causal render test. This is the behavioral prerequisite:
    the signal path must be active for the mutation to be audible.

    scope must be 'single_run_non_reusable'. Future extensions may add explicit
    evidence-backed generalizations, but that requires a separate qualification step.
    """

    target_semantic_id: str           # e.g. "Filter.Cutoff"
    target_cbor_path: str             # e.g. "VoiceFilter0.plainParams.kParamFreq"
    frozen_context: Dict[str, float]  # host params applied to both arms
    mutation_value: Any               # treatment value (baseline = Serum default)
    causal_measurement: CausalMeasurement
    isolation_level: str              # must be SINGLE_FIELD
    scope: str                        # "single_run_non_reusable"
    experiment_id: str

    @property
    def is_valid(self) -> bool:
        """True only when all invariants hold:
        - EFFECT_OBSERVED was measured
        - Isolation is SINGLE_FIELD
        - Scope is non-reusable (anti-shortcut invariant)

        Note: frozen_context MAY be empty for always-active parameters
        (e.g. OSC1.Level — no special signal-path activation needed).
        The context is recorded as-is; emptiness is not itself a validity failure.
        """
        return (
            self.causal_measurement.status == EFFECT_OBSERVED
            and self.isolation_level == SINGLE_FIELD
            and self.scope == "single_run_non_reusable"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_semantic_id": self.target_semantic_id,
            "target_cbor_path": self.target_cbor_path,
            "frozen_context": self.frozen_context,
            "mutation_value": self.mutation_value,
            "causal_measurement": {
                "metric": self.causal_measurement.metric,
                "baseline": self.causal_measurement.baseline,
                "treatment": self.causal_measurement.treatment,
                "delta": self.causal_measurement.delta,
                "expected_direction": self.causal_measurement.expected_direction,
                "observed_direction": self.causal_measurement.observed_direction,
                "threshold": self.causal_measurement.threshold,
                "status": self.causal_measurement.status,
            },
            "isolation_level": self.isolation_level,
            "scope": self.scope,
            "experiment_id": self.experiment_id,
            "is_valid": self.is_valid,
        }


def make_exercise_qualification(
    *,
    target_semantic_id: str,
    target_cbor_path: str,
    frozen_context: Dict[str, float],
    mutation_value: Any,
    experiment_id: str,
    behavior_result: Dict[str, Any],
) -> ExerciseQualification:
    """Build an ExerciseQualification from a behavior test result dict.

    behavior_result must come from a2_behavior_harness.run_behavior_test().
    The causal_measurement is constructed from the observed metric values.
    """
    metric_name = behavior_result.get("metric_name", "spectral_centroid_hz")
    baseline = behavior_result.get("baseline_metric")
    treatment = behavior_result.get("mutated_metric")
    delta = (treatment - baseline) if (baseline is not None and treatment is not None) else None
    expected = behavior_result.get("expected_direction", "change")
    observed = behavior_result.get("observed_direction")
    status = behavior_result.get("status", "UNKNOWN")

    # Map behavior harness statuses to CausalMeasurement statuses
    if status in ("CAUSAL_VERIFIED", "EFFECT_OBSERVED"):
        cm_status = EFFECT_OBSERVED
    elif status == "NO_OBSERVED_EFFECT":
        from serum2.evidence.record import NO_OBSERVED_EFFECT
        cm_status = NO_OBSERVED_EFFECT
    elif status == "WRONG_DIRECTION":
        from serum2.evidence.record import WRONG_DIRECTION
        cm_status = WRONG_DIRECTION
    else:
        cm_status = "NOT_RUN"

    from serum2.evidence.record import MeasurementTarget
    measurement = CausalMeasurement(
        metric=metric_name,
        target=MeasurementTarget(
            field_path=target_cbor_path,
        ),
        baseline=baseline,
        treatment=treatment,
        delta=delta,
        expected_direction=expected,
        observed_direction=observed,
        threshold=behavior_result.get("effect_threshold"),
        status=cm_status,
        measurement_condition_signature=None,
        measurement_definition_id=None,
    )

    return ExerciseQualification(
        target_semantic_id=target_semantic_id,
        target_cbor_path=target_cbor_path,
        frozen_context=dict(frozen_context),
        mutation_value=mutation_value,
        causal_measurement=measurement,
        isolation_level=SINGLE_FIELD,
        scope="single_run_non_reusable",
        experiment_id=experiment_id,
    )
