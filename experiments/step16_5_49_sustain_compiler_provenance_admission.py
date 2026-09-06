"""16.5.49: Sustain compiler provenance admission audit.

Validates that the compiler can safely consume the newly repaired
CapabilityContract provenance for envelope_field_sustain.

Audit scope: admission/compiler layer only.
No Serum mutations, no state changes, no new evidence.
"""

import sys
import json
import pickle
from pathlib import Path
from typing import Dict, Tuple, Any, Optional
from dataclasses import dataclass, asdict

# ---- Path setup ----
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from serum2.evidence import admission, capability_contract
from serum2.compiler import targets, context as ctx_mod


# ---- Decision enum ----
DECISION_BLOCKED_SEMANTIC_TARGET = "BLOCKED_SEMANTIC_TARGET"
DECISION_BLOCKED_CONTEXT_ADMISSION = "BLOCKED_CONTEXT_ADMISSION"
DECISION_COMPILER_CONTEXT_READY = "COMPILER_CONTEXT_READY"
DECISION_BLOCKED_COMPILER_API = "BLOCKED_COMPILER_API"


@dataclass
class AuditResult:
    """Structured audit verdict."""
    decision: str
    category: str  # A, B, C, or D
    sustain_contract_found: bool
    sustain_in_semantic_targets: bool
    contract_details: Optional[Dict[str, Any]] = None
    admission_refusal: Optional[str] = None
    negative_test_refused: bool = False
    positive_test_eligible: bool = False
    findings: list = None
    blockers: list = None

    def __post_init__(self):
        if self.findings is None:
            self.findings = []
        if self.blockers is None:
            self.blockers = []


def load_contracts() -> Dict[Tuple[str, str], Any]:
    """Load the current _capability_contracts.pkl from experiments."""
    pkl_path = repo_root / "experiments" / "_capability_contracts.pkl"
    if not pkl_path.exists():
        raise FileNotFoundError(f"Contracts pickle not found: {pkl_path}")

    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def find_sustain_contract(contracts: Dict[Tuple[str, str], Any]) -> Optional[Any]:
    """Locate contract with target == 'envelope_field_sustain'."""
    for (cdid, cond), contract in contracts.items():
        if hasattr(contract, "target") and contract.target == "envelope_field_sustain":
            return contract
    return None


def verify_contract_structure(contract: Any) -> Dict[str, Any]:
    """Extract and verify contract structure."""
    findings = []
    details = {
        "target": getattr(contract, "target", None),
        "status": getattr(contract, "status", None),
        "allowed_operation": getattr(contract, "allowed_operation", None),
        "prerequisites": tuple(getattr(contract, "prerequisites", ())),
        "verified": dict(getattr(contract, "verified", {})),
        "measurement": dict(getattr(contract, "measurement", {})) if hasattr(contract, "measurement") else None,
        "scope": dict(getattr(contract, "scope", {})),
        "provenance": dict(getattr(contract, "provenance", {})),
        "limitations": tuple(getattr(contract, "limitations", ())),
    }

    # ---- Verify critical fields ----
    if not details.get("scope", {}).get("mutation_target_path"):
        findings.append("WARNING: mutation_target_path missing from scope")
    if not details.get("measurement", {}).get("measurement_definition_id"):
        findings.append("WARNING: measurement_definition_id missing from measurement")

    provenance = details.get("provenance", {})
    if isinstance(provenance, dict):
        # Check for shared_context in provenance
        shared_ctx = provenance.get("shared_context", {})
        if not shared_ctx:
            findings.append("WARNING: shared_context missing from provenance")
        else:
            details["provenance_shared_context"] = shared_ctx
            if shared_ctx.get("status") != "PARTIAL":
                findings.append(f"WARNING: shared_context status is {shared_ctx.get('status')}, expected PARTIAL")

    # Check baseline_overrides
    baseline_overrides = provenance.get("baseline_overrides", {})
    if baseline_overrides:
        details["baseline_overrides"] = baseline_overrides
        expected = {"Env0.plainParams.kParamDecay": 0.02}
        for key, val in expected.items():
            if baseline_overrides.get(key) != val:
                findings.append(f"WARNING: baseline_overrides[{key}] = {baseline_overrides.get(key)}, expected {val}")
    else:
        findings.append("WARNING: baseline_overrides empty or missing")

    return {"details": details, "findings": findings}


