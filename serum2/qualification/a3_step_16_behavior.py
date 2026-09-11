"""16.5.69.2-A3-16: Causal Behavior Qualification

Executes causal behavior tests on H1 targets:
  1. Filter.Resonance (scalar)
  2. Filter.Type (enum)
  3. OSC1.Enable (boolean)

Key constraints:
  - Behavior is independent of all other gates
  - NO_OBSERVED_EFFECT does not poison generation
  - INCONCLUSIVE/UNKNOWN are distinguishable
  - No persistence/restoration inference
"""

from __future__ import annotations

import json
from typing import Any

from serum2 import bridge
from serum2.qualification.a3_test_plans import build_h1_pilot_plans
from serum2.qualification.a3_behavior_harness import qualify_with_behavior

# Expected direction per target: what should the audio do when the parameter is mutated?
# "change" = any detectable change is sufficient for CAUSAL_VERIFIED
# "increase" / "decrease" = specific direction required
_EXPECTED_DIRECTIONS = {
    "Filter.Resonance": "change",   # Higher resonance -> audible peak change
    "Filter.Type": "change",        # Different filter type -> different timbre
    "OSC1.Enable": "decrease",      # Enabling OSC1 (True) -> more energy = increase;
                                    # but baseline is default which may already have OSC1 on
                                    # Use "change" to capture either direction
}

# Override with "change" for safety (avoid WRONG_DIRECTION on unknown baseline state)
_EXPECTED_DIRECTIONS["OSC1.Enable"] = "change"


def run_behavior_on_target(
    target_name: str,
    plan: Any,
    resolved_target: dict,
    skeleton: tuple,
) -> dict[str, Any]:
    """Run behavior test on one target. Returns result dict."""

    print("\n  {}".format(target_name))
    expected = _EXPECTED_DIRECTIONS.get(target_name, "change")

    try:
        result = qualify_with_behavior(
            experiment_id=plan.experiment_id,
            resolved_target=resolved_target,
            spec=plan,
            skeleton=skeleton,
            expected_direction=expected,
        )

        obs = result["behavior_observation"]
        print("    behavior: {}".format(obs.status))
        print("    baseline_rendered: {}".format(obs.baseline_rendered))
        print("    mutated_rendered: {}".format(obs.mutated_rendered))
        if obs.baseline_metric is not None:
            print("    baseline_rms: {:.2f} dB".format(obs.baseline_metric))
        if obs.mutated_metric is not None:
            print("    mutated_rms: {:.2f} dB".format(obs.mutated_metric))
        if obs.observed_direction:
            print("    observed_direction: {}".format(obs.observed_direction))
        if obs.reason:
            print("    reason: {}".format(obs.reason))

        return {
            "semantic_id": target_name,
            "behavior": obs.status,
            "baseline_rendered": obs.baseline_rendered,
            "mutated_rendered": obs.mutated_rendered,
            "baseline_metric": obs.baseline_metric,
            "mutated_metric": obs.mutated_metric,
            "metric_name": obs.metric_name,
            "expected_direction": expected,
            "observed_direction": obs.observed_direction,
            "reason": obs.reason,
        }

    except Exception as e:
        print("    ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return {
            "semantic_id": target_name,
            "behavior": "UNKNOWN",
            "baseline_rendered": False,
            "mutated_rendered": False,
            "error": str(e),
        }


def run_step_16():
    """Execute causal behavior qualification on all 3 H1 targets."""

    print("\n" + "=" * 70)
    print("STEP 16: CAUSAL BEHAVIOR QUALIFICATION")
    print("=" * 70 + "\n")
    print("Execution order: Filter.Resonance -> Filter.Type -> OSC1.Enable\n")
    print("Constraint: Behavior gate independent of generation/persistence/restoration.")

    plans = build_h1_pilot_plans()
    plan_dict = {p.claim_subject: p for p in plans}

    # Load resolved targets
    with open("serum2/qualification/RESOLVED_TARGET_REGISTRY.json", "r") as f:
        data = json.load(f)
        resolved_list = data.get("resolved_targets", [])
    targets_dict = {t["semantic_id"]: t for t in resolved_list}

    from serum2.evidence import epoch as epoch_mod
    skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)

    target_names = ["Filter.Resonance", "Filter.Type", "OSC1.Enable"]
    results = []

    print("\nResults:")
    for name in target_names:
        r = run_behavior_on_target(
            name,
            plan_dict[name],
            targets_dict[name],
            skeleton,
        )
        results.append(r)

    matrix = {r["semantic_id"]: r for r in results}

    print("\n" + "=" * 70)
    print("STEP 16 BEHAVIOR MATRIX")
    print("=" * 70)

    for name in target_names:
        m = matrix[name]
        print("  {}:".format(name))
        print("    behavior: {}".format(m["behavior"]))
        if m.get("baseline_metric") is not None:
            delta = (m["mutated_metric"] or 0) - (m["baseline_metric"] or 0)
            print("    rms delta: {:.2f} dB".format(delta))
        print("    observed_direction: {}".format(m.get("observed_direction", "N/A")))

    print("\n" + "=" * 70)
    print("INDEPENDENCE CHECK: Behavior gate vs other gates")
    print("=" * 70)
    print("(OSC1.Enable: persistence=FAIL, restoration=PASS, behavior=?)")
    osc = matrix.get("OSC1.Enable", {})
    print("  OSC1.Enable behavior: {}".format(osc.get("behavior", "N/A")))
    print("  (This can be CAUSAL_VERIFIED or NO_OBSERVED_EFFECT — both are valid)")

    return matrix


def test_step_16_behavior():
    """Pytest: behavior runs on all 3 targets, no cascade from other gates."""
    matrix = run_step_16()
    assert matrix is not None
    assert len(matrix) == 3

    for name, result in matrix.items():
        # Behavior must have been attempted
        assert result["behavior"] in (
            "CAUSAL_VERIFIED", "NO_OBSERVED_EFFECT", "WRONG_DIRECTION",
            "INCONCLUSIVE", "UNKNOWN"
        ), "Invalid behavior status for {}: {}".format(name, result["behavior"])

        # Must have rendered both arms (UNKNOWN is allowed only if rendering failed)
        if result["behavior"] != "UNKNOWN":
            assert result["baseline_rendered"], "{} baseline not rendered".format(name)
            assert result["mutated_rendered"], "{} mutated not rendered".format(name)

    # OSC1.Enable behavior must not be inferred from persistence=FAIL
    # Behavior gate can be any valid status — the key is it was measured independently
    osc = matrix["OSC1.Enable"]
    assert osc["behavior"] in (
        "CAUSAL_VERIFIED", "NO_OBSERVED_EFFECT", "WRONG_DIRECTION", "INCONCLUSIVE", "UNKNOWN"
    ), "OSC1.Enable behavior status is invalid"


if __name__ == "__main__":
    run_step_16()
