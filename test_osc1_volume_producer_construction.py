"""Test OSC1.Volume through full producer construction path.

This is the first real producer construction test after the dry_run-only
registration series (16.5.52). It exercises:

  semantic intent (OSC1.Volume)
  -> semantic resolution (SEMANTIC_TARGETS lookup)
  -> path resolution (body context)
  -> admission (dry_run/prerequisite checks)
  -> construct_and_verify (actual Serum mutation)

The test captures and reports verification fields from construct_and_verify:
  - load_status (did Serum load the ExperimentSpec?)
  - persistence_status (did Serum persist the mutation to state?)
  - causal_status (did we observe the intended effect?)
  - measurement (what did we measure?)

No new EvidenceRecord is created or promoted to capability. The frontier
remains unchanged (37 contracts).
"""

import sys
import pickle
from pathlib import Path

sys.path.insert(0, r"d:\ableton claude")

from serum2.compiler import result
from serum2.compiler.targets import SEMANTIC_TARGETS

REPO_ROOT = Path(r"d:\ableton claude")
CONTRACTS_PATH = REPO_ROOT / "experiments" / "_capability_contracts.pkl"

def load_contracts():
    with open(CONTRACTS_PATH, "rb") as f:
        return pickle.load(f)

print("=" * 80)
print("16.5.53: OSC1.Volume Full Producer Construction Path Test")
print("=" * 80)
print()

# Step 1: Verify semantic target is registered
print("[STEP 1] Semantic target registration check")
if "OSC1.Volume" in SEMANTIC_TARGETS:
    ref = SEMANTIC_TARGETS["OSC1.Volume"]
    print(f"  [PASS] OSC1.Volume registered")
    print(f"    - Semantic name: {ref.name}")
    print(f"    - Capability key: {ref.capability_key}")
else:
    print(f"  [FAIL] OSC1.Volume NOT registered")
    sys.exit(1)

print()

# Step 2: Load contracts
print("[STEP 2] Load contracts")
try:
    contracts = load_contracts()
    print(f"  [PASS] Contracts loaded ({len(contracts)} total)")
except Exception as e:
    print(f"  [FAIL] Failed to load contracts: {e}")
    sys.exit(1)

print()

# Step 3: Call the full producer entrypoint (witness mode, no requested_value)
print("[STEP 3] Call producer.produce() with full construction path")
print("  (semantic resolution -> admission -> construct_and_verify)")

# Minimal body structure for Oscillator0
test_body = {
    "Oscillator0": {
        "plainParams": {}
    }
}

try:
    producer_result = result.produce(
        "OSC1.Volume",
        contracts,
        structural_records=[],
        body=test_body,
        requested_value=None,  # WITNESS_MODE
        experiment_id="16_5_53_osc1_volume_construction",
        measure_overall_rms=True,
    )
    print(f"  [PASS] produce() completed")
except Exception as e:
    print(f"  [FAIL] produce() raised exception: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Step 4: Analyze the result
print("[STEP 4] Analyze producer result (verification gates)")
print()

# 4a: Check semantic resolution
print("  [Resolution]")
if producer_result.resolved_ref is not None:
    print(f"    [OK] Semantic target resolved: {producer_result.resolved_ref.name}")
    print(f"    [OK] Capability key: {producer_result.resolved_ref.capability_key}")
else:
    print(f"    [FAIL] Semantic resolution failed")
    sys.exit(1)

# 4b: Check path resolution
print()
print("  [Path Resolution]")
if producer_result.resolved_path is not None:
    print(f"    [OK] Concrete path resolved: {producer_result.resolved_path}")
else:
    print(f"    [FAIL] Path resolution failed (context not satisfied)")
    sys.exit(1)

# 4c: Check for refusal (admission or structural)
print()
print("  [Admission Gate]")
if producer_result.refusal_reason is None:
    print(f"    [OK] No refusal (admission passed)")
    print(f"    [OK] Execution mode: {producer_result.execution_mode}")
else:
    print(f"    [FAIL] Admission REFUSED: {producer_result.refusal_reason}")
    print(f"    - Detail: {producer_result.refusal_detail}")
    sys.exit(1)

# 4d: Check construct_and_verify verification fields
print()
print("  [Construct & Verify Gates]")
print(f"    Load status:        {producer_result.load_status}")
print(f"    Persistence status: {producer_result.persistence_status}")
print(f"    Causal status:      {producer_result.causal_status}")

if producer_result.load_status == "PASS":
    print(f"      [OK] Load gate PASS")
else:
    print(f"      [FAIL] Load gate {producer_result.load_status}")

if producer_result.persistence_status == "PASS":
    print(f"      [OK] Persistence gate PASS")
else:
    print(f"      [FAIL] Persistence gate {producer_result.persistence_status}")

if producer_result.causal_status == "EFFECT_OBSERVED":
    print(f"      [OK] Causal gate PASS (effect observed)")
elif producer_result.causal_status == "NO_OBSERVED_EFFECT":
    print(f"      [WARN] Causal gate NO_OBSERVED_EFFECT (measurement completed but no delta)")
elif producer_result.causal_status == "NOT_RUN":
    print(f"      [WARN] Causal gate NOT_RUN (measurement not executed)")
else:
    print(f"      [FAIL] Causal gate {producer_result.causal_status}")

# 4e: Check measurement if available
print()
print("  [Measurement]")
if producer_result.measurement:
    m = producer_result.measurement
    print(f"    Metric: {m.get('metric')}")
    print(f"    Baseline: {m.get('baseline')}")
    print(f"    Treatment: {m.get('treatment')}")
    print(f"    Delta: {m.get('delta')}")
    print(f"    Status: {m.get('status')}")
else:
    print(f"    (No measurement available)")

# 4f: Check that an EvidenceRecord was created (construct_and_verify ran)
print()
print("  [EvidenceRecord]")
if producer_result.record is not None:
    print(f"    [OK] EvidenceRecord created by construct_and_verify")
    print(f"    - Experiment ID: {producer_result.record.experiment_id}")
else:
    print(f"    [FAIL] No EvidenceRecord (construct_and_verify did not run)")
    sys.exit(1)

print()

# Step 5: Final decision
print("=" * 80)
passed = (
    producer_result.resolved_ref is not None and
    producer_result.resolved_path is not None and
    producer_result.refusal_reason is None and
    producer_result.load_status == "PASS" and
    producer_result.persistence_status == "PASS" and
    producer_result.record is not None
)

if passed:
    print("[PASS] DECISION: OSC1_VOLUME_PRODUCER_CONSTRUCTION_VERIFIED")
    print("       Full path: semantic -> resolve -> admission -> construct_and_verify [OK]")
else:
    print("[FAIL] DECISION: OSC1_VOLUME_PRODUCER_CONSTRUCTION_INCOMPLETE")
    print("       One or more verification gates failed")
    sys.exit(1)

print("=" * 80)
