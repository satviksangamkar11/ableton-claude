"""16.5.69.2-A3-18: Route dataclasses.

Separates three concerns that were previously implicit:
  - WHERE a mutation is written (mutation_route)
  - HOW audio behavior is measured (behavior_route)
  - Qualification status (from empirical observation)

mutation_route.adapter values:
  "cbor_body"   - write to CBOR body via pathmerge (most parameters)
  "host_param"  - write via synth.set_parameter() only; no CBOR path exists
  "cbor_string" - write a string field in CBOR body (e.g. wavetable path)
  "NOT_SUPPORTED" - adapter not yet implemented (architecture placeholder)

behavior_route.metric values:
  "overall_rms_db"       - broadband RMS energy
  "spectral_centroid_hz" - spectral centroid frequency
  "NOT_OBSERVABLE"       - no audio metric established (topology/modulation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class MutationRoute:
    """How a mutation is applied to the synthesizer state."""

    adapter: str
    path: Optional[str] = None
    host_param: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        valid = {"cbor_body", "host_param", "cbor_string", "NOT_SUPPORTED"}
        if self.adapter not in valid:
            raise ValueError("Unknown adapter: {!r}".format(self.adapter))
        if self.adapter == "cbor_body" and self.path is None:
            raise ValueError("cbor_body adapter requires path")
        if self.adapter == "cbor_string" and self.path is None:
            raise ValueError("cbor_string adapter requires path")
        if self.adapter == "host_param" and self.host_param is None:
            raise ValueError("host_param adapter requires host_param name")


@dataclass(frozen=True)
class BehaviorRoute:
    """How audio behavior causality is measured."""

    metric: str
    exercise_context: Tuple[Tuple[str, float], ...] = ()
    baseline_host_context: Tuple[Tuple[str, float], ...] = ()
    mutated_host_context: Tuple[Tuple[str, float], ...] = ()
    effect_threshold: Optional[float] = None
    notes: Optional[str] = None

    def __post_init__(self):
        valid = {"overall_rms_db", "spectral_centroid_hz", "NOT_OBSERVABLE"}
        if self.metric not in valid:
            raise ValueError("Unknown metric: {!r}".format(self.metric))

    @property
    def is_observable(self) -> bool:
        return self.metric != "NOT_OBSERVABLE"
