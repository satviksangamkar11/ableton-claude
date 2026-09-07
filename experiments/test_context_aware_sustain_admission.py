"""Test context-aware admission for Sustain prerequisite.

Tests all 8 cases of the admission matrix.
"""

import sys
import json
import pickle
from pathlib import Path

sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence import admission

def main():
    print("=" * 80)
    print("CONTEXT-AWARE SUSTAIN ADMISSION TESTS")
    print("=" * 80)
    print()

    # Load contracts
    contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

    # Find Sustain contract
    sustain = next((c for c in contracts.values() if c.target == "envelope_field_sustain"), None)
    if not sustain:
        print("ERROR: Sustain contract not found")
        return False

    print(f"Sustain Contract:")
    print(f"  Status: {sustain.status}")
    print(f"  Prerequisites: {sustain.prerequisites}")
    print(f"  Measurement ID: {sustain.measurement.get('measurement_definition_id') if sustain.measurement else None}")
    print()

    # Define admission test matrix
    mdid = sustain.measurement.get('measurement_definition_id') if sustain.measurement else None

    tests = [
        {
            "name": "Missing context",
            "target": "envelope_field_sustain",
            "kwargs": {"proposed_prerequisites_verified": None},
            "expect_admitted": False,
            "expect_reason": "prerequisite_unverified",
        },
        {
            "name": "Unverified context",
            "target": "envelope_field_sustain",
            "kwargs": {"proposed_prerequisites_verified": {"body:Env0.plainParams.kParamDecay": False}},
            "expect_admitted": False,
            "expect_reason": "prerequisite_unverified",
        },
        {
            "name": "Verified Decay=0.01 (wrong value)",
            "target": "envelope_field_sustain",
            "kwargs": {"proposed_prerequisites_verified": {"body:Env0.plainParams.kParamDecay": 0.01}},
            "expect_admitted": False,
            "expect_reason": "prerequisite_unverified",  # Value mismatch
        },
        {
            "name": "Verified Decay=0.03 (wrong value)",
            "target": "envelope_field_sustain",
            "kwargs": {"proposed_prerequisites_verified": {"body:Env0.plainParams.kParamDecay": 0.03}},
            "expect_admitted": False,
            "expect_reason": "prerequisite_unverified",  # Value mismatch
        },
        {
            "name": "Verified Decay=0.02 (correct)",
            "target": "envelope_field_sustain",
            "kwargs": {"proposed_prerequisites_verified": {"body:Env0.plainParams.kParamDecay": 0.02}, "required_measurement_definition_id": mdid},
            "expect_admitted": True,
            "expect_reason": "ADMITTED",
        },
        {
            "name": "Correct context + wrong measurement ID",
            "target": "envelope_field_sustain",
            "kwargs": {"proposed_prerequisites_verified": {"body:Env0.plainParams.kParamDecay": 0.02}, "required_measurement_definition_id": "wrong:deadbeef"},
            "expect_admitted": False,
            "expect_reason": "measurement_definition_mismatch",
        },
        {
            "name": "Unknown target Env1.FooBar",
            "target": "Env1.FooBar",
            "kwargs": {},
            "expect_admitted": False,
            "expect_reason": "unknown_no_contract",
        },
        {
            "name": "Unknown target Env0.Sustain",
            "target": "Env0.Sustain",
            "kwargs": {},
            "expect_admitted": False,
            "expect_reason": "unknown_no_contract",
        },
    ]

    results = []
    passed = 0
    failed = 0

    for test in tests:
        result = admission.admit(contracts, test["target"], **test["kwargs"])
        test_pass = (result.admitted == test["expect_admitted"] and result.reason == test["expect_reason"])

        status = "PASS" if test_pass else "FAIL"
        if test_pass:
            passed += 1
        else:
            failed += 1

        print(f"{status}: {test['name']}")
        print(f"     Expected: admitted={test['expect_admitted']}, reason={test['expect_reason']}")
        print(f"     Got:      admitted={result.admitted}, reason={result.reason}")

        results.append({
            "name": test["name"],
            "admitted": result.admitted,
            "reason": result.reason,
            "expected_admitted": test["expect_admitted"],
            "expected_reason": test["expect_reason"],
            "passed": test_pass,
        })

    print()
    print("=" * 80)
    print(f"RESULTS: {passed} PASS, {failed} FAIL out of {len(tests)}")
    print("=" * 80)

    # Check frontier
    old_contracts = contracts  # Already loaded
    status_counts = {}
    for c in old_contracts.values():
        status = c.status
        status_counts[status] = status_counts.get(status, 0) + 1

    print()
    print("Frontier Integrity:")
    print(f"  Total: {len(old_contracts)} (expected 37)")
    print(f"  CAUSAL_VERIFIED: {status_counts.get('CAUSAL_VERIFIED', 0)} (expected 26)")
    print(f"  STRUCTURAL_ONLY: {status_counts.get('STRUCTURAL_ONLY', 0)} (expected 8)")
    print(f"  NEGATIVE_EVIDENCE: {status_counts.get('NEGATIVE_EVIDENCE', 0)} (expected 3)")

    frontier_ok = (
        len(old_contracts) == 37 and
        status_counts.get('CAUSAL_VERIFIED') == 26 and
        status_counts.get('STRUCTURAL_ONLY') == 8 and
        status_counts.get('NEGATIVE_EVIDENCE') == 3
    )

    print()
    if failed == 0 and frontier_ok:
        print("DECISION: CONTEXT_AWARE_SUSTAIN_ADMISSION_VERIFIED")
        return True
    else:
        if failed > 0:
            print(f"BLOCKED: {failed} admission tests failed")
        if not frontier_ok:
            print("BLOCKED: Frontier integrity check failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
