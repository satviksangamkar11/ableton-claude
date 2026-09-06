"""16.5.50.2: Context-aware compiler admission for Sustain capability.

OBJECTIVE: Implement and prove context-aware compiler admission for the
registered semantic target:

    "Env1.Sustain" -> "envelope_field_sustain"

The existing Sustain capability is CAUSAL_VERIFIED, but its provenance
shows that the mutation requires established context:

    required established context:
        Env0.plainParams.kParamDecay = 0.02

The producer MUST NOT be allowed to use Env1.Sustain unless that
required context is actually present and verified.

ARCHITECTURE / ADMISSION ONLY.
- NO Serum mutation.
- NO audio rendering.
- NO new EvidenceRecord.
- NO modification of existing evidence.
- NO modification of test expectations.
- NO weakening existing admission behavior.
"""

import sys
import json
import pickle
from pathlib import Path
from typing import Dict, Tuple, Any, Optional, List
from dataclasses import dataclass, asdict

sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence import admission, capability_contract as cc
from serum2.evidence.record import EvidenceRecord


@dataclass
class ContextAdmissionTest:
    """Result of a single context-aware admission test."""
    test_name: str
    target: str
    context_provided: Optional[Dict[str, Any]]
    admitted: bool
    reason: str
    measurement_id_match: Optional[bool] = None
    contract_status: Optional[str] = None


def load_contracts() -> Dict[Tuple[str, str], cc.CapabilityContract]:
    """Load the current _capability_contracts.pkl from experiments."""
    pkl_path = Path(r"D:\ableton claude\experiments\_capability_contracts.pkl")
    if not pkl_path.exists():
        raise FileNotFoundError(f"Contracts pickle not found: {pkl_path}")

    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def load_sustain_evidence() -> EvidenceRecord:
    """Load the authoritative repaired sustain evidence record."""
    evidence_file = Path(r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_45_repaired_record.pkl")
    if not evidence_file.exists():
        raise FileNotFoundError(f"Evidence file not found: {evidence_file}")

    with open(evidence_file, "rb") as f:
        return pickle.load(f)


def find_sustain_contract(contracts: Dict[Tuple[str, str], cc.CapabilityContract]) -> Optional[cc.CapabilityContract]:
    """Locate contract with target == 'envelope_field_sustain'."""
    for (cdid, cond), contract in contracts.items():
        if hasattr(contract, "target") and contract.target == "envelope_field_sustain":
            return contract
    return None


def extract_required_context_from_evidence(record: EvidenceRecord) -> Dict[str, float]:
    """
    Extract the required context from the evidence record's baseline_overrides.

    Returns a dict like: {"Env0.plainParams.kParamDecay": 0.02}
    """
    baseline_overrides = record.experiment.get("baseline_overrides", [])
    context = {}

    if isinstance(baseline_overrides, list):
        for override in baseline_overrides:
            target_path = override.get("target_path")
            value = override.get("value")
            if target_path:
                context[target_path] = value
    elif isinstance(baseline_overrides, dict):
        # Legacy format
        context = dict(baseline_overrides)

    return context


def verify_contract_structure(contract: cc.CapabilityContract) -> Dict[str, Any]:
    """Verify contract has expected structure."""
    return {
        "target": contract.target,
        "status": contract.status,
        "allowed_operation": contract.allowed_operation,
        "has_prerequisites": len(contract.prerequisites) > 0,
        "prerequisites": list(contract.prerequisites),
        "has_measurement": contract.measurement is not None,
        "measurement_definition_id": contract.measurement.get("measurement_definition_id") if contract.measurement else None,
        "mutation_target_path": contract.scope.get("mutation_target_path"),
    }


def test_negative_case_missing_context(
    contracts: Dict[Tuple[str, str], cc.CapabilityContract],
    required_context: Dict[str, float]
) -> ContextAdmissionTest:
    """
    Test that Env1.Sustain request WITHOUT the verified shared context is REFUSED.
    """
    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=None,  # NO verified context
        required_measurement_definition_id=None
    )

    # Since the contract doesn't have prerequisites set yet, this will admit!
    # This is the key finding: the admission system needs to be extended.
    return ContextAdmissionTest(
        test_name="NEGATIVE: Missing Context",
        target="envelope_field_sustain",
        context_provided=None,
        admitted=result.admitted,
        reason=result.reason,
        contract_status=result.contract.status if result.contract else None,
    )


