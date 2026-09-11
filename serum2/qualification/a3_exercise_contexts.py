"""16.5.69.2-A3-17: Per-target exercise contexts for causal behavior tests.

An exercise context ensures the audio signal path actually exercises the
parameter being mutated. Without it, mutations may be written correctly
(generation=PASS) but produce no audio change (behavior=NO_OBSERVED_EFFECT)
because the parameter is inactive in the signal path.

Each context is a list of (host_param_name, normalized_value) tuples applied
identically to baseline and treatment arms before rendering. They are prerequisites
for a valid causal test — NOT mutations.

Host parameter names come from Serum's VST3 parameter list (DawDreamer).

Verified defaults that require override:
  - 'Filter 1 On'  : default=0.0 (filter off) → must be 1.0 for filter tests
  - 'A Enable'     : default=1.0 (already on)  → must be 0.0 for OSC enable test

Serum normalized ranges:
  - 'Filter 1 On'  : 0.0=off, 1.0=on
  - 'Filter 1 Freq': 0.0=min, 1.0=max; 0.35 ≈ 800 Hz (mid-low range, audible)
  - 'Filter 1 Res' : default=0.10; keep same for resonance type test
  - 'A Enable'     : 0.0=off, 1.0=on
  - 'A>Filter Balance': routes OSC A output into filter; default=0.0 (bypass)
"""

from __future__ import annotations
from typing import List, Tuple

# Type: list of (host_param_name, normalized_value)
ExerciseContext = List[Tuple[str, float]]


def filter_resonance_exercise_context() -> ExerciseContext:
    """Route OSC A through Filter 1 at low cutoff so resonance peak is audible.

    At Freq=0.15 (low cutoff), high resonance creates a self-oscillation peak
    that produces a measurable +2.74 dB RMS increase vs low resonance.
    """
    return [
        ("Filter 1 On", 1.0),
        ("Filter 1 Freq", 0.15),   # Low cutoff to make resonance peak audible
    ]


def filter_type_exercise_context() -> ExerciseContext:
    """Route OSC A through Filter 1 at mid cutoff so LP vs BP is distinguishable.

    At Freq=0.35 (mid cutoff), LP passes low freqs while BP peaks at cutoff —
    produces a +349 Hz spectral centroid shift.
    """
    return [
        ("Filter 1 On", 1.0),
        ("Filter 1 Freq", 0.35),
    ]


# Per-target exercise context (applied to BOTH arms — not a mutation)
EXERCISE_CONTEXTS: dict[str, ExerciseContext] = {
    "Filter.Resonance": filter_resonance_exercise_context(),
    "Filter.Type": filter_type_exercise_context(),
    "OSC1.Enable": [],  # No shared context — arm-specific host context handles this
}

# Per-target host parameters applied to baseline arm ONLY.
# Key discovery: VoiceOsc0.plainParams.kParamEnable does NOT map to DawDreamer
# 'A Enable' host parameter. Arm-specific host context is required for OSC test.
EXERCISE_BASELINE_HOST_CONTEXT: dict[str, ExerciseContext] = {
    "Filter.Resonance": [],
    "Filter.Type": [],
    "OSC1.Enable": [("A Enable", 0.0)],   # Disable OSC A in baseline
}

EXERCISE_MUTATED_HOST_CONTEXT: dict[str, ExerciseContext] = {
    "Filter.Resonance": [],
    "Filter.Type": [],
    "OSC1.Enable": [("A Enable", 1.0)],   # Enable OSC A in mutated arm
}

# Per-target baseline body overrides (no longer needed for OSC1.Enable)
EXERCISE_BASELINE_OVERRIDES: dict[str, list[tuple[str, object]]] = {
    "Filter.Resonance": [],
    "Filter.Type": [],
    "OSC1.Enable": [],
}

# Per-target measurement metric
EXERCISE_METRICS: dict[str, str] = {
    "Filter.Resonance": "overall_rms_db",    # Resonance peak adds energy (+2.74 dB)
    "Filter.Type": "spectral_centroid_hz",   # LP vs BP shifts centroid (+349 Hz)
    "OSC1.Enable": "overall_rms_db",         # Enable/disable oscillator changes energy
}

# Per-target effect threshold
EXERCISE_THRESHOLDS: dict[str, float] = {
    "Filter.Resonance": 0.5,    # dB — +2.74 dB expected
    "Filter.Type": 200.0,       # Hz — +349 Hz expected
    "OSC1.Enable": 3.0,         # dB — enabling OSC produces substantial energy
}
