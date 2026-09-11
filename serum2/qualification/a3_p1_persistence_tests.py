"""16.5.69.2-A3-12A: P1 Persistence Lifecycle Qualification

P1 = resave/reload in same Serum lifecycle

Test sequence:
  baseline state
      ↓
  mutate target
      ↓
  verify mutation present
      ↓
  save state
      ↓
  resave (reload from same save)
      ↓
  verify target persisted
      ↓
  result: PASS / FAIL / INCONCLUSIVE

Critical: P1 is measured independently from P2/P3.
No propagation: P1 PASS does not imply P2 PASS.
"""

from __future__ import annotations

import json
from typing import Any

from serum2.qualification.a3_test_plans import build_h1_pilot_plans
from serum2.qualification.a3_harness import qualify_plan


def load_resolved_targets_from_registry() -> dict[str, dict[str, Any]]:
    """Load Phase 1 resolved targets."""
    from pathlib import Path
    import json

    registry_path = (
        Path(__file__).parent.parent.parent
        / "serum2"
        / "qualification"
        / "RESOLVED_TARGET_REGISTRY.json"
    )

    with open(registry_path) as f:
        registry = json.load(f)

    targets = {}
    for resolved in registry.get("resolved_targets", []):
        semantic_id = resolved["semantic_id"]
        targets[semantic_id] = {
            "semantic_id": resolved["semantic_id"],
            "capability_key": resolved["capability_key"],
            "vst3_name": resolved["vst3_name"],
            "vst3_index": resolved["vst3_index"],
        }

    return targets


def run_p1_lifecycle_tests() -> dict[str, dict[str, Any]]:
    """Run P1 persistence tests on the three H1 targets.

    Returns a matrix of results:
      {
        "OSC1.Enable": { "p1_status": "...", "details": ... },
        "Filter.Type": { "p1_status": "...", "details": ... },
        "Filter.Resonance": { "p1_status": "...", "details": ... },
      }
    """

    resolved_targets = load_resolved_targets_from_registry()
    plans = build_h1_pilot_plans()

    results = {}

    print("\n" + "=" * 70)
    print("A3 P1 PERSISTENCE LIFECYCLE TESTS")
    print("=" * 70)

    for plan in plans:
        semantic_id = plan.claim_subject

        if semantic_id not in resolved_targets:
            print("\nWARNING: {} not in resolved registry".format(semantic_id))
            continue

        resolved_target = resolved_targets[semantic_id]

        print("\n--- {} ---".format(semantic_id))
        print("VST3: {} (index {})".format(
            resolved_target["vst3_name"],
            resolved_target["vst3_index"]
        ))

        # Run the qualification (which includes persistence observation)
        try:
            receipt = qualify_plan(plan, resolved_target)

            # Extract P1 result from the receipt
            p1_status = receipt.persistence.p1_same_engine.status
            p1_reason = receipt.persistence.p1_same_engine.reason

            # Also capture overall persistence as reference
            overall_status = receipt.persistence.overall.status

            results[semantic_id] = {
                "p1_status": p1_status,
                "p1_reason": p1_reason,
                "overall_persistence": overall_status,
                "overall_reason": receipt.persistence.overall.reason,
                "generation": receipt.generation.status,
                "collateral": receipt.collateral.status,
            }

            print("P1 Result: {}".format(p1_status))
            print("  Reason: {}".format(p1_reason))
            print("Overall Persistence: {}".format(overall_status))
            print("  Reason: {}".format(receipt.persistence.overall.reason))

        except Exception as e:
            print("ERROR: {}".format(e))
            import traceback
            traceback.print_exc()
            results[semantic_id] = {
                "p1_status": "ERROR",
                "error": str(e),
            }

    # Summary
    print("\n" + "=" * 70)
    print("P1 PERSISTENCE RESULTS MATRIX")
    print("=" * 70)

    print("\nTarget".ljust(25) + "P1 Status".ljust(15) + "Overall".ljust(15) + "Generation")
    print("-" * 70)

    for semantic_id, result in results.items():
        print(
            semantic_id.ljust(25)
            + result.get("p1_status", "?").ljust(15)
            + result.get("overall_persistence", "?").ljust(15)
            + result.get("generation", "?")
        )

    print("\n" + "=" * 70)
    print("END P1 LIFECYCLE TESTS")
    print("=" * 70 + "\n")

    return results


def main() -> None:
    """Entry point for P1 persistence lifecycle tests."""

    results = run_p1_lifecycle_tests()

    # Print results as JSON for further processing
    print("\nP1 Results JSON:")
    print(json.dumps(results, indent=2))

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
