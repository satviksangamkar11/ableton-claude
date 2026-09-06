"""16.5.51 FINAL: Producer-entry verification for value-aware prerequisites.

This test proves the REAL producer entry point chain through the admission layer:

Env1.Sustain
→ resolve_semantic_target()
→ result.produce()
→ kernel.dry_run() [internal]
→ admission.admit() [internal]

Uses the existing 37-contract artifact and tests through the real producer
entry point, stopping at the admission level (no rendering per task constraint).

Test cases (all through producer entry point to dry_run/admission):
1. Decay missing → REFUSED prerequisite_unverified
2. Decay=0.01 → REFUSED prerequisite_unverified
3. Decay=0.03 → REFUSED prerequisite_unverified
4. Decay=0.02 → ADMITTED (passes admission, would proceed to construct)
5. Regression: prerequisite-free target (e.g., OSC1.Volume) passes through
"""

import sys
import pickle
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, r"D:\ableton claude")

from serum2.compiler import result
from serum2.compiler.targets import resolve_semantic_target

REPO_ROOT = Path(r"D:\ableton claude")
CONTRACTS_PATH = REPO_ROOT / "experiments" / "_capability_contracts.pkl"


@dataclass(frozen=True)
class ProducerEntryTestResult:
    name: str
    scenario: str
    expected_outcome: str  # "REFUSED" | "ADMITTED"
    actual_outcome: str    # "REFUSED" | "ADMITTED"
    refusal_reason: str    # if refused
    passed: bool


def load_contracts():
    """Load capability contracts."""
    with open(CONTRACTS_PATH, "rb") as f:
        return pickle.load(f)


def make_test_body_env0_sustain(decay_value=None):
    """Construct a minimal Serum state body with Env0 for Sustain prerequisite.

    The Sustain contract uses Env0 (mutation path: Env0.plainParams.kParamSustain).
    The prerequisite is Env0.plainParams.kParamDecay (must be 0.02).

    If decay_value is None, Env0 is missing Decay entirely.
    """
    if decay_value is None:
        # Missing Decay: Env0.plainParams incomplete
        return {
            "Env0": {
                "plainParams": {}
            }
        }
    else:
        # Decay present with given value
        return {
            "Env0": {
                "plainParams": {
                    "kParamDecay": decay_value,
                }
            }
        }


def make_minimal_body_env1_decay():
    """Construct a minimal body for prerequisite-free regression test (Env1.Decay)."""
    return {
        "Env1": {
            "plainParams": {}
        }
    }


def test_case_1_decay_missing():
    """Case 1: Decay field is completely missing from body.
    Expected: REFUSED prerequisite_unverified
    """
    contracts = load_contracts()
    body = make_test_body_env0_sustain(decay_value=None)

    # Call through the REAL producer entry point
    producer_result = result.produce(
        "Env1.Sustain",
        contracts,
        structural_records=[],  # No structural records needed for this test
        body=body,
        requested_value=None,  # WITNESS_MODE
        experiment_id="test_case_1",
    )

    # Check the result
    refused = producer_result.refusal_reason is not None
    outcome = "REFUSED" if refused else "ADMITTED"
    passed = (
        outcome == "REFUSED" and
        "prerequisite" in (producer_result.refusal_detail or "").lower()
    )

    return ProducerEntryTestResult(
        name="Case 1: Decay Missing",
        scenario="body missing Env1.plainParams.kParamDecay entirely",
        expected_outcome="REFUSED",
        actual_outcome=outcome,
        refusal_reason=producer_result.refusal_detail or "admitted",
        passed=passed,
    )


def test_case_2_decay_wrong_0_01():
    """Case 2: Decay=0.01 in body.
    Expected: REFUSED prerequisite_unverified (value mismatch)
    """
    contracts = load_contracts()
    body = make_test_body_env0_sustain(decay_value=0.01)

    producer_result = result.produce(
        "Env1.Sustain",
        contracts,
        structural_records=[],
        body=body,
        requested_value=None,
        experiment_id="test_case_2",
    )

    refused = producer_result.refusal_reason is not None
    outcome = "REFUSED" if refused else "ADMITTED"
    passed = (
        outcome == "REFUSED" and
        "prerequisite" in (producer_result.refusal_detail or "").lower()
    )

    return ProducerEntryTestResult(
        name="Case 2: Decay=0.01 (Wrong)",
        scenario="body has Env1.plainParams.kParamDecay=0.01",
        expected_outcome="REFUSED",
        actual_outcome=outcome,
        refusal_reason=producer_result.refusal_detail or "admitted",
        passed=passed,
    )


