"""16.5.69.2-A3-15: Formal Restoration Qualification

Execute restoration tests on:
  1. Filter.Resonance (scalar)
  2. Filter.Type (enum)
  3. OSC1.Enable (boolean — persistence FAIL, restoration must be measured independently)

Key constraint: OSC1.Enable persistence=FAIL must NOT automatically make restoration=FAIL.
"""

from __future__ import annotations

import json
from typing import Any

from serum2 import bridge
from serum2.qualification.a3_test_plans import build_h1_pilot_plans
from serum2.qualification.a3_restoration_harness import qualify_with_restoration


def run_restoration_on_target(
    target_name: str,
    plan: Any,
    resolved_target: dict,
    skeleton: tuple,
) -> dict[str, Any]:
    """Run restoration on one target. Returns result dict."""

    print("\n  {}".format(target_name))

    try:
        result = qualify_with_restoration(
            experiment_id=plan.experiment_id,
            resolved_target=resolved_target,
            spec=plan,
            skeleton=skeleton,
        )

        obs = result["restoration_observation"]
        print("    restoration: {}".format(obs.status))
        print("    target_restored: {}".format(obs.target_restored))
        print("    collateral_restored: {}".format(obs.collateral_restored))
        if obs.reason:
            print("    reason: {}".format(obs.reason))

        return {
            "semantic_id": target_name,
            "restoration": obs.status,
            "target_restored": obs.target_restored,
            "collateral_restored": obs.collateral_restored,
            "baseline_value": obs.baseline_value,
            "value_after_restore": obs.value_after_restore,
            "reason": obs.reason,
        }

    except Exception as e:
        print("    ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return {
            "semantic_id": target_name,
            "restoration": "FAIL",
            "target_restored": False,
            "collateral_restored": False,
            "error": str(e),
        }


def run_step_15():
    """Execute restoration qualification on all 3 H1 targets."""

    print("\n" + "=" * 70)
    print("STEP 15: FORMAL RESTORATION QUALIFICATION")
    print("=" * 70 + "\n")
    print("Execution order: Filter.Resonance -> Filter.Type -> OSC1.Enable\n")
    print("Constraint: OSC1.Enable persistence=FAIL does NOT poison restoration.")

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
        r = run_restoration_on_target(
            name,
            plan_dict[name],
            targets_dict[name],
            skeleton,
        )
        results.append(r)

    matrix = {r["semantic_id"]: r for r in results}

    print("\n" + "=" * 70)
    print("STEP 15 RESTORATION MATRIX")
    print("=" * 70)

    for name in target_names:
        m = matrix[name]
        print("  {}:".format(name))
        print("    restoration: {}".format(m["restoration"]))
        print("    target_restored: {}".format(m["target_restored"]))
        print("    collateral_restored: {}".format(m["collateral_restored"]))

    return matrix


def test_step_15_restoration():
    """Pytest: restoration runs successfully on all 3 targets."""
    matrix = run_step_15()
    assert matrix is not None
    assert len(matrix) == 3


if __name__ == "__main__":
    run_step_15()
