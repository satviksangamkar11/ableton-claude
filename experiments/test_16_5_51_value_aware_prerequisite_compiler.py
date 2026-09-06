"""16.5.51: Compiler integration test for value-aware prerequisite verification.

Proves the REAL compiler chain obtains actual values from the supplied body
and passes value-bearing representation into admission. Tests all 5 context outcomes:

1. missing context (proposed_prerequisites_verified=None, base_body=None)
   → REFUSED prerequisite_unverified
2. unverified context (base_body has Decay=0.01)
   → REFUSED prerequisite_unverified (value mismatch)
3. wrong value Decay=0.01
   → REFUSED prerequisite_unverified (value mismatch)
4. wrong value Decay=0.03
   → REFUSED prerequisite_unverified (value mismatch)
5. correct value Decay=0.02
   → ADMITTED
"""

import sys
import json
import pickle
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, r"D:\ableton claude")

from serum2.compiler import kernel, result, context as ctx_mod
from serum2.evidence import admission as adm

REPO_ROOT = Path(r"D:\ableton claude")
CONTRACTS_PATH = REPO_ROOT / "experiments" / "_capability_contracts.pkl"


@dataclass(frozen=True)
class CompilerTestResult:
    name: str
    scenario: str
    outcome: str  # "REFUSED" | "ADMITTED"
    reason: str  # detailed refusal reason or "ADMITTED"
    passed: bool


def load_contracts():
    """Load capability contracts."""
    with open(CONTRACTS_PATH, "rb") as f:
        return pickle.load(f)


def make_test_body(decay_value):
    """Construct a minimal Serum state body with Env0.plainParams.kParamDecay."""
    return {
        "Env0": {
            "plainParams": {
                "kParamDecay": decay_value,
            }
        }
    }


def test_case_1_missing_context():
    """Missing context: no base_body, no proposed_prerequisites_verified.
    Expected: REFUSED prerequisite_unverified
    """
    contracts = load_contracts()
    targets = ["envelope_field_sustain"]

    result = kernel.dry_run(
        targets, contracts,
        base_body=None,
        proposed_prerequisites_verified=None,
    )

    passed = not result.accepted and result.reason == kernel.REFUSED_ADMISSION
    return CompilerTestResult(
        name="Case 1: Missing Context",
        scenario="base_body=None, proposed=None",
        outcome="REFUSED" if not result.accepted else "ADMITTED",
        reason=result.detail if not result.accepted else "unexpected admission",
        passed=passed,
    )


def test_case_2_unverified_context():
    """Unverified context: base_body supplied but has wrong value Decay=0.01.
    Expected: REFUSED prerequisite_unverified
    """
    contracts = load_contracts()
    targets = ["envelope_field_sustain"]
    body = make_test_body(0.01)

    # No proposed_prerequisites_verified, so compiler extracts from body
    result = kernel.dry_run(
        targets, contracts,
        base_body=body,
        proposed_prerequisites_verified=None,
    )

    passed = not result.accepted and result.reason == kernel.REFUSED_ADMISSION
    return CompilerTestResult(
        name="Case 2: Unverified Value (Decay=0.01)",
        scenario="base_body with Decay=0.01, proposed=None",
        outcome="REFUSED" if not result.accepted else "ADMITTED",
        reason=result.detail if not result.accepted else "unexpected admission",
        passed=passed,
    )


def test_case_3_wrong_value_0_01():
    """Caller explicitly passes wrong value Decay=0.01 in proposed_prerequisites_verified.
    Expected: REFUSED prerequisite_unverified
    """
    contracts = load_contracts()
    targets = ["envelope_field_sustain"]

    result = kernel.dry_run(
        targets, contracts,
        base_body=None,
        proposed_prerequisites_verified={"Env0.plainParams.kParamDecay": 0.01},
    )

    passed = not result.accepted and result.reason == kernel.REFUSED_ADMISSION
    return CompilerTestResult(
        name="Case 3: Caller Provided Wrong Value (0.01)",
        scenario="proposed={Decay: 0.01}",
        outcome="REFUSED" if not result.accepted else "ADMITTED",
        reason=result.detail if not result.accepted else "unexpected admission",
        passed=passed,
    )


