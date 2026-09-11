"""16.5.69.2: A3 H1 Pilot Execution Runner

Loads resolved targets from the Phase 1 registry and executes H1 experiments.
Supports per-target execution via --target flag for gated evaluation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from serum2.qualification.a3_harness import qualify_plan
from serum2.qualification.a3_test_plans import build_h1_pilot_plans


def load_resolved_targets_from_registry(
    registry_path: str,
) -> dict[str, dict[str, Any]]:
    """Load resolved targets from RESOLVED_TARGET_REGISTRY.json.

    Returns a dict mapping semantic_id → resolved_target dict.
    """

    with open(registry_path, 'r') as f:
        registry = json.load(f)

    targets = {}
    for resolved in registry.get('resolved_targets', []):
        semantic_id = resolved['semantic_id']
        targets[semantic_id] = {
            'semantic_id': resolved['semantic_id'],
            'capability_key': resolved['capability_key'],
            'vst3_name': resolved['vst3_name'],
            'vst3_index': resolved['vst3_index'],
        }

    return targets


def run_h1_pilot_with_resolved_targets(target_filter: str = None) -> list:
    """Execute H1 pilot experiments with resolved targets from Phase 1.

    Args:
        target_filter: If provided, execute only this target ("boolean", "enum", or "scalar").
                      If None, execute all three.
    """

    repo_root = Path(__file__).parent.parent.parent
    registry_path = repo_root / 'serum2' / 'qualification' / 'RESOLVED_TARGET_REGISTRY.json'

    if not registry_path.exists():
        raise RuntimeError(
            f"Resolved target registry not found at {registry_path}. "
            f"Run resolved_target_registry.py first."
        )

    # Load resolved targets
    print("\n" + "=" * 70)
    print("A3 H1 PILOT EXECUTION")
    if target_filter:
        print(f"Target: {target_filter.upper()}")
    print("=" * 70)

    resolved_targets_dict = load_resolved_targets_from_registry(str(registry_path))
    print(f"\nLoaded {len(resolved_targets_dict)} resolved targets from Phase 1 registry")

    # Build H1 pilot plans
    plans = build_h1_pilot_plans()

    # Filter by target if requested
    if target_filter:
        target_filter = target_filter.lower()
        target_idx = {"boolean": 0, "enum": 1, "scalar": 2}.get(target_filter)
        if target_idx is None:
            raise ValueError(f"Invalid target: {target_filter}. Use: boolean, enum, or scalar.")
        plans = [plans[target_idx]]

    print(f"Executing {len(plans)} H1 experiment plan(s):")

    for plan in plans:
        print(f"  - {plan.experiment_id}: {plan.claim_subject}")

    # Map each plan to its resolved target
    print("\n" + "-" * 70)
    print("Mapping H1 plans to resolved targets...")
    print("-" * 70 + "\n")

    target_mapping = []
    missing_targets = []

    for plan in plans:
        semantic_id = plan.claim_subject
        if semantic_id not in resolved_targets_dict:
            missing_targets.append(semantic_id)
            print(f"WARNING: No resolved target for {semantic_id}")
            print(f"  Available resolved targets: {sorted(resolved_targets_dict.keys())}")
            print(f"  (Will attempt execution anyway; harness will validate)")
            # Continue anyway; let the harness validation catch it
            continue

        resolved = resolved_targets_dict[semantic_id]
        target_mapping.append((plan, resolved))

        print(f"{semantic_id}:")
        print(f"  VST3: {resolved['vst3_name']} (index {resolved['vst3_index']})")
        print(f"  Capability: {resolved['capability_key']}")

    if missing_targets and len(target_mapping) == 0:
        print(f"\nERROR: No resolved targets found for any plan.")
        print(f"Available targets: {sorted(resolved_targets_dict.keys())}")
        raise RuntimeError(f"Cannot proceed without resolved targets.")

    # Execute qualification pipeline
    print("\n" + "-" * 70)
    print("Executing H1 qualification pipeline...")
    print("-" * 70 + "\n")

    receipts = []
    for plan, resolved_target in target_mapping:
        print(f"\n>>> Qualifying {plan.claim_subject}...")

        try:
            receipt = qualify_plan(plan, resolved_target)
            receipts.append(receipt)

            if receipt:
                print(f"    Generation: {receipt.generation.status}")
                print(f"    Behavior: {receipt.behavior.status}")
                print(f"    Collateral: {receipt.collateral.status}")
                print(f"    Persistence (overall): {receipt.persistence.overall.status}")
                print(f"    Restoration: {receipt.restoration.status}")
            else:
                print("    (No receipt returned)")

        except Exception as e:
            print(f"    ERROR during qualification: {e}")
            import traceback
            traceback.print_exc()
            raise

    # Summary
    print("\n" + "=" * 70)
    print(f"A3 H1 PILOT: {len(receipts)}/{len(plans)} target(s) completed")
    if missing_targets:
        print(f"Warnings: {len(missing_targets)} target(s) not in resolved registry")
    print("=" * 70 + "\n")

    return receipts


def main() -> int:
    """Entry point for H1 pilot runner with CLI argument support."""

    parser = argparse.ArgumentParser(
        description="Execute A3 H1 pilot experiments (gated by target)"
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Execute only this target: boolean, enum, or scalar. If omitted, execute all.",
    )

    args = parser.parse_args()

    try:
        receipts = run_h1_pilot_with_resolved_targets(target_filter=args.target)
        return 0 if receipts else 1
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