def check_semantic_targets() -> Dict[str, Any]:
    """Inspect semantic target vocabulary."""
    findings = []

    # Check if Env1.Sustain or Env0.Sustain are registered
    has_sustain_semantic = False
    for name in targets.SEMANTIC_TARGETS.keys():
        if "Sustain" in name:
            has_sustain_semantic = True
            findings.append(f"Found semantic target: {name}")

    if not has_sustain_semantic:
        findings.append("No Env0.Sustain or Env1.Sustain in SEMANTIC_TARGETS vocabulary")
        findings.append("envelope_field_sustain capability exists but semantic target NOT silently resolved")

    return {
        "semantic_targets_defined": list(targets.SEMANTIC_TARGETS.keys()),
        "has_sustain_semantic": has_sustain_semantic,
        "findings": findings,
    }


def test_negative_case(contracts: Dict[Tuple[str, str], Any]) -> Dict[str, Any]:
    """Test that sustain request WITHOUT shared context is REFUSED."""
    # Attempt to admit sustain without any special context
    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=False,
        required_persistence=False,
        proposed_prerequisites_verified=None,
        required_measurement_definition_id=None
    )

    return {
        "test": "negative (no shared context)",
        "admitted": result.admitted,
        "reason": result.reason,
        "detail": result.detail,
        "contract_status": result.contract.status if result.contract else None,
    }


def test_positive_case(contracts: Dict[Tuple[str, str], Any],
                       contract: Optional[Any]) -> Dict[str, Any]:
    """Test that sustain WITH the established shared context is eligible."""
    if not contract:
        return {"test": "positive", "error": "No sustain contract found"}

    # Extract the measurement_definition_id from contract
    mdid = None
    if contract.measurement:
        mdid = contract.measurement.get("measurement_definition_id")

    # Try admission with matching measurement definition
    result = admission.admit(
        contracts,
        target="envelope_field_sustain",
        required_causal=contract.status == "CAUSAL_VERIFIED",
        required_persistence=False,
        proposed_prerequisites_verified={p["field_path"]: True for p in contract.prerequisites},
        required_measurement_definition_id=mdid,
    )

    return {
        "test": "positive (with shared context)",
        "admitted": result.admitted,
        "reason": result.reason,
        "detail": result.detail,
        "contract_status": result.contract.status if result.contract else None,
        "measurement_definition_id_used": mdid,
    }


def check_compiler_api_compatibility(contract: Optional[Any]) -> Dict[str, Any]:
    """Verify compiler APIs can consume shared_context."""
    findings = []
    blockers = []

    if not contract:
        return {"findings": findings, "blockers": ["No sustain contract to test"]}

    # ---- Check 1: context.py can extract RequiredContext ----
    provenance = getattr(contract, "provenance", {})
    if isinstance(provenance, dict):
        shared_ctx = provenance.get("shared_context", {})
        if not shared_ctx:
            findings.append("No shared_context in provenance to extract")
        else:
            # Verify it has the expected structure for RequiredContext
            container_path = shared_ctx.get("container_path")
            element_key = shared_ctx.get("element_key")
            leaf_suffix = shared_ctx.get("leaf_suffix")

            if container_path and element_key and leaf_suffix:
                findings.append(f"RequiredContext structure ready: container={container_path}, key={element_key}, leaf={leaf_suffix}")
            else:
                blockers.append(f"RequiredContext incomplete: container_path={container_path}, element_key={element_key}, leaf_suffix={leaf_suffix}")

    # ---- Check 2: targets.py semantic target registration ----
    if "Env1.Sustain" not in targets.SEMANTIC_TARGETS and "Env0.Sustain" not in targets.SEMANTIC_TARGETS:
        blockers.append("DECISION_BLOCKED_SEMANTIC_TARGET: No Env0.Sustain or Env1.Sustain in SEMANTIC_TARGETS")
    else:
        findings.append("Semantic target registered for sustain")

    # ---- Check 3: admission.py can admit with measurement_definition_id ----
    if contract.measurement:
        mdid = contract.measurement.get("measurement_definition_id")
        if mdid:
            findings.append(f"Measurement definition ID available for admission: {mdid}")
        else:
            findings.append("WARNING: measurement has no measurement_definition_id")

    return {"findings": findings, "blockers": blockers}


