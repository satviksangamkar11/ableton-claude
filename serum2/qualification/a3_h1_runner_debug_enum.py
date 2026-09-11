"""A3 H1 debug runner — ENUM variant."""

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
    """Load resolved targets from RESOLVED_TARGET_REGISTRY.json."""

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


def run_enum_and_dump() -> None:
    """Run ENUM H1 and dump complete artifacts."""

    repo_root = Path(__file__).parent.parent.parent
    registry_path = repo_root / 'serum2' / 'qualification' / 'RESOLVED_TARGET_REGISTRY.json'

    # Load registry
    resolved_targets_dict = load_resolved_targets_from_registry(str(registry_path))

    # Build ENUM plan only
    plans = build_h1_pilot_plans()
    enum_plan = plans[1]

    # Get resolved target
    semantic_id = enum_plan.claim_subject
    resolved_target = resolved_targets_dict[semantic_id]

    print("\n" + "=" * 70)
    print("A3 H1 ENUM PILOT — DEBUG OUTPUT")
    print("=" * 70)

    print("\n--- RESOLVED TARGET ---")
    print(json.dumps(resolved_target, indent=2))

    print("\n--- EXPERIMENT SPEC ---")
    spec_dict = {
        "experiment_id": enum_plan.experiment_id,
        "claim_subject": enum_plan.claim_subject,
        "claim_predicate": enum_plan.claim_predicate,
        "mutations": [
            {
                "target_path": m.target_path,
                "value": m.value,
                "provenance": m.provenance,
            }
            for m in enum_plan.mutations
        ],
        "prerequisites": enum_plan.prerequisites,
        "isolation_level": enum_plan.isolation_level,
    }
    print(json.dumps(spec_dict, indent=2))

    # Execute qualification
    print("\n--- EXECUTING QUALIFICATION ---")
    receipt = qualify_plan(enum_plan, resolved_target)

    print("\n--- MUTATION RECEIPT ---")
    receipt_dict = receipt.to_dict()
    print(json.dumps(receipt_dict, indent=2, default=str))

    print("\n--- RECEIPT GATE STATUS SUMMARY ---")
    print(f"Generation:       {receipt.generation.status}")
    print(f"Collateral:       {receipt.collateral.status}")
    print(f"Behavior:         {receipt.behavior.status}")
    print(f"Persistence.P1:   {receipt.persistence.p1_same_engine.status}")
    print(f"Persistence.P2:   {receipt.persistence.p2_new_instance.status}")
    print(f"Persistence.P3:   {receipt.persistence.p3_fresh_process.status}")
    print(f"Persistence.Overall: {receipt.persistence.overall.status}")
    print(f"Restoration:      {receipt.restoration.status}")

    print("\n--- RECEIPT DETAILED REASONS ---")
    print(f"\nGeneration reason:\n  {receipt.generation.reason}")
    print(f"\nCollateral reason:\n  {receipt.collateral.reason}")
    print(f"\nBehavior reason:\n  {receipt.behavior.reason}")
    print(f"\nPersistence.Overall reason:\n  {receipt.persistence.overall.reason}")

    print("\n--- PERSISTENCE DETAILS (enum value representation) ---")
    persistence_details = receipt.persistence.overall.details
    print(json.dumps(persistence_details, indent=2, default=str))

    print("\n--- GENERATION DETAILS (enum value verification) ---")
    generation_details = receipt.generation.details
    print(json.dumps(generation_details, indent=2, default=str))

    if receipt.notes:
        print(f"\nReceipt notes:")
        for note in receipt.notes:
            print(f"  - {note}")

    print("\n" + "=" * 70)
    print("END ENUM AUDIT")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        run_enum_and_dump()
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
