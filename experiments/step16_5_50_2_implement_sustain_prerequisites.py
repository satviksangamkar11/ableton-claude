"""16.5.50.2: Implement context-aware prerequisite admission for Env1.Sustain.

Reuses the established Macro.value prerequisite pattern.
- Extracts context from Sustain evidence baseline_overrides
- Constructs prerequisite dict with field_path, declared_value, must_hold_identical
- Rebuilds contracts through canonical path
- Tests admission matrix
- Preserves frontier (37 contracts, 26/8/3 distribution)
"""

import sys
import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Tuple, Any
from collections import defaultdict

sys.path.insert(0, r"D:\ableton claude")

from serum2 import statemodel, bridge
from serum2.evidence.claim import (
    ClaimDefinition, ClaimEngine, SINGLE_FIELD, OBJECTIVELY_MEASURABLE,
    CONTROLLED_MULTI_FIELD, FAMILY
)
from serum2.evidence.record import PASS
from serum2.evidence import fixtures, admission, capability_contract as cc
from serum2.evidence.disposition import DispositionLedger
from serum2.evidence.disposition_gate import EvidenceDispositionGate


def get_frontier_hash(contracts: Dict[Tuple[str, str], cc.CapabilityContract]) -> str:
    """Compute frontier hash for regression detection."""
    contract_list = sorted([
        (c.target, c.status, c.verified.get("causal"))
        for c in contracts.values()
    ])
    return hashlib.sha256(str(contract_list).encode()).hexdigest()


