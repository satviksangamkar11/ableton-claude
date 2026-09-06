"""Test that Env1.Release is properly registered and resolvable."""
import sys
import pickle
from pathlib import Path

sys.path.insert(0, r"d:\ableton claude")

from serum2.compiler.targets import resolve_semantic_target, resolve_path, SEMANTIC_TARGETS, TargetRefusal
from serum2.compiler import result
from serum2.compiler.kernel import dry_run

REPO_ROOT = Path(r"d:\ableton claude")
CONTRACTS_PATH = REPO_ROOT / "experiments" / "_capability_contracts.pkl"

def load_contracts():
    with open(CONTRACTS_PATH, "rb") as f:
        return pickle.load(f)

print("=" * 80)
print("16.5.52.A: Env1.Release Semantic Registration Test")
print("=" * 80)
print()

# Step 1: Check registration
print("[STEP 1] Check semantic target registration")
if "Env1.Release" in SEMANTIC_TARGETS:
    ref = SEMANTIC_TARGETS["Env1.Release"]
    print(f"  [PASS] Env1.Release registered")
    print(f"    - Semantic name: {ref.name}")
    print(f"    - Capability key: {ref.capability_key}")
else:
    print(f"  [FAIL] Env1.Release NOT registered")
    sys.exit(1)

print()

# Step 2: Load contracts and resolve
print("[STEP 2] Resolve semantic target to contract")
contracts = load_contracts()
resolved = resolve_semantic_target("Env1.Release", contracts)

if hasattr(resolved, 'ref'):  # ResolvedTarget
    print(f"  [PASS] Resolved successfully")
    print(f"    - Contract target: {resolved.contract.target}")
    print(f"    - Contract status: {resolved.contract.status}")
    print(f"    - Mutation path: {resolved.contract.scope.get('mutation_target_path')}")
    print(f"    - Prerequisites: {len(resolved.contract.prerequisites)}")
else:  # TargetRefusal
    print(f"  [FAIL] Resolution failed: {resolved.reason}")
    print(f"    - Detail: {resolved.detail}")
    sys.exit(1)

print()

# Step 3: Direct admission test via dry_run (no construct_and_verify)
print("[STEP 3] Test admission layer via dry_run (no Serum/harness)")

test_body = {
    "Env0": {
        "plainParams": {}
    }
}

# Reconstruct what produce() does up to dry_run()
resolved2 = resolve_semantic_target("Env1.Release", contracts)
if isinstance(resolved2, TargetRefusal):
    print(f"  [FAIL] Semantic resolution failed: {resolved2.reason}")
    sys.exit(1)

concrete_path = resolve_path(resolved2, test_body)
if concrete_path is None:
    print(f"  [FAIL] Path resolution failed (context not satisfied)")
    sys.exit(1)

# Now test dry_run directly (admission layer, no construct_and_verify)
dry_result = dry_run(
    [resolved2.ref.capability_key],
    contracts,
    base_body=test_body,
    requested_value_overrides=None,
)

if dry_result.accepted:
    print(f"  [PASS] Admission ACCEPTED for Env1.Release")
    print(f"    - Resolved path: {concrete_path}")
    print(f"    - Contract target: {resolved2.contract.target}")
    print(f"    - Execution mode: {dry_result.execution_mode}")
    print(f"    - Mutation plan entries: {len(dry_result.mutation_plan)}")
    if dry_result.mutation_plan:
        for path, val in dry_result.mutation_plan:
            print(f"      • {path} = {val}")
else:
    print(f"  [FAIL] Admission REFUSED: {dry_result.reason}")
    print(f"    - Detail: {dry_result.detail}")
    sys.exit(1)

print()
print("=" * 80)
print("[PASS] DECISION: ENV1_RELEASE_SEMANTIC_REGISTRATION_VERIFIED")
print("=" * 80)
