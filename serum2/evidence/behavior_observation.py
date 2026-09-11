"""BehaviorObservation — raw measurement capture from one experiment.

Records all measurements from a behavioral experiment WITHOUT interpretation.
Multiple measurement dimensions per observation. No causal claim, no semantic
meaning — just raw numbers and measurement metadata.

This is observation only. Interpretation happens at the BehaviorClaim layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from serum2.evidence.record import CausalMeasurement, MeasurementTarget


@dataclass(frozen=True)
class MeasurementDimension:
    """One measurement axis (e.g., spectral_centroid_hz, overall_rms_db)."""
    name: str                           # user-facing name
    kernel: str                         # which measurement function produced this
    baseline: Optional[float]           # value in baseline arm
    treatment: Optional[float]          # value in treatment arm
    delta: Optional[float]              # treatment - baseline
    threshold: Optional[float]          # was this difference meaningful?
    status: str                         # EFFECT_OBSERVED | NO_OBSERVED_EFFECT | etc.


@dataclass(frozen=True)
class BehaviorObservation:
    """Raw observation from a behavioral experiment.

    No interpretation. All measurements for this experiment, all contexts,
    all dimensions. The evidence layer: facts only.
    """

    experiment_id: str
    timestamp: str                      # ISO datetime when experiment ran
    semantic_target: str                # e.g., "Filter1.Cutoff"
    operation: str                      # e.g., "SET_PARAMETER"
    context: Dict[str, Any]             # host params, signal path config, etc.
    context_provenance: str             # why this context was chosen
    baseline_intervention: Dict[str, Any]  # baseline arm state
    treatment_intervention: Dict[str, Any] # treatment arm state
    baseline_rendered: bool
    treatment_rendered: bool
    isolation_level: str                # "single_field" (only one param differs)

    # Optional fields
    baseline_render_time_sec: Optional[float] = None
    treatment_render_time_sec: Optional[float] = None
    measurements: Tuple[MeasurementDimension, ...] = field(default_factory=tuple)
    execution_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON/storage."""
        return {
            "experiment_id": self.experiment_id,
            "timestamp": self.timestamp,
            "semantic_target": self.semantic_target,
            "operation": self.operation,
            "context": self.context,
            "context_provenance": self.context_provenance,
            "baseline_intervention": self.baseline_intervention,
            "treatment_intervention": self.treatment_intervention,
            "baseline_rendered": self.baseline_rendered,
            "treatment_rendered": self.treatment_rendered,
            "baseline_render_time_sec": self.baseline_render_time_sec,
            "treatment_render_time_sec": self.treatment_render_time_sec,
            "measurements": [
                {
                    "name": m.name,
                    "kernel": m.kernel,
                    "baseline": m.baseline,
                    "treatment": m.treatment,
                    "delta": m.delta,
                    "threshold": m.threshold,
                    "status": m.status,
                }
                for m in self.measurements
            ],
            "isolation_level": self.isolation_level,
            "execution_notes": self.execution_notes,
        }

    @property
    def any_dimension_passed(self) -> bool:
        """True if any measurement dimension shows EFFECT_OBSERVED."""
        return any(m.status == "EFFECT_OBSERVED" for m in self.measurements)

    @property
    def all_dimensions_passed(self) -> bool:
        """True if all measurements show EFFECT_OBSERVED."""
        if not self.measurements:
            return False
        return all(m.status == "EFFECT_OBSERVED" for m in self.measurements)

    @property
    def primary_measurement(self) -> Optional[MeasurementDimension]:
        """The first measurement dimension (often the one requested in the plan)."""
        return self.measurements[0] if self.measurements else None
