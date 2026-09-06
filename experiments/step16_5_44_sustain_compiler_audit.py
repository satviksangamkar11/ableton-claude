"""
16.5.44 — SUSTAIN COMPILER CONTRACT / CONTEXT AUDIT

Audit whether the current compiler can safely consume the newly promoted
Env Sustain capability before any Serum execution is attempted.

AUDIT ONLY: No mutations, no rendering, no evidence creation, no promotion.
"""

import sys
import json
import pickle
from pathlib import Path

# Add repository root to sys.path
sys.path.insert(0, r"D:\ableton claude")

# ================================================================
# 16.5.44 — SUSTAIN COMPILER CONTRACT / CONTEXT AUDIT
# ================================================================

def main():
    audit_result = {
        "step": "16.5.44",
        "semantic_target_present": False,
        "sustain_contract_count": 0,
        "causal_verified_count": 0,
        "contracts": [],
        "resolver_result": None,
        "context_provenance": {},
        "decision": None,
        "execution_performed": False,
        "serum_mutated": False,
        "evidence_created": False,
        "capability_promoted": False,
    }

    print("\n" + "=" * 64)
    print("16.5.44 — SUSTAIN COMPILER CONTRACT / CONTEXT AUDIT")
    print("=" * 64)

    # Step 1: Load capability contracts
    contract_path = Path(r"D:\ableton claude\experiments\_capability_contracts.pkl")
    if not contract_path.exists():
        print(f"ERROR: Contract file not found: {contract_path}")
        audit_result["decision"] = "BLOCKED_CONTEXT_PROVENANCE"
        audit_result["error"] = f"Contract file missing: {contract_path}"
        write_audit_json(audit_result)
        return

    try:
        with open(contract_path, "rb") as f:
            contracts_dict = pickle.load(f)
        print(f"✓ Loaded {len(contracts_dict)} contracts from pickle")
    except Exception as e:
        print(f"ERROR: Failed to load contracts: {e}")
        audit_result["decision"] = "BLOCKED_CONTEXT_PROVENANCE"
        audit_result["error"] = f"Failed to load contracts: {str(e)}"
        write_audit_json(audit_result)
        return

    # Step 2: Import from serum2
    try:
        from serum2.compiler.targets import SEMANTIC_TARGETS, resolve_semantic_target
        from serum2.evidence.capability_contract import CAUSAL_VERIFIED
        print("✓ Imported SEMANTIC_TARGETS, resolve_semantic_target, CAUSAL_VERIFIED")
    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        audit_result["decision"] = "BLOCKED_CONTEXT_PROVENANCE"
        audit_result["error"] = f"Import failed: {str(e)}"
        write_audit_json(audit_result)
        return

    # Step 3: Check whether "Env1.Sustain" in SEMANTIC_TARGETS
    semantic_target_present = "Env1.Sustain" in SEMANTIC_TARGETS
    audit_result["semantic_target_present"] = semantic_target_present
    print(f"\nsemantic_target_present: {semantic_target_present}")

    if semantic_target_present:
        print(f"  → Env1.Sustain maps to: {SEMANTIC_TARGETS.get('Env1.Sustain')}")
    else:
        print("  → Env1.Sustain not yet in semantic vocabulary")

    # Step 4: Filter contracts by target == "envelope_field_sustain"
    sustain_contracts = {}
    for key, contract in contracts_dict.items():
        if hasattr(contract, "target") and contract.target == "envelope_field_sustain":
            sustain_contracts[key] = contract

    sustain_contract_count = len(sustain_contracts)
    audit_result["sustain_contract_count"] = sustain_contract_count
    print(f"\nsustain_contract_count: {sustain_contract_count}")

    # Step 5: Analyze each sustain contract
    causal_verified_count = 0
    causal_verified_contracts = []

    for key, contract in sustain_contracts.items():
        contract_info = {
            "key": str(key),
            "target": getattr(contract, "target", None),
            "status": getattr(contract, "status", None),
            "is_causal_verified": getattr(contract, "status", None) == CAUSAL_VERIFIED,
            "mutation_target_path": getattr(contract, "mutation_target_path", None),
            "mutation_value_used": getattr(contract, "mutation_value_used", None),
            "prerequisites": getattr(contract, "prerequisites", None),
            "measurement_definition_id": getattr(contract, "measurement_definition_id", None),
            "limitations": getattr(contract, "limitations", None),
        }

        # Extract condition signature if available
        if hasattr(contract, "provenance") and contract.provenance:
            contract_info["provenance"] = contract.provenance
        if hasattr(contract, "condition_signature_hash"):
            contract_info["condition_signature_hash"] = contract.condition_signature_hash

        audit_result["contracts"].append(contract_info)

        print(f"\n  Contract key: {key}")
        print(f"    target: {contract_info['target']}")
        print(f"    status: {contract_info['status']}")
        print(f"    is_causal_verified: {contract_info['is_causal_verified']}")
        print(f"    mutation_target_path: {contract_info['mutation_target_path']}")
        print(f"    mutation_value_used: {contract_info['mutation_value_used']}")
        print(f"    prerequisites: {contract_info['prerequisites']}")
        print(f"    measurement_definition_id: {contract_info['measurement_definition_id']}")
        print(f"    limitations: {contract_info['limitations']}")

        if contract_info["is_causal_verified"]:
            causal_verified_count += 1
            causal_verified_contracts.append(key)

    audit_result["causal_verified_count"] = causal_verified_count
    print(f"\ncausal_verified_count: {causal_verified_count}")

    # Step 6: Try to resolve semantic target if present
    resolver_result = None
    if semantic_target_present:
        print("\nAttempting resolve_semantic_target('Env1.Sustain', contracts)...")
        try:
            resolver_result = resolve_semantic_target("Env1.Sustain", contracts_dict)
            audit_result["resolver_result"] = {
                "success": True,
                "resolved_contract_key": str(list(sustain_contracts.keys())[0])
                if sustain_contracts
                else None,
                "target": "envelope_field_sustain",
            }
            print(f"  ✓ Resolution succeeded: {resolver_result}")
        except Exception as e:
            print(f"  ✗ Resolution failed: {e}")
            audit_result["resolver_result"] = {"success": False, "error": str(e)}

    # Step 7: Detect blocking conditions
    print("\n" + "=" * 64)
    print("DECISION LOGIC")
    print("=" * 64)

    if not semantic_target_present:
        decision = "BLOCKED_SEMANTIC_TARGET"
        print(f"\n→ {decision}")
        print("  Reason: compiler semantic vocabulary does not yet expose Env1.Sustain")

    elif causal_verified_count > 1:
        decision = "BLOCKED_CONDITION_SELECTION"
        print(f"\n→ {decision}")
        print(f"  Reason: {causal_verified_count} condition-specific CAUSAL_VERIFIED")
        print("  Sustain contracts exist, but resolver has no condition-selection mechanism")

    elif causal_verified_count == 1:
        # Inspect context provenance
        causal_contract_key = causal_verified_contracts[0]
        causal_contract = sustain_contracts[causal_contract_key]

        print(f"\n→ Exactly 1 CAUSAL_VERIFIED contract found: {causal_contract_key}")
        print("  Inspecting context provenance...")

        # Check if context/prerequisites are sufficient
        prerequisites = getattr(causal_contract, "prerequisites", None)
        has_baseline_overrides = False
        baseline_override_note = None

        audit_result["context_provenance"] = {
            "contract_key": str(causal_contract_key),
            "prerequisites": prerequisites,
            "baseline_overrides_present": False,
            "limitation_note": (
                "baseline_overrides not represented in EvidenceRecord.experiment"
            ),
        }

        if prerequisites:
            print(f"    Prerequisites: {prerequisites}")
            # Check if prerequisites include baseline_overrides
            if isinstance(prerequisites, dict) and "baseline_overrides" in prerequisites:
                has_baseline_overrides = True
                print(f"    ✓ baseline_overrides found in prerequisites")
            else:
                baseline_override_note = (
                    "baseline_overrides not represented in EvidenceRecord.experiment"
                )
                print(f"    ✗ baseline_overrides NOT recoverable from contract")
                print(f"    ✗ {baseline_override_note}")
        else:
            baseline_override_note = (
                "No prerequisites; baseline_overrides NOT represented in EvidenceRecord"
            )
            print(f"    ✗ {baseline_override_note}")

        audit_result["context_provenance"]["baseline_overrides_present"] = (
            has_baseline_overrides
        )

        if has_baseline_overrides:
            decision = "READY_FOR_COMPILER_IMPLEMENTATION"
            print(f"\n→ {decision}")
            print("  Reason: Context provenance sufficient to identify corpus Sustain context")
        else:
            decision = "BLOCKED_CONTEXT_PROVENANCE"
            print(f"\n→ {decision}")
            print(f"  Reason: {baseline_override_note}")

    else:
        decision = "BLOCKED_CONTEXT_PROVENANCE"
        print(f"\n→ {decision}")
        print("  Reason: No CAUSAL_VERIFIED Sustain contracts found")

    audit_result["decision"] = decision

    # Step 8: Write JSON audit artifact
    write_audit_json(audit_result)


def write_audit_json(audit_result):
    """Write audit result to JSON file."""
    output_path = Path(r"D:\ableton claude\experiments\16_5_44_SUSTAIN_COMPILER_AUDIT.json")
    try:
        with open(output_path, "w") as f:
            json.dump(audit_result, f, indent=2, default=str)
        print(f"\n✓ Audit JSON written to: {output_path}")
    except Exception as e:
        print(f"\n✗ Failed to write audit JSON: {e}")

    print("\n" + "=" * 64)
    print("AUDIT COMPLETE")
    print("=" * 64)
    print(f"\nFinal Decision: {audit_result['decision']}")
    print(f"Mutations performed: {audit_result['serum_mutated']}")
    print(f"Evidence created: {audit_result['evidence_created']}")
    print(f"Capability promoted: {audit_result['capability_promoted']}")


if __name__ == "__main__":
    main()