def test_case_3_decay_wrong_0_03():
    """Case 3: Decay=0.03 in body.
    Expected: REFUSED prerequisite_unverified (value mismatch)
    """
    contracts = load_contracts()
    body = make_test_body_env0_sustain(decay_value=0.03)

    producer_result = result.produce(
        "Env1.Sustain",
        contracts,
        structural_records=[],
        body=body,
        requested_value=None,
        experiment_id="test_case_3",
    )

    refused = producer_result.refusal_reason is not None
    outcome = "REFUSED" if refused else "ADMITTED"
    passed = (
        outcome == "REFUSED" and
        "prerequisite" in (producer_result.refusal_detail or "").lower()
    )

    return ProducerEntryTestResult(
        name="Case 3: Decay=0.03 (Wrong)",
        scenario="body has Env1.plainParams.kParamDecay=0.03",
        expected_outcome="REFUSED",
        actual_outcome=outcome,
        refusal_reason=producer_result.refusal_detail or "admitted",
        passed=passed,
    )


def test_case_4_decay_correct_0_02():
    """Case 4: Decay=0.02 in body.
    Expected: ADMITTED (correct value)
    """
    contracts = load_contracts()
    body = make_test_body_env0_sustain(decay_value=0.02)

    producer_result = result.produce(
        "Env1.Sustain",
        contracts,
        structural_records=[],
        body=body,
        requested_value=None,
        experiment_id="test_case_4",
    )

    admitted = producer_result.refusal_reason is None
    outcome = "ADMITTED" if admitted else "REFUSED"
    passed = (
        outcome == "ADMITTED" and
        producer_result.resolved_ref is not None
    )

    return ProducerEntryTestResult(
        name="Case 4: Decay=0.02 (Correct)",
        scenario="body has Env1.plainParams.kParamDecay=0.02",
        expected_outcome="ADMITTED",
        actual_outcome=outcome,
        refusal_reason=producer_result.refusal_detail or "ADMITTED",
        passed=passed,
    )


def test_case_5_regression_prerequisite_free():
    """Case 5: Regression test for prerequisite-free target.

    Env1.Decay has no prerequisites. It should pass through the same
    producer entry point without errors (different code path, but
    should complete successfully and not refuse on prerequisites).

    Expected: Either ADMITTED or REFUSED for a structural reason,
    but NOT for a prerequisite reason.
    """
    contracts = load_contracts()
    body = make_minimal_body_env1_decay()

    producer_result = result.produce(
        "Env1.Decay",
        contracts,
        structural_records=[],
        body=body,
        requested_value=None,
        experiment_id="test_case_5",
    )

    # For a prerequisite-free target, we should NOT see "prerequisite" in
    # the refusal reason (if it was refused for some other reason, that's ok)
    refused = producer_result.refusal_reason is not None

    # The key check: if it's refused, it should NOT be for prerequisites
    passed = (
        "prerequisite" not in (producer_result.refusal_detail or "").lower()
    )

    outcome = "REFUSED" if refused else "ADMITTED"

    return ProducerEntryTestResult(
        name="Case 5: Regression - Prerequisite-Free Target",
        scenario="Env1.Decay (no prerequisites) through producer entry",
        expected_outcome="NO_PREREQUISITE_REFUSAL",
        actual_outcome=outcome,
        refusal_reason=producer_result.refusal_detail or "ADMITTED",
        passed=passed,
    )


def main():
    print("=" * 80)
    print("16.5.51 FINAL: PRODUCER-ENTRY PREREQUISITE VERIFICATION")
    print("=" * 80)
    print()

    results = []
    tests = [
        test_case_1_decay_missing,
        test_case_2_decay_wrong_0_01,
        test_case_3_decay_wrong_0_03,
        test_case_4_decay_correct_0_02,
        test_case_5_regression_prerequisite_free,
    ]

    for test_fn in tests:
        try:
            result_obj = test_fn()
            results.append(result_obj)
            status = "[PASS]" if result_obj.passed else "[FAIL]"
            print(f"{status} {result_obj.name}")
            print(f"     Scenario:   {result_obj.scenario}")
            print(f"     Expected:   {result_obj.expected_outcome}")
            print(f"     Actual:     {result_obj.actual_outcome}")
            print(f"     Detail:     {result_obj.refusal_reason[:100]}...")
            print()
        except Exception as e:
            print(f"[FAIL] {test_fn.__name__}")
            print(f"     Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(ProducerEntryTestResult(
                name=test_fn.__name__,
                scenario="(error)",
                expected_outcome="N/A",
                actual_outcome="ERROR",
                refusal_reason=str(e),
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
        print("[PASS] DECISION: PRODUCER_ENTRY_PREREQUISITE_VERIFIED")
        return 0
    else:
        if failed > 0:
            print(f"[FAIL] BLOCKED: {failed} producer-entry tests failed")
        if not frontier_ok:
            print("[FAIL] BLOCKED: Frontier integrity check failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
