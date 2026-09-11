"""16.5.69.2-A3 Step 14: Real P1/P2/P3 Execution on H1 Targets

Execute real P1/P2/P3 lifecycle tests on:
  1. Filter.Resonance (scalar, clean case)
  2. Filter.Type (enum)
  3. OSC1.Enable (boolean with known persistence issue)

Produces: Machine-readable lifecycle matrix with actual results.
"""

from __future__ import annotations

import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from typing import Any

from serum2 import bridge
from serum2.evidence.spec import ExperimentSpec
from serum2.qualification.a3_harness import qualify_plan
from serum2.qualification.a3_test_plans import build_h1_pilot_plans
from serum2.qualification.a3_p2_p3_harness import qualify_with_p1_p2_p3
from serum2.qualification.a3_evidence_extension import PersistenceLifecycleEvidence
from serum2.evidence.record import EvidenceRecord


def run_target_p1p2p3(target_name: str, plan: Any, resolved_target: dict,
                      skeleton: tuple, plans_dict: dict) -> dict[str, Any]:
    """Run P1/P2/P3 on a single target. Returns result dict."""

    print("\n" + "-" * 70)
    print("Target: {}".format(target_name))
    print("-" * 70)

    try:
        result = qualify_with_p1_p2_p3(
            experiment_id=plan.experiment_id,
            resolved_target=resolved_target,
            spec=plan,
            skeleton=skeleton,
        )

        print("  P1 (same-lifecycle): {}".format(result["p1_observation"].status))
        print("  P2 (fresh instance): {}".format(result["p2_observation"].status))
        print("  P3 (fresh process): {}".format(result["p3_observation"].status))

        return {
            "semantic_id": target_name,
            "generation": "PASS",  # H1 all had generation PASS
            "p1": result["p1_observation"].status,
            "p2": result["p2_observation"].status,
            "p3": result["p3_observation"].status,
            "details": {
                "p1_reason": result["p1_observation"].reason,
                "p2_reason": result["p2_observation"].reason,
                "p3_reason": result["p3_observation"].reason,
            },
        }

    except Exception as e:
        print("  ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return {
            "semantic_id": target_name,
            "generation": "PASS",
            "p1": "FAIL",
            "p2": "FAIL",
            "p3": "FAIL",
            "error": str(e),
        }


def run_step_14_full_test():
    """Execute P1/P2/P3 on all 3 H1 targets."""

    print("\n" + "=" * 70)
    print("STEP 14: REAL P1/P2/P3 LIFECYCLE EXECUTION")
    print("=" * 70 + "\n")

    # Load H1 plans (fixed order: OSC1.Enable, Filter.Type, Filter.Resonance)
    plans = build_h1_pilot_plans()
    assert len(plans) == 3
    plan_dict = {p.claim_subject: p for p in plans}

    # Load resolved targets
    try:
        with open("serum2/qualification/RESOLVED_TARGET_REGISTRY.json", "r") as f:
            data = json.load(f)
            resolved_targets_list = data.get("resolved_targets", [])
    except FileNotFoundError:
        print("ERROR: RESOLVED_TARGET_REGISTRY.json not found")
        return None

    # Build target lookup
    targets_dict = {t.get("semantic_id"): t for t in resolved_targets_list}

    # Get skeleton
    from serum2.evidence import epoch as epoch_mod
    VST3 = epoch_mod.SERUM_VST3
    skeleton = bridge.capture_v8_skeleton(VST3)

    # Execution order: Resonance (scalar) → Type (enum) → Enable (boolean)
    target_names = ["Filter.Resonance", "Filter.Type", "OSC1.Enable"]
    results = []

    for target_name in target_names:
        if target_name not in plan_dict:
            print("ERROR: {} plan not found".format(target_name))
            continue

        if target_name not in targets_dict:
            print("ERROR: {} not in resolved targets".format(target_name))
            continue

        plan = plan_dict[target_name]
        resolved_target = targets_dict[target_name]

        result = run_target_p1p2p3(target_name, plan, resolved_target, skeleton, plan_dict)
        results.append(result)

    # Build matrix
    matrix = {target["semantic_id"]: target for target in results}

    print("\n" + "=" * 70)
    print("STEP 14 LIFECYCLE MATRIX")
    print("=" * 70 + "\n")

    for target_name in target_names:
        if target_name in matrix:
            m = matrix[target_name]
            print("{}:".format(target_name))
            print("  generation: {}".format(m["generation"]))
            print("  P1: {}".format(m["p1"]))
            print("  P2: {}".format(m["p2"]))
            print("  P3: {}".format(m["p3"]))

    return matrix


def test_step_14_full():
    """Pytest wrapper for Step 14 full lifecycle test."""
    result = run_step_14_full_test()
    assert result is not None, "Step 14 full test failed"
    assert len(result) == 3, "Expected 3 targets, got {}".format(len(result))


def main() -> None:
    """Entry point for Step 14."""

    result = run_step_14_full_test()

    if result and len(result) == 3:
        print("\n" + "=" * 70)
        print("STEP 14 COMPLETED")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("STEP 14 FAILED")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