def test_case_4_wrong_value_0_03():
    """Caller explicitly passes wrong value Decay=0.03 in proposed_prerequisites_verified.
    Expected: REFUSED prerequisite_unverified
    """
    contracts = load_contracts()
    targets = ["envelope_field_sustain"]

    result = kernel.dry_run(
        targets, contracts,
        base_body=None,
        proposed_prerequisites_verified={"Env0.plainParams.kParamDecay": 0.03},
    )

    passed = not result.accepted and result.reason == kernel.REFUSED_ADMISSION
    return CompilerTestResult(
        name="Case 4: Caller Provided Wrong Value (0.03)",
        scenario="proposed={Decay: 0.03}",
        outcome="REFUSED" if not result.accepted else "ADMITTED",
        reason=result.detail if not result.accepted else "unexpected admission",
        passed=passed,
    )


def test_case_5_correct_value():
    """Correct value Decay=0.02 in base_body.
    Compiler extracts it and passes to admission.
    Expected: ADMITTED
    """
    contracts = load_contracts()
    targets = ["envelope_field_sustain"]
    body = make_test_body(0.02)

    result = kernel.dry_run(
        targets, contracts,
        base_body=body,
        proposed_prerequisites_verified=None,
    )

    passed = result.accepted
    return CompilerTestResult(
        name="Case 5: Correct Value (Decay=0.02)",
        scenario="base_body with Decay=0.02, proposed=None",
        outcome="ADMITTED" if result.accepted else "REFUSED",
        reason=result.detail if result.accepted else result.detail,
        passed=passed,
    )


def main():
    print("=" * 80)
    print("16.5.51: VALUE-AWARE PREREQUISITE VERIFICATION COMPILER TEST")
    print("=" * 80)
    print()

    results = []
    tests = [
        test_case_1_missing_context,
        test_case_2_unverified_context,
        test_case_3_wrong_value_0_01,
        test_case_4_wrong_value_0_03,
        test_case_5_correct_value,
    ]

    for test_fn in tests:
        try:
            result = test_fn()
            results.append(result)
            status = "[PASS] PASS" if result.passed else "[FAIL] FAIL"
            print(f"{status}: {result.name}")
            print(f"     Scenario: {result.scenario}")
            print(f"     Outcome:  {result.outcome}")
            print(f"     Detail:   {result.reason[:100]}...")
            print()
        except Exception as e:
            print(f"[FAIL] ERROR: {test_fn.__name__}")
            print(f"     Exception: {e}")
            results.append(CompilerTestResult(
                name=test_fn.__name__,
                scenario="(error)",
                outcome="ERROR",
                reason=str(e),
                passed=False,
            ))
            print()

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print("=" * 80)
    print(f"RESULTS: {passed} PASS, {failed} FAIL out of {len(results)}")
    print("=" * 80)
    print()

    # Verify frontier integrity
    contracts = load_contracts()
    status_counts = {}
    for c in contracts.values():
        status = c.status
        status_counts[status] = status_counts.get(status, 0) + 1

    print("Frontier Integrity Check:")
    print(f"  Total: {len(contracts)} (expected 37)")
    print(f"  CAUSAL_VERIFIED: {status_counts.get('CAUSAL_VERIFIED', 0)} (expected 26)")
    print(f"  STRUCTURAL_ONLY: {status_counts.get('STRUCTURAL_ONLY', 0)} (expected 8)")
    print(f"  NEGATIVE_EVIDENCE: {status_counts.get('NEGATIVE_EVIDENCE', 0)} (expected 3)")
    print()

    frontier_ok = (
        len(contracts) == 37 and
        status_counts.get('CAUSAL_VERIFIED') == 26 and
        status_counts.get('STRUCTURAL_ONLY') == 8 and
        status_counts.get('NEGATIVE_EVIDENCE') == 3
    )

    if passed == len(results) and frontier_ok:
        print("[PASS] DECISION: VALUE_AWARE_PREREQUISITE_COMPILER_CHAIN_VERIFIED")
        return 0
    else:
        if failed > 0:
            print(f"[FAIL] BLOCKED: {failed} compiler tests failed")
        if not frontier_ok:
            print("[FAIL] BLOCKED: Frontier integrity check failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