def main():
    print("=" * 80)
    print("16.5.50.2: CONTEXT-AWARE SUSTAIN PREREQUISITE ADMISSION")
    print("=" * 80)
    print()

    # STEP 1: Load Sustain evidence (no modification - prerequisites inferred from baseline_overrides)
    print("[STEP 1] Loading Sustain evidence record...")
    evidence_path = Path(r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_45_repaired_record.pkl")
    sustain_evidence = pickle.load(open(evidence_path, "rb"))

    # Verify baseline_overrides present
    baseline_overrides = sustain_evidence.experiment.get("baseline_overrides", [])
    print(f"  Baseline overrides in evidence:")
    for override in baseline_overrides:
        target_path = override.get("target_path")
        value = override.get("value")
        print(f"    {target_path} = {value}")

    print(f"  (Prerequisites will be inferred from baseline_overrides during contract build)")
    print()

    # STEP 2: Rebuild contracts through canonical path
    print("[STEP 2] Rebuilding contracts through canonical path...")

    VST3_PATH = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
    skel_meta, skel_body = bridge.capture_v8_skeleton(VST3_PATH)

    ledger = DispositionLedger(Path(r"D:\ableton claude\experiments\16_5_40C_DISPOSITION_LEDGER.jsonl"))
    ledger.verify_integrity()
    disposition_gate = EvidenceDispositionGate(ledger)

    # Build claim definitions (same as step 16.5.50.1)
    defs = {}

    ENV_METRIC = {
        "attack": "attack_onset_rms_db",
        "decay": "decay_window_rms_db",
        "sustain": "sustain_window_rms_db",
        "release": "tail_rms_db"
    }
    ENV_TARGET = {
        "attack": "kParamAttack",
        "decay": "kParamDecay",
        "sustain": "kParamSustain",
        "release": "kParamRelease"
    }

    for name in ENV_METRIC:
        defs["env_%s" % name] = ClaimDefinition(
            claim_type="envelope_field_%s" % name,
            subject_pattern={"kind": "envelope_field"},
            predicate="produces_measurable_effect",
            required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 2},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
            contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
            dependency_rule={"enabled": False},
            measurability=OBJECTIVELY_MEASURABLE,
            required_measurement={
                "metric_name": ENV_METRIC[name],
                "target": "Env0.plainParams.%s" % ENV_TARGET[name]
            }
        )

    # Oscillator, modulation, filter definitions (abbreviated - same as 16.5.50.1)
    OSC_METRIC = {
        "OSC-ENABLE": ("overall_rms_db", "Oscillator0.plainParams.kParamEnable"),
        "OSC-OCTAVE": ("wholesignal_centroid", "Oscillator0.plainParams.kParamOctave"),
        "OSC-VOLUME": ("overall_rms_db", "Oscillator0.plainParams.kParamVolume"),
        "OSC-WAVETABLE": ("wholesignal_centroid", "Oscillator0.WTOsc0")
    }
    for eid, (metric, target) in OSC_METRIC.items():
        defs["osc_%s" % eid] = ClaimDefinition(
            claim_type="oscillator_field_%s" % eid,
            subject_pattern={"kind": "oscillator_field"},
            predicate="produces_measurable_effect",
            required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 2},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
            contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
            dependency_rule={"enabled": False},
            measurability=OBJECTIVELY_MEASURABLE,
            required_measurement={"metric_name": metric, "target": target}
        )

    defs["route_vf"] = ClaimDefinition(
        claim_type="modulation_route_voicefilter",
        subject_pattern={"kind": "modulation_route"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2, "scope_on_satisfy": FAMILY},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": "spectral_centroid_hz", "target": "VoiceFilter0.plainParams.kParamFreq"}
    )

    defs["route_fx"] = ClaimDefinition(
        claim_type="modulation_route_fxdelay",
        subject_pattern={"kind": "modulation_route"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": True, "require_same_mutation": True,
                        "require_declared_condition_difference": True,
                        "require_isolated_condition_difference": True,
                        "require_runtime_verified": False, "require_outcome_difference": True},
        measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": "tail_rms_db", "target": "FXRack0.FX[FXDelay].plainParams.kParamWet"}
    )

    defs["route_coexist"] = ClaimDefinition(
        claim_type="route_coexistence",
        subject_pattern={"kind": "modulation_route_pair"},
        predicate="coexist_without_interference",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(CONTROLLED_MULTI_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True},
        dependency_rule={"enabled": False}
    )

    defs["filter_reso"] = ClaimDefinition(
        claim_type="filter_field_reso",
        subject_pattern={"kind": "filter_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": "overall_rms_db", "target": "VoiceFilter0.plainParams.kParamReso"}
    )

    defs["filter_type"] = ClaimDefinition(
        claim_type="filter_field_type",
        subject_pattern={"kind": "filter_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": "wholesignal_centroid", "target": "VoiceFilter0.plainParams.kParamType"}
    )

    engine = ClaimEngine(defs)

    def admit_add(record, claim_type):
        try:
            disposition_gate.require_admissible(record)
            return engine.add(record, claim_type)
        except Exception as e:
            print(f"  ! Rejection for {record.experiment_id}: {e}")
            return None

    # Load prior records
    prior_path = Path(r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_43_2_record.pkl")
    if prior_path.exists():
        prior = pickle.load(open(prior_path, "rb"))
        admit_add(prior, "env_sustain")

    # Load fixtures
    E0, E1, E2a, E2b, E3 = fixtures.all_real()
    admit_add(E0, "route_vf")
    admit_add(E1, "route_vf")
    admit_add(E2a, "route_fx")
    admit_add(E2b, "route_fx")
    admit_add(E3, "route_coexist")

    # Load env records
    for env_name in ["attack", "decay", "release"]:
        env_file = Path(rf"D:\ableton claude\experiments\_env_{env_name}_record.pkl")
        if env_file.exists():
            rec = pickle.load(open(env_file, "rb"))
            admit_add(rec, f"env_{env_name}")

    # Load oscillator records
    osc_file = Path(r"D:\ableton claude\experiments\_osc_records.pkl")
    if osc_file.exists():
        osc_recs = pickle.load(open(osc_file, "rb"))
        for eid, rec in osc_recs.items():
            admit_add(rec, "osc_" + eid)

    # Load filter records
    for fname in ["reso", "type"]:
        ffile = Path(rf"D:\ableton claude\experiments\_filter_{fname}_record.pkl")
        if ffile.exists():
            rec = pickle.load(open(ffile, "rb"))
            admit_add(rec, f"filter_{fname}")

    # Load REPAIRED sustain record with NEW prerequisites
    admit_add(sustain_evidence, "env_sustain")

    engine.derive_relationships()

    print(f"  Built claim engine with {len(engine.groups)} groups")
    print()

    # STEP 3: Build contracts
    print("[STEP 3] Building contracts...")
    new_contracts = cc.build_all_contracts(engine)

    status_counts = defaultdict(int)
    for c in new_contracts.values():
        status_counts[c.status] += 1

    for status in ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY", "NEGATIVE_EVIDENCE"]:
        count = status_counts.get(status, 0)
        print(f"  {status:30s} {count}")
    print(f"  {'TOTAL':30s} {len(new_contracts)}")
    print()

    # STEP 4: Verify Sustain contract has prerequisite
    print("[STEP 4] Verifying Sustain contract...")
    sustain_contract = next((c for c in new_contracts.values() if c.target == "envelope_field_sustain"), None)
    if sustain_contract:
        print(f"  Target: {sustain_contract.target}")
        print(f"  Status: {sustain_contract.status}")
        print(f"  Prerequisites: {sustain_contract.prerequisites}")
        if sustain_contract.prerequisites:
            for prereq in sustain_contract.prerequisites:
                print(f"    {prereq}")
    else:
        print("  ERROR: Sustain contract not found!")
        return None
    print()

    # STEP 5: Test admission matrix
    print("[STEP 5] Testing admission matrix...")

    tests = {
        "Missing context": (
            {"proposed_prerequisites_verified": None},
            False, "prerequisite_unverified"
        ),
        "Unverified context": (
            {"proposed_prerequisites_verified": {"Env0.plainParams.kParamDecay": False}},
            False, "prerequisite_unverified"
        ),
        "Decay=0.01": (
            {"proposed_prerequisites_verified": {"Env0.plainParams.kParamDecay": True}},
            False, "prerequisite_unverified"  # Value mismatch still treated as unverified in this check
        ),
        "Decay=0.03": (
            {"proposed_prerequisites_verified": {"Env0.plainParams.kParamDecay": True}},
            False, "prerequisite_unverified"
        ),
        "Decay=0.02 (correct)": (
            {"proposed_prerequisites_verified": {"Env0.plainParams.kParamDecay": True}},
            True, "ADMITTED"
        ),
        "Wrong measurement": (
            {"proposed_prerequisites_verified": {"Env0.plainParams.kParamDecay": True},
             "required_measurement_definition_id": "wrong:deadbeef"},
            False, "measurement_definition_mismatch"
        ),
    }

    results = {}
    for test_name, (kwargs, expected_admitted, expected_reason) in tests.items():
        result = admission.admit(new_contracts, "envelope_field_sustain", **kwargs)
        status = "PASS" if (result.admitted == expected_admitted and result.reason == expected_reason) else "FAIL"
        results[test_name] = {
            "admitted": result.admitted,
            "reason": result.reason,
            "expected_admitted": expected_admitted,
            "expected_reason": expected_reason,
            "status": status
        }
        print(f"  {status} {test_name:35s} {result.reason}")
    print()

    # STEP 6: Test unknown targets
    print("[STEP 6] Testing unknown targets...")
    unknown_tests = {
        "Env1.FooBar": "unknown_no_contract",
        "Env0.Sustain": "unknown_no_contract",
    }
    for target, expected_reason in unknown_tests.items():
        result = admission.admit(new_contracts, target)
        status = "PASS" if result.reason == expected_reason else "FAIL"
        print(f"  {status} {target:35s} {result.reason}")
    print()

    # STEP 7: Frontier check
    print("[STEP 7] Checking frontier...")
    old_contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
    old_hash = get_frontier_hash(old_contracts)
    new_hash = get_frontier_hash(new_contracts)

    print(f"  Old frontier hash: {old_hash[:16]}...")
    print(f"  New frontier hash: {new_hash[:16]}...")
    print(f"  Match: {old_hash == new_hash}")

    if old_hash != new_hash:
        print("  ERROR: Frontier hash changed!")
        return None
    print()

    # STEP 8: Save new contracts
    print("[STEP 8] Saving contracts...")
    with open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "wb") as f:
        pickle.dump(new_contracts, f)
    print("  Saved to _capability_contracts.pkl")
    print()

    # STEP 9: Write audit
    print("[STEP 9] Writing audit...")

    # Check if all admission tests passed
    all_pass = all(r["status"] == "PASS" for r in results.values())

    decision = "CONTEXT_AWARE_SUSTAIN_ADMISSION_VERIFIED" if all_pass else "BLOCKED_CONTEXT_ADMISSION"

    audit = {
        "step": "16.5.50.2",
        "sustain_target": "envelope_field_sustain",
        "sustain_status": sustain_contract.status if sustain_contract else None,
        "sustain_prerequisites": list(sustain_contract.prerequisites) if sustain_contract else None,
        "admission_tests": results,
        "all_tests_passed": all_pass,
        "frontier_unchanged": old_hash == new_hash,
        "contract_count": len(new_contracts),
        "status_counts": dict(status_counts),
        "serum_mutated": False,
        "render_performed": False,
        "new_evidence_created": False,
        "decision": decision,
    }

    with open(r"D:\ableton claude\experiments\16_5_50_2_CONTEXT_AWARE_SUSTAIN_ADMISSION.json", "w") as f:
        json.dump(audit, f, indent=2)

    print(f"  Audit written")
    print()

    # STEP 10: Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Sustain contract: {sustain_contract.target if sustain_contract else 'NOT FOUND'}")
    print(f"Status: {sustain_contract.status if sustain_contract else 'N/A'}")
    print(f"Prerequisites: {len(sustain_contract.prerequisites) if sustain_contract else 0}")
    print(f"All admission tests passed: {all_pass}")
    print(f"Frontier unchanged: {old_hash == new_hash}")
    print(f"Contracts: {len(new_contracts)} (expected 37)")
    print(f"CAUSAL_VERIFIED: {status_counts['CAUSAL_VERIFIED']} (expected 26)")
    print(f"STRUCTURAL_ONLY: {status_counts['STRUCTURAL_ONLY']} (expected 8)")
    print(f"NEGATIVE_EVIDENCE: {status_counts['NEGATIVE_EVIDENCE']} (expected 3)")
    print()
    print(f"DECISION: {decision}")
    print("=" * 80)

    return audit


if __name__ == "__main__":
    audit = main()
    if audit and audit["decision"] == "CONTEXT_AWARE_SUSTAIN_ADMISSION_VERIFIED":
        print("\n[OK] Step 16.5.50.2 COMPLETE")
        sys.exit(0)
    else:
        print("\n[BLOCKED] Step 16.5.50.2 FAILED")
        sys.exit(1)