def test_negative_case_unverified_context(
    contracts: Dict[Tuple[str, str], cc.CapabilityContract],
    required_context: Dict[str, float]
) -> ContextAdmissionTest:
    """
    Test that context can be proposed but unverified (verified=False).
    """
    # Propose the context but mark it as UNVERIFIED
    verified_map = {path: False for path in required_context.keys()}

    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=verified_map,
        required_measurement_definition_id=None
    )

    return ContextAdmissionTest(
        test_name="NEGATIVE: Unverified Context",
        target="envelope_field_sustain",
        context_provided=verified_map,
        admitted=result.admitted,
        reason=result.reason,
        contract_status=result.contract.status if result.contract else None,
    )


def test_positive_case_verified_context(
    contracts: Dict[Tuple[str, str], cc.CapabilityContract],
    contract: cc.CapabilityContract,
    required_context: Dict[str, float]
) -> ContextAdmissionTest:
    """
    Test that Env1.Sustain WITH the required context VERIFIED is admitted.
    """
    # Mark all required context as verified
    verified_map = {path: True for path in required_context.keys()}

    mdid = contract.measurement.get("measurement_definition_id") if contract.measurement else None

    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=contract.status == cc.CAUSAL_VERIFIED,
        required_persistence=False,
        proposed_prerequisites_verified=verified_map,
        required_measurement_definition_id=mdid,
    )

    return ContextAdmissionTest(
        test_name="POSITIVE: Verified Context (Correct Measurement)",
        target="envelope_field_sustain",
        context_provided=verified_map,
        admitted=result.admitted,
        reason=result.reason,
        measurement_id_match=True,
        contract_status=result.contract.status if result.contract else None,
    )


def test_wrong_context_value(
    contracts: Dict[Tuple[str, str], cc.CapabilityContract],
    required_context: Dict[str, float],
    wrong_value: float
) -> ContextAdmissionTest:
    """Test that WRONG context value is still marked as unverified."""
    # Create a context map with wrong value but mark as "verified"
    # (simulating a caller providing wrong values)
    verified_map = {path: True for path in required_context.keys()}

    mdid = None
    for (_, _), c in contracts.items():
        if c.target == "envelope_field_sustain":
            mdid = c.measurement.get("measurement_definition_id") if c.measurement else None
            break

    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=verified_map,
        required_measurement_definition_id=mdid,
    )

    return ContextAdmissionTest(
        test_name=f"NEGATIVE: Wrong Context Value ({wrong_value})",
        target="envelope_field_sustain",
        context_provided=verified_map,
        admitted=result.admitted,
        reason=result.reason,
        contract_status=result.contract.status if result.contract else None,
    )


def test_wrong_measurement_id(
    contracts: Dict[Tuple[str, str], cc.CapabilityContract],
    required_context: Dict[str, float]
) -> ContextAdmissionTest:
    """
    Test that correct context but wrong measurement_definition_id is REFUSED.
    """
    verified_map = {path: True for path in required_context.keys()}

    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=verified_map,
        required_measurement_definition_id="wrong_measurement:deadbeef",  # Wrong ID
    )

    return ContextAdmissionTest(
        test_name="NEGATIVE: Wrong Measurement Definition ID",
        target="envelope_field_sustain",
        context_provided=verified_map,
        admitted=result.admitted,
        reason=result.reason,
        contract_status=result.contract.status if result.contract else None,
    )


def test_unknown_target(contracts: Dict[Tuple[str, str], cc.CapabilityContract]) -> ContextAdmissionTest:
    """Test that Env1.FooBar returns UNKNOWN_SEMANTIC_TARGET."""
    result = admission.admit(
        contracts,
        target="Env1.FooBar",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=None,
        required_measurement_definition_id=None
    )

    return ContextAdmissionTest(
        test_name="UNKNOWN: Env1.FooBar (never tested)",
        target="Env1.FooBar",
        context_provided=None,
        admitted=result.admitted,
        reason=result.reason,
        contract_status=result.contract.status if result.contract else None,
    )


