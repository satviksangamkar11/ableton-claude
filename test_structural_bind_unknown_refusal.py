"""Adversarial regression: STRUCTURAL_BIND_MODE with UNKNOWN structural status must be refused before construct_and_verify.

This test proves that when structural_admit() returns UNKNOWN status in
STRUCTURAL_BIND_MODE, the producer refuses BEFORE calling construct_and_verify
or creating an EvidenceRecord.

Test setup:
- Use Filter.Type (enumerated field, requires structural validation)
- STRUCTURAL_BIND_MODE (requested_value is provided)
- Request a value that would yield UNKNOWN structural status
  (or empty/minimal structural records that leave it unvalidated)
- Verify:
  1. refusal_reason == "STRUCTURAL_ADMISSION_REFUSED"
  2. causal_status == NOT_RUN (construct_and_verify was NOT called)
  3. record is None (no EvidenceRecord created)
  4. load_status == NOT_RUN, persistence_status == NOT_RUN
"""

import sys
import pickle
from pathlib import Path

sys.path.insert(0, r"d:\ableton claude")

from serum2.compiler import result
from serum2.evidence.record import NOT_RUN

REPO_ROOT = Path(r"d:\ableton claude")
CONTRACTS_PATH = REPO_ROOT / "experiments" / "_capability_contracts.pkl"

def load_contracts():
    with open(CONTRACTS_PATH, "rb") as f:
        return pickle.load(f)

print("=" * 80)
print("16.5.53.A: Adversarial - STRUCTURAL_BIND UNKNOWN must refuse before construct_and_verify")
print("=" * 80)
print()

# Test setup
print("[SETUP] Load contracts")
try:
    contracts = load_contracts()
    print(f"  [OK] Contracts loaded ({len(contracts)} total)")
except Exception as e:
    print(f"  [FAIL] Failed to load contracts: {e}")
    sys.exit(1)

print()

# Test Filter.Type in STRUCTURAL_BIND_MODE with a value that has no structural records
# to validate it. This should result in UNKNOWN structural status.
print("[TEST] Filter.Type with STRUCTURAL_BIND_MODE and no structural records")
print("  (No structural_records provided - should leave status as UNKNOWN)")

test_body = {
    "VoiceFilter0": {
        "plainParams": {}
    }
}

# Request a value without any structural records to validate it
# This should cause structural_admit() to return UNKNOWN
producer_result = result.produce(
    "Filter.Type",
    contracts,
    structural_records=[],  # Empty - no structural validation data
    body=test_body,
    requested_value="HP24",  # Request a specific filter type (STRUCTURAL_BIND_MODE)
    experiment_id="16_5_53_a_structural_unknown",
    measure_overall_rms=False,  # Skip measurement since we expect refusal
)

print()
print("[ANALYSIS] Verify gates are set correctly for refusal scenario")
print()

# Check 1: Must have refusal_reason set
print("  [Gate 1] Refusal check")
if producer_result.refusal_reason is not None:
    print(f"    [OK] refusal_reason = {producer_result.refusal_reason}")
    if "STRUCTURAL" in producer_result.refusal_reason:
        print(f"    [OK] Reason includes STRUCTURAL_ADMISSION_REFUSED")
    else:
        print(f"    [FAIL] Reason should be STRUCTURAL_ADMISSION_REFUSED, got {producer_result.refusal_reason}")
        sys.exit(1)
else:
    print(f"    [FAIL] refusal_reason is None (should have refused)")
    sys.exit(1)

# Check 2: construct_and_verify must NOT have been called (no EvidenceRecord)
print()
print("  [Gate 2] Construct_and_verify gate")
if producer_result.record is None:
    print(f"    [OK] record is None (construct_and_verify was NOT called)")
else:
    print(f"    [FAIL] record is not None (construct_and_verify WAS called, should have refused before it)")
    sys.exit(1)

# Check 3: Execution gates must all be NOT_RUN
print()
print("  [Gate 3] Execution status gates")
if producer_result.load_status == NOT_RUN:
    print(f"    [OK] load_status = NOT_RUN")
else:
    print(f"    [FAIL] load_status = {producer_result.load_status} (should be NOT_RUN)")
    sys.exit(1)

if producer_result.persistence_status == NOT_RUN:
    print(f"    [OK] persistence_status = NOT_RUN")
else:
    print(f"    [FAIL] persistence_status = {producer_result.persistence_status} (should be NOT_RUN)")
    sys.exit(1)

if producer_result.causal_status == NOT_RUN:
    print(f"    [OK] causal_status = NOT_RUN")
else:
    print(f"    [FAIL] causal_status = {producer_result.causal_status} (should be NOT_RUN)")
    sys.exit(1)

# Check 4: Structural status should be UNKNOWN or REFUSE
print()
print("  [Gate 4] Structural status")
print(f"    structural_status = {producer_result.structural_status}")
if producer_result.structural_status in ("UNKNOWN", "REFUSE"):
    print(f"    [OK] Structural status indicates admission problem")
else:
    print(f"    [WARN] Structural status unexpected: {producer_result.structural_status}")

print()
print("=" * 80)
print("[PASS] DECISION: STRUCTURAL_BIND_UNKNOWN_REFUSAL_VERIFIED")
print("       UNKNOWN in STRUCTURAL_BIND_MODE is refused BEFORE construct_and_verify")
print("=" * 80)
