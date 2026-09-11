"""BehaviorClaim — semantic interpretation of a BehaviorObservation.

One observation (raw measurements) can support multiple claims
(semantic interpretations). A claim is an interpretation layer saying:

"This observation (under this context) supports a claim about
a semantic relationship."

Claims are not evidence; evidence is observation. A claim uses
observation to make a grounded semantic statement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class BehaviorClaim:
    """Semantic interpretation of a behavioral observation.

    One observation can generate multiple claims if multiple semantic
    relationships are supported by the same measurement set.
    """

    # What evidence produced this claim
    observation_id: str                 # experiment_id from BehaviorObservation

    # Semantic relationship
    semantic_target: str                # e.g., "Filter1.Cutoff"
    predicate: str                      # e.g., "increases"
    semantic_object: str                # e.g., "spectral_brightness"

    # Measurement operationalization
    measurement_kernel: str             # which measurement supports this (e.g., "spectral_centroid_hz")
    measurement_baseline: Optional[float]
    measurement_treatment: Optional[float]
    measurement_delta: Optional[float]

    # Claim status
    status: str                         # PLAUSIBLE | PARTIALLY_GROUNDED | GROUNDED | CONDITIONAL
    condition: Optional[str] = None     # if CONDITIONAL, what context required?

    # Provenance
    context: Dict[str, Any] = None      # observation's context
    isolation_level: str = "single_field"

    # Confidence metadata
    confidence: Optional[float] = None  # 0.0–1.0 if quantifiable
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict."""
        return {
            "observation_id": self.observation_id,
            "semantic_target": self.semantic_target,
            "predicate": self.predicate,
            "semantic_object": self.semantic_object,
            "measurement_kernel": self.measurement_kernel,
            "measurement_baseline": self.measurement_baseline,
            "measurement_treatment": self.measurement_treatment,
            "measurement_delta": self.measurement_delta,
            "status": self.status,
            "condition": self.condition,
            "context": self.context,
            "isolation_level": self.isolation_level,
            "confidence": self.confidence,
            "notes": self.notes,
        }