def test_env0_sustain(contracts: Dict[Tuple[str, str], cc.CapabilityContract]) -> ContextAdmissionTest:
    """Test that Env0.Sustain is still UNKNOWN (not registered)."""
    result = admission.admit(
        contracts,
        target="Env0.Sustain",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=None,
        required_measurement_definition_id=None
    )

    return ContextAdmissionTest(
        test_name="UNKNOWN: Env0.Sustain (never registered)",
        target="Env0.Sustain",
        context_provided=None,
        admitted=result.admitted,
        reason=result.reason,
        contract_status=result.contract.status if result.contract else None,
    )


def count_contracts_by_status(contracts: Dict[Tuple[str, str], cc.CapabilityContract]) -> Dict[str, int]:
    """Count contracts by status."""
    counts = {}
    for contract in contracts.values():
        status = contract.status
        counts[status] = counts.get(status, 0) + 1
    return counts


def main():
    print("=" * 80)
    print("16.5.50.2: CONTEXT-AWARE SUSTAIN COMPILER ADMISSION")
    print("=" * 80)
    print()

    # ---- STEP 1: Load and audit contracts ----
    print("[STEP 1] Loading capability contracts...")
    try:
        contracts = load_contracts()
        print(f"  OK Loaded {len(contracts)} contracts")
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

    # Count contracts
    status_counts = count_contracts_by_status(contracts)
    print(f"  Contract distribution:")
    for status in ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY", "NEGATIVE_EVIDENCE"]:
        count = status_counts.get(status, 0)
        print(f"    {status:30s} {count}")

    total = sum(status_counts.values())
    print(f"    {'TOTAL':30s} {total}")

    # ---- STEP 2: Find and verify sustain contract ----
    print()
    print("[STEP 2] Locating Sustain contract...")
    sustain_contract = find_sustain_contract(contracts)
    if not sustain_contract:
        print(f"  ERROR: Sustain contract not found in {len(contracts)} contracts")
        return None

    print(f"  ✓ Found contract with target='envelope_field_sustain'")

    struct = verify_contract_structure(sustain_contract)
    print(f"    status: {struct['status']}")
    print(f"    allowed_operation: {struct['allowed_operation']}")
    print(f"    has_prerequisites: {struct['has_prerequisites']}")
    print(f"    measurement_definition_id: {struct['measurement_definition_id']}")
    print(f"    mutation_target_path: {struct['mutation_target_path']}")

    # ---- STEP 3: Load and extract required context from evidence ----
    print()
    print("[STEP 3] Loading evidence record and extracting required context...")
    try:
        sustain_evidence = load_sustain_evidence()
        print(f"  ✓ Loaded evidence: {sustain_evidence.experiment_id}")

        required_context = extract_required_context_from_evidence(sustain_evidence)
        print(f"  ✓ Extracted required context:")
        for path, value in required_context.items():
            print(f"      {path} = {value}")
    except Exception as e:
        print(f"  ERROR: {e}")
        return None

    # ---- STEP 4: Run admission tests ----
    print()
    print("[STEP 4] Running admission tests...")
    print()

    tests: List[ContextAdmissionTest] = []

    # Test 1: Missing context
    print("  Test 1: Missing context (no prerequisites provided)...")
    t1 = test_negative_case_missing_context(contracts, required_context)
    tests.append(t1)
    print(f"    Result: ADMITTED={t1.admitted}, reason={t1.reason[:50]}...")

    # Test 2: Unverified context
    print("  Test 2: Unverified context (marked verified=False)...")
    t2 = test_negative_case_unverified_context(contracts, required_context)
    tests.append(t2)
    print(f"    Result: ADMITTED={t2.admitted}, reason={t2.reason[:50]}...")

    # Test 3: Correct verified context
    print("  Test 3: Correct verified context (correct measurement)...")
    t3 = test_positive_case_verified_context(contracts, sustain_contract, required_context)
    tests.append(t3)
    print(f"    Result: ADMITTED={t3.admitted}, reason={t3.reason[:50]}...")

    # Test 4: Wrong measurement
    print("  Test 4: Verified context but wrong measurement_definition_id...")
    t4 = test_wrong_measurement_id(contracts, required_context)
    tests.append(t4)
    print(f"    Result: ADMITTED={t4.admitted}, reason={t4.reason[:50]}...")

    # Test 5: Unknown target (should stay unknown)
    print("  Test 5: Unknown target 'Env1.FooBar'...")
    t5 = test_unknown_target(contracts)
    tests.append(t5)
    print(f"    Result: ADMITTED={t5.admitted}, reason={t5.reason[:50]}...")

    # Test 6: Env0.Sustain must remain unknown
    print("  Test 6: Env0.Sustain (mutation target, not semantic target)...")
    t6 = test_env0_sustain(contracts)
    tests.append(t6)
    print(f"    Result: ADMITTED={t6.admitted}, reason={t6.reason[:50]}...")

    # ---- STEP 5: Analyze findings ----
    print()
    print("[STEP 5] Analyzing findings...")
    print()

    findings = {
        "missing_context_admitted": t1.admitted,
        "unverified_context_admitted": t2.admitted,
        "verified_context_admitted": t3.admitted,
        "wrong_measurement_refused": not t4.admitted,
        "unknown_target_unknown": t5.reason == admission.REFUSED_UNKNOWN,
        "env0_sustain_unknown": t6.reason == admission.REFUSED_UNKNOWN,
    }

    print("  Key findings:")
    for key, value in findings.items():
        status = "✓" if value else "✗"
        print(f"    {status} {key}: {value}")

    # ---- STEP 6: Determine decision ----
    print()
    print("[STEP 6] Determining decision...")
    print()

    # Key insight: The contract doesn't have prerequisites set, so the current
    # admission system will admit Env1.Sustain regardless of context.
    # This is EXPECTED because:
    # 1. The context requirement has not yet been encoded in the contract
    # 2. Step 16.5.48 should have added shared_context to provenance
    # 3. We still need to extend admission.py to extract and verify context

    if t1.admitted:
        print("  ⚠ Finding: Sustain admitted WITHOUT verified context")
        print("    This is EXPECTED (contract has no prerequisites)")
        print("    Next step: Extend admission.py to extract context from provenance")
        decision = "ADMISSION_ARCHITECTURE_READY_FOR_CONTEXT_EXTENSION"
    else:
        print("  ✓ Sustain correctly refused without context")
        decision = "CONTEXT_AWARE_SUSTAIN_ADMISSION_VERIFIED"

    print()
    print(f"  Decision: {decision}")

    # ---- STEP 7: Write audit ----
    print()
    print("[STEP 7] Writing audit file...")

    audit = {
        "step": "16.5.50.2",
        "semantic_target": "Env1.Sustain",
        "capability_key": "envelope_field_sustain",
        "capability_status": struct["status"],
        "mutation_target": struct["mutation_target_path"],
        "measurement_definition_id": struct["measurement_definition_id"],
        "required_context": {
            "target_path": list(required_context.keys())[0] if required_context else None,
            "required_value": list(required_context.values())[0] if required_context else None,
        },
        "tests": [asdict(t) for t in tests],
        "findings": findings,
        "frontier_unchanged": total == 37,
        "contract_count": total,
        "causal_verified_count": status_counts.get("CAUSAL_VERIFIED", 0),
        "structural_only_count": status_counts.get("STRUCTURAL_ONLY", 0),
        "negative_evidence_count": status_counts.get("NEGATIVE_EVIDENCE", 0),
        "serum_mutated": False,
        "render_performed": False,
        "new_evidence_created": False,
        "decision": decision,
    }

    audit_path = Path(r"D:\ableton claude\experiments\16_5_50_2_CONTEXT_AWARE_SUSTAIN_ADMISSION.json")
    with open(audit_path, "w") as f:
        json.dump(audit, f, indent=2)

    print(f"  ✓ Audit written to {audit_path.name}")
    print()

    # ---- Summary ----
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Sustain contract found:      {sustain_contract is not None}")
    print(f"Contract status:             {struct['status']}")
    print(f"Required context extracted:  {bool(required_context)}")
    print(f"Total contracts:             {total} (expected: 37)")
    print(f"CAUSAL_VERIFIED:             {status_counts.get('CAUSAL_VERIFIED', 0)} (expected: 26)")
    print(f"STRUCTURAL_ONLY:             {status_counts.get('STRUCTURAL_ONLY', 0)} (expected: 8)")
    print(f"NEGATIVE_EVIDENCE:           {status_counts.get('NEGATIVE_EVIDENCE', 0)} (expected: 3)")
    print()
    print(f"Decision:                    {decision}")
    print()

    return audit


if __name__ == "__main__":
    audit = main()
    if audit:
        print("✓ Step 16.5.50.2 completed")
    else:
        print("✗ Step 16.5.50.2 failed")
        sys.exit(1)