def categorize_blocker(blockers: list, findings: list, neg_test: dict, pos_test: dict) -> Tuple[str, str]:
    """Categorize the issue as A, B, C, or D."""

    # Category A: capability exists but semantic target vocabulary is missing
    if any("SEMANTIC_TARGET" in b for b in blockers):
        return (DECISION_BLOCKED_SEMANTIC_TARGET, "A")

    # Category B: semantic target exists but context is unverified
    if any("RequiredContext" in b or "shared_context" in b for b in blockers):
        return (DECISION_BLOCKED_CONTEXT_ADMISSION, "B")

    # Category D: compiler cannot consume shared_context because APIs insufficient
    if any("API" in b or "insufficient" in b for b in blockers):
        return (DECISION_BLOCKED_COMPILER_API, "D")

    # Category C: semantic target + context valid and admission succeeds
    if pos_test.get("admitted"):
        return (DECISION_COMPILER_CONTEXT_READY, "C")

    # Default to admission blocker
    return (DECISION_BLOCKED_CONTEXT_ADMISSION, "B")


def audit() -> AuditResult:
    """Run the complete audit."""
    print("=" * 80)
    print("16.5.49: SUSTAIN COMPILER PROVENANCE ADMISSION AUDIT")
    print("=" * 80)
    print()

    # ---- Load contracts ----
    print("[1] Loading capability contracts...")
    try:
        contracts = load_contracts()
        print(f"    Loaded {len(contracts)} contracts")
    except Exception as e:
        print(f"    ERROR: {e}")
        return AuditResult(
            decision=DECISION_BLOCKED_SEMANTIC_TARGET,
            category="X",
            sustain_contract_found=False,
            sustain_in_semantic_targets=False,
            blockers=[str(e)],
        )

    # ---- Find sustain contract ----
    print()
    print("[2] Locating contract with target='envelope_field_sustain'...")
    sustain_contract = find_sustain_contract(contracts)
    if not sustain_contract:
        print("    NOT FOUND")
        return AuditResult(
            decision=DECISION_BLOCKED_SEMANTIC_TARGET,
            category="A",
            sustain_contract_found=False,
            sustain_in_semantic_targets=False,
            blockers=["No sustain contract in _capability_contracts.pkl"],
        )
    print("    FOUND")

    # ---- Verify contract structure ----
    print()
    print("[3] Verifying contract structure...")
    struct_result = verify_contract_structure(sustain_contract)
    details = struct_result["details"]
    struct_findings = struct_result["findings"]

    print(f"    Target: {details['target']}")
    print(f"    Status: {details['status']}")
    print(f"    Allowed operation: {details['allowed_operation']}")
    print(f"    Prerequisites: {details['prerequisites']}")
    print(f"    Verified gates: {details['verified']}")
    print(f"    Measurement: {details.get('measurement')}")
    print(f"    Scope: {details['scope']}")
    print(f"    Provenance keys: {list(details['provenance'].keys())}")
    print(f"    Limitations: {details['limitations']}")

    if "provenance_shared_context" in details:
        print(f"    Provenance shared_context: {details['provenance_shared_context']}")
    if "baseline_overrides" in details:
        print(f"    Baseline overrides: {details['baseline_overrides']}")

    for finding in struct_findings:
        print(f"    {finding}")

    # ---- Check semantic targets ----
    print()
    print("[4] Inspecting semantic target vocabulary...")
    semantic_result = check_semantic_targets()
    for finding in semantic_result["findings"]:
        print(f"    {finding}")
    print(f"    Total semantic targets: {len(semantic_result['semantic_targets_defined'])}")

    sustain_in_semantic = semantic_result["has_sustain_semantic"]

    # ---- Test negative case ----
    print()
    print("[5] Testing NEGATIVE case (no shared context)...")
    neg_test = test_negative_case(contracts)
    print(f"    Admitted: {neg_test['admitted']}")
    print(f"    Reason: {neg_test['reason']}")
    print(f"    Detail: {neg_test['detail'][:120]}...")
    print(f"    Contract status in result: {neg_test['contract_status']}")

    neg_refused = not neg_test["admitted"]

    # ---- Test positive case ----
    print()
    print("[6] Testing POSITIVE case (with shared context)...")
    pos_test = test_positive_case(contracts, sustain_contract)
    print(f"    Admitted: {pos_test['admitted']}")
    print(f"    Reason: {pos_test['reason']}")
    print(f"    Detail: {pos_test['detail'][:120]}...")
    print(f"    Contract status in result: {pos_test['contract_status']}")
    print(f"    Measurement definition ID: {pos_test.get('measurement_definition_id_used')}")

    pos_eligible = pos_test["admitted"]

    # ---- Check compiler API compatibility ----
    print()
    print("[7] Checking compiler API compatibility...")
    api_result = check_compiler_api_compatibility(sustain_contract)
    for finding in api_result["findings"]:
        print(f"    ✓ {finding}")
    for blocker in api_result["blockers"]:
        print(f"    ✗ {blocker}")

    # ---- Categorize and decide ----
    print()
    print("[8] Categorizing findings...")
    all_blockers = struct_findings + semantic_result["findings"] + api_result["blockers"]
    decision, category = categorize_blocker(
        api_result["blockers"],
        api_result["findings"],
        neg_test,
        pos_test,
    )

    print(f"    Category: {category}")
    print(f"    Decision: {decision}")

    # ---- Summary ----
    print()
    print("=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"Sustain contract found:       {bool(sustain_contract)}")
    print(f"Sustain in SEMANTIC_TARGETS:  {sustain_in_semantic}")
    print(f"Negative case refused:        {neg_refused} (expected: True)")
    print(f"Positive case eligible:       {pos_eligible} (expected: True or later)")
    print(f"Category:                     {category}")
    print(f"Decision:                     {decision}")
    print()

    return AuditResult(
        decision=decision,
        category=category,
        sustain_contract_found=bool(sustain_contract),
        sustain_in_semantic_targets=sustain_in_semantic,
        contract_details=details,
        admission_refusal=neg_test.get("reason"),
        negative_test_refused=neg_refused,
        positive_test_eligible=pos_eligible,
        findings=api_result["findings"],
        blockers=api_result["blockers"],
    )


if __name__ == "__main__":
    result = audit()

    # Write JSON decision file
    output_path = Path(__file__).parent / "16_5_49_SUSTAIN_COMPILER_PROVENANCE_ADMISSION.json"

    output_data = {
        "audit": "sustain_compiler_provenance_admission",
        "decision": result.decision,
        "category": result.category,
        "sustain_contract_found": result.sustain_contract_found,
        "sustain_in_semantic_targets": result.sustain_in_semantic_targets,
        "negative_test_refused": result.negative_test_refused,
        "positive_test_eligible": result.positive_test_eligible,
        "contract_details": result.contract_details,
        "admission_refusal_reason": result.admission_refusal,
        "findings": result.findings,
        "blockers": result.blockers,
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nDecision written to: {output_path}")
    print(json.dumps(output_data, indent=2))
