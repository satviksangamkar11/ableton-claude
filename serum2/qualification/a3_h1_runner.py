"""16.5.69.2: A3 H1 Pilot Execution Runner

Loads resolved targets from the Phase 1 registry and executes the three H1 experiments.
"""

from __future__ import annotations

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


def run_h1_pilot_with_resolved_targets() -> None:
    """Execute H1 pilot experiments with resolved targets from Phase 1."""

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
    print("=" * 70)

    resolved_targets_dict = load_resolved_targets_from_registry(str(registry_path))
    print(f"\nLoaded {len(resolved_targets_dict)} resolved targets from Phase 1 registry")

    # Build H1 pilot plans
    plans = build_h1_pilot_plans()
    print(f"Built {len(plans)} H1 experiment plans:")

    for plan in plans:
        print(f"  - {plan.experiment_id}: {plan.claim_subject}")

    # Map each plan to its resolved target
    print("\n" + "-" * 70)
    print("Mapping H1 plans to resolved targets...")
    print("-" * 70 + "\n")

    target_mapping = []
    for plan in plans:
        semantic_id = plan.claim_subject
        if semantic_id not in resolved_targets_dict:
            print(f"ERROR: No resolved target for {semantic_id}")
            print(f"Available targets: {sorted(resolved_targets_dict.keys())}")
            raise RuntimeError(
                f"Semantic target '{semantic_id}' not in Phase 1 resolved registry"
            )

        resolved = resolved_targets_dict[semantic_id]
        target_mapping.append((plan, resolved))

        print(f"{semantic_id}:")
        print(f"  VST3: {resolved['vst3_name']} (index {resolved['vst3_index']})")
        print(f"  Capability: {resolved['capability_key']}")

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
    print(f"A3 H1 PILOT: {len(receipts)}/3 experiments completed")
    print("=" * 70 + "\n")

    return receipts


def main() -> int:
    """Entry point for H1 pilot runner."""

    try:
        receipts = run_h1_pilot_with_resolved_targets()
        return 0 if receipts else 1
    except Exception as e:
        print(f"\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
