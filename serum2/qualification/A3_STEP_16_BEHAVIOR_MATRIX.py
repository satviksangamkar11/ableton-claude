"""16.5.69.2-A3 Step 16: Causal Behavior Matrix

Actual measured results from real behavior execution on H1 targets.

Executed: 2026-09-11
Test suite: a3_step_16_behavior.py::test_step_16_behavior
Metric: overall_rms_db (broadband energy)
Stimulus: MIDI note 60, velocity 100, 1.5s note, 2.0s render

Key findings:
  - All three targets: NO_OBSERVED_EFFECT (delta=0.00 dB)
  - Renders succeeded for all arms (baseline_rendered=True, mutated_rendered=True)
  - NO_OBSERVED_EFFECT does NOT cascade to generation (generation still PASS)
  - Measurement setup: default Serum skeleton has filter bypassed/cutoff at max;
    VoiceFilter0.plainParams="default" => filter not in audio path by default.
    OSC1.Enable=True is default; enabling already-on oscillator produces no change.
  - This is a valid evidence-derived classification, not a test failure.
"""

STEP_16_BEHAVIOR_MATRIX = {
    "Filter.Resonance": {
        "semantic_id": "Filter.Resonance",
        "semantic_type": "SCALAR",
        "behavior": "NO_OBSERVED_EFFECT",
        "baseline_rendered": True,
        "mutated_rendered": True,
        "baseline_rms_db": -20.05,
        "mutated_rms_db": -20.05,
        "delta_db": 0.00,
        "metric": "overall_rms_db",
        "expected_direction": "change",
        "observed_direction": "none",
        "interpretation": (
            "Default Serum state has filter not actively routing through signal path "
            "(VoiceFilter0.plainParams='default' => filter bypassed or cutoff at max). "
            "Resonance mutation applied to state but produces no measurable RMS change. "
            "This is a measurement-setup limitation: broadband RMS is insensitive to "
            "filter resonance unless filter is actively in signal path."
        ),
    },
    "Filter.Type": {
        "semantic_id": "Filter.Type",
        "semantic_type": "ENUM",
        "behavior": "NO_OBSERVED_EFFECT",
        "baseline_rendered": True,
        "mutated_rendered": True,
        "baseline_rms_db": -20.05,
        "mutated_rms_db": -20.05,
        "delta_db": 0.00,
        "metric": "overall_rms_db",
        "expected_direction": "change",
        "observed_direction": "none",
        "interpretation": (
            "Filter type mutation (-> BP12) applied to state but produces no RMS change. "
            "Same root cause as Filter.Resonance: filter not in active signal path in "
            "default skeleton. A spectral centroid or bandpass energy metric over a "
            "filter-routed patch would detect this effect."
        ),
    },
    "OSC1.Enable": {
        "semantic_id": "OSC1.Enable",
        "semantic_type": "BOOLEAN",
        "behavior": "NO_OBSERVED_EFFECT",
        "baseline_rendered": True,
        "mutated_rendered": True,
        "baseline_rms_db": -20.05,
        "mutated_rms_db": -20.05,
        "delta_db": 0.00,
        "metric": "overall_rms_db",
        "expected_direction": "change",
        "observed_direction": "none",
        "interpretation": (
            "Mutation: Enable=True. Default Serum skeleton has OSC1 already enabled "
            "(Serum init patch has oscillator on by default). Enabling an already-enabled "
            "oscillator produces no change. A causal test would need baseline_override "
            "to explicitly disable OSC1 (Enable=False), then mutate to Enable=True."
        ),
    },
}

# Aggregate
STEP_16_SUMMARY = {
    "total_targets": 3,
    "causal_verified": 0,
    "no_observed_effect": 3,
    "wrong_direction": 0,
    "inconclusive": 0,
    "unknown": 0,
    "generation_gate": "ALL_PASS (3/3 - unchanged from Step 14)",
    "behavior_gate": "ALL_NO_OBSERVED_EFFECT (3/3)",
    "independence_confirmed": True,
    "key_finding": (
        "NO_OBSERVED_EFFECT for all three targets. "
        "This is a measurement-setup result: the default Serum skeleton state "
        "does not route audio through the filter or expose the OSC enable effect. "
        "Renders executed successfully; metric is valid but not sensitive to these "
        "mutations in this context. "
        "Behavior gate is independent: NO_OBSERVED_EFFECT does NOT cascade to "
        "generation, persistence, or restoration."
    ),
    "gate_independence_confirmed": (
        "OSC1.Enable: generation=PASS, p1=FAIL, p2=FAIL, p3=FAIL, "
        "restoration=PASS, behavior=NO_OBSERVED_EFFECT. "
        "No inter-gate inference. Each gate observed independently."
    ),
}


def get_behavior_status(semantic_id: str) -> dict:
    return STEP_16_BEHAVIOR_MATRIX.get(semantic_id)


if __name__ == "__main__":
    print("\nSTEP 16 BEHAVIOR MATRIX\n")
    for target_id, data in STEP_16_BEHAVIOR_MATRIX.items():
        print("{}:".format(target_id))
        print("  Type: {}".format(data["semantic_type"]))
        print("  Behavior: {}".format(data["behavior"]))
        print("  delta_db: {:.2f}".format(data["delta_db"]))
        print("  Interpretation: {}".format(data["interpretation"]))
        print()

    print("SUMMARY:")
    print("  behavior=NO_OBSERVED_EFFECT: {}".format(STEP_16_SUMMARY["no_observed_effect"]))
    print()
    print("KEY FINDING:")
    print("  {}".format(STEP_16_SUMMARY["key_finding"]))
    print()
    print("GATE INDEPENDENCE:")
    print("  {}".format(STEP_16_SUMMARY["gate_independence_confirmed"]))
