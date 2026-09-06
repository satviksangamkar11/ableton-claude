"""16.5.50.1: Restore cumulative capability contracts artifact.

OBJECTIVE: Repair the cumulative capability artifacts broken by the 16.5.48
provenance script and preserve the newly registered Env1.Sustain semantic target.

This script rebuilds the complete cumulative capability artifacts using the
canonical promotion architecture from step16_5_43_3, adding the repaired sustain
record and extended provenance from 16.5.48.
"""

import sys
import json
import pickle
from pathlib import Path
from typing import Dict, Tuple, Any, List, Optional
from collections import defaultdict

sys.path.insert(0, r"D:\ableton claude")

from serum2 import statemodel, bridge, capability
from serum2.evidence.claim import (
    ClaimDefinition, ClaimEngine, SINGLE_FIELD, OBJECTIVELY_MEASURABLE,
    CONTROLLED_MULTI_FIELD, FAMILY
)
from serum2.evidence.record import PASS
from serum2.evidence import fixtures
from serum2.evidence.disposition import DispositionLedger, evidence_fingerprint
from serum2.evidence.disposition_gate import EvidenceDispositionGate
from serum2.evidence import capability_contract as cc

# Configuration
VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
DISPOSITION_LEDGER = Path(r"D:\ableton claude\experiments\16_5_40C_DISPOSITION_LEDGER.jsonl")
CONTRACTS_PKL = Path(r"D:\ableton claude\experiments\_capability_contracts.pkl")
INVENTORY_PKL = Path(r"D:\ableton claude\experiments\_capability_inventory.pkl")
AUDIT_OUTPUT = Path(r"D:\ableton claude\experiments\16_5_50_1_CUMULATIVE_CONTRACT_REPAIR.json")

EXPECTED_CAUSAL_VERIFIED = 26
EXPECTED_STRUCTURAL_ONLY = 8
EXPECTED_NEGATIVE_EVIDENCE = 3
EXPECTED_TOTAL = 37


def get_current_contract_counts() -> Dict[str, int]:
    """Read current contract counts before restoration."""
    if not CONTRACTS_PKL.exists():
        return {}
    try:
        with open(CONTRACTS_PKL, "rb") as f:
            current = pickle.load(f)
        counts = defaultdict(int)
        for contract in current.values():
            counts[contract.status] += 1
        return dict(counts)
    except Exception as e:
        print(f"Warning: Could not read current contracts: {e}")
        return {}


def main():
    print("=" * 80)
    print("16.5.50.1: RESTORE CUMULATIVE CAPABILITY CONTRACTS")
    print("=" * 80)

    # Record current state
    print("\n=== STEP 0: Assess current state ===")
    current_counts = get_current_contract_counts()
    current_total = sum(current_counts.values())
    print(f"Current contract artifact contains {current_total} contracts:")
    for status in ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY", "NEGATIVE_EVIDENCE", "UNSUPPORTED", "BLOCKED_CONTRADICTED"]:
        count = current_counts.get(status, 0)
        print(f"  {status:30s} {count}")

    print("\n=== STEP 1: Initialize infrastructure ===")
    VST3_PATH = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
    skel_meta, skel_body = bridge.capture_v8_skeleton(VST3_PATH)
    families = statemodel.module_families(skel_body)
    print(f"Captured skeleton with {len(families)} families")

    # Load disposition gate
    ledger = DispositionLedger(DISPOSITION_LEDGER)
    ledger.verify_integrity()
    print(f"Disposition ledger verified")

    disposition_gate = EvidenceDispositionGate(ledger)

    def admit_add(record, claim_type, eng):
        try:
            disposition_gate.require_admissible(record)
            return eng.add(record, claim_type)
        except Exception as e:
            print(f"  ! Admission rejected for {record.experiment_id}: {e}")
            return None

    print("\n=== STEP 2: Build all claim definitions ===")
    defs = {}

    # Envelope fields
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

    # Oscillator fields
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

    # Modulation routes
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

    # Filter fields
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

    # LFO fields
    LFO_TARGET = {
        "LFO-RATE": "LFO0.plainParams.kParamRate",
        "LFO-SHAPE": "LFO0.pathData",
        "LFO-MODE": "LFO0.plainParams.kParamMode"
    }
    for eid in LFO_TARGET:
        defs["lfo_%s" % eid] = ClaimDefinition(
            claim_type="lfo_field_%s" % eid,
            subject_pattern={"kind": "lfo_field"},
            predicate="constructs_mutates_persists",
            required_gate={"load": PASS, "persistence": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 2},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
            contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
            dependency_rule={"enabled": False}
        )

    # Macro fields
    defs["macro_value"] = ClaimDefinition(
        claim_type="macro_field_value",
        subject_pattern={"kind": "macro_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )
    defs["macro_name"] = ClaimDefinition(
        claim_type="macro_field_name",
        subject_pattern={"kind": "macro_field"},
        predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}
    )

    # LFO-as-source (negative evidence)
    defs["lfo_as_source"] = ClaimDefinition(
        claim_type="lfo_as_modulation_source",
        subject_pattern={"kind": "modulation_source_candidate"},
        predicate="produces_periodic_modulation",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )

    # Global and Voice fields
    defs["global_mastervolume"] = ClaimDefinition(
        claim_type="global_field_mastervolume",
        subject_pattern={"kind": "global_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )
    defs["global_oversampling"] = ClaimDefinition(
        claim_type="global_field_oversampling",
        subject_pattern={"kind": "global_field"},
        predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}
    )
    defs["global_monotoggle"] = ClaimDefinition(
        claim_type="global_field_monotoggle",
        subject_pattern={"kind": "global_field"},
        predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}
    )
    defs["voice_randompan"] = ClaimDefinition(
        claim_type="voice_field_randompan",
        subject_pattern={"kind": "voice_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )
    defs["voice_detune"] = ClaimDefinition(
        claim_type="voice_field_detune",
        subject_pattern={"kind": "voice_field"},
        predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}
    )

    # FX Distortion
    defs["fx_distortion_drive"] = ClaimDefinition(
        claim_type="fx_field_distortion_drive",
        subject_pattern={"kind": "fx_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )
    defs["fx_distortion_mode"] = ClaimDefinition(
        claim_type="fx_field_distortion_mode",
        subject_pattern={"kind": "fx_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )

    # FX EQ
    defs["fx_eq_freq1"] = ClaimDefinition(
        claim_type="fx_field_eq_freq1",
        subject_pattern={"kind": "fx_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )
    FXEQ_NUMERIC_FIELDS = ["kParamFreq2", "kParamReso1", "kParamReso2", "kParamGain1", "kParamGain2", "kParamLevelOut"]
    for field in FXEQ_NUMERIC_FIELDS:
        ct = "fx_eq_%s" % field.replace("kParam", "").lower()
        defs[ct] = ClaimDefinition(
            claim_type="fx_field_eq_%s" % field,
            subject_pattern={"kind": "fx_field"},
            predicate="produces_measurable_effect",
            required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
            dependency_rule={"enabled": False},
            measurability=OBJECTIVELY_MEASURABLE
        )

    defs["fx_eq_type2"] = ClaimDefinition(
        claim_type="fx_field_eq_kParamType2",
        subject_pattern={"kind": "fx_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )
    defs["fx_eq_type1"] = ClaimDefinition(
        claim_type="fx_field_eq_kParamType1",
        subject_pattern={"kind": "fx_field"},
        predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}
    )

    # LFO rate dependence
    defs["lfo_rate_dependence"] = ClaimDefinition(
        claim_type="lfo_rate_dependent_route",
        subject_pattern={"kind": "modulation_source_rate_dependence"},
        predicate="produces_rate_dependent_destination_response",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False},
        measurability=OBJECTIVELY_MEASURABLE
    )

    print(f"  Built {len(defs)} claim definitions")

    # Create engine with ALL definitions
    print("\n=== STEP 3: Create ClaimEngine ===")
    eng = ClaimEngine(defs)
    print(f"  Engine created with {len(defs)} definitions")

    # Add all records
    print("\n=== STEP 4: Add all evidence records ===")
    E0, E1, E2a, E2b, E3 = fixtures.all_real()
    admit_add(E0, "route_vf", eng)
    admit_add(E1, "route_vf", eng)
    admit_add(E2a, "route_fx", eng)
    admit_add(E2b, "route_fx", eng)
    admit_add(E3, "route_coexist", eng)

    env_recs = {
        "attack": pickle.load(open(r"D:\ableton claude\experiments\_env_attack_record.pkl", "rb")),
        "decay": pickle.load(open(r"D:\ableton claude\experiments\_env_decay_record.pkl", "rb")),
        "sustain": pickle.load(open(r"D:\ableton claude\experiments\_env_sustain_record.pkl", "rb")),
        "release": pickle.load(open(r"D:\ableton claude\experiments\_env_release_record.pkl", "rb"))
    }
    for name, rec in env_recs.items():
        admit_add(rec, "env_%s" % name, eng)

    corpus_sustain = pickle.load(open(r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_43_2_record.pkl", "rb"))
    admit_add(corpus_sustain, "env_sustain", eng)

    sustain_repaired_file = Path(r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_45_repaired_record.pkl")
    if sustain_repaired_file.exists():
        sustain_repaired = pickle.load(open(sustain_repaired_file, "rb"))
        admit_add(sustain_repaired, "env_sustain", eng)
        print(f"  Added repaired sustain record: {sustain_repaired.experiment_id}")

    osc_recs = pickle.load(open(r"D:\ableton claude\experiments\_osc_records.pkl", "rb"))
    for eid, rec in osc_recs.items():
        admit_add(rec, "osc_%s" % eid, eng)

    filter_reso = pickle.load(open(r"D:\ableton claude\experiments\_filter_reso_record.pkl", "rb"))
    filter_type = pickle.load(open(r"D:\ableton claude\experiments\_filter_type_record.pkl", "rb"))
    admit_add(filter_reso, "filter_reso", eng)
    admit_add(filter_type, "filter_type", eng)

    lfo_recs = pickle.load(open(r"D:\ableton claude\experiments\_lfo_own_state_records.pkl", "rb"))
    for eid, rec in lfo_recs.items():
        admit_add(rec, "lfo_%s" % eid, eng)

    macro_recs = pickle.load(open(r"D:\ableton claude\experiments\_macro_records.pkl", "rb"))
    admit_add(macro_recs["MACRO-VALUE"], "macro_value", eng)
    admit_add(macro_recs["MACRO-NAME"], "macro_name", eng)

    lfo_src_recs = pickle.load(open(r"D:\ableton claude\experiments\_lfo_source_records.pkl", "rb"))
    for eid, rec in lfo_src_recs.items():
        admit_add(rec, "lfo_as_source", eng)

    gv_recs = pickle.load(open(r"D:\ableton claude\experiments\_global_voice_records.pkl", "rb"))
    admit_add(gv_recs["GLOBAL-MASTERVOLUME"], "global_mastervolume", eng)
    admit_add(gv_recs["GLOBAL-OVERSAMPLING"], "global_oversampling", eng)
    admit_add(gv_recs["GLOBAL-MONOTOGGLE"], "global_monotoggle", eng)
    admit_add(gv_recs["VOICE-RANDOMPAN"], "voice_randompan", eng)
    admit_add(gv_recs["VOICE-DETUNE"], "voice_detune", eng)

    fxdist_drive = pickle.load(open(r"D:\ableton claude\experiments\_fxdist_drive_record.pkl", "rb"))
    fxdist_mode = pickle.load(open(r"D:\ableton claude\experiments\_fxdist_mode_record.pkl", "rb"))
    fxeq_freq1 = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))
    fxeq_numeric = pickle.load(open(r"D:\ableton claude\experiments/_fxeq_numeric_records.pkl", "rb"))
    fxeq_type = pickle.load(open(r"D:\ableton claude\experiments/_fxeq_type_records.pkl", "rb"))
    lfo_rate_dep = pickle.load(open(r"D:\ableton claude\experiments/_lfo_rate_dependence_records.pkl", "rb"))

    admit_add(fxdist_drive, "fx_distortion_drive", eng)
    admit_add(fxdist_mode, "fx_distortion_mode", eng)
    admit_add(fxeq_freq1, "fx_eq_freq1", eng)
    for field in FXEQ_NUMERIC_FIELDS:
        ct = "fx_eq_%s" % field.replace("kParam", "").lower()
        admit_add(fxeq_numeric[field], ct, eng)
    admit_add(fxeq_type["kParamType2"], "fx_eq_type2", eng)
    admit_add(fxeq_type["kParamType1"], "fx_eq_type1", eng)
    admit_add(lfo_rate_dep["positive"], "lfo_rate_dependence", eng)

    print(f"  Records in engine: {len(eng.records)}")
    print(f"  Claim groups: {len(eng.groups)}")

    print("\n=== STEP 5: Build contracts ===")
    contracts = cc.build_all_contracts(eng)
    print(f"  Built {len(contracts)} contracts")

    status_counts = defaultdict(int)
    for c in contracts.values():
        status_counts[c.status] += 1

    for status in ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY", "NEGATIVE_EVIDENCE", "UNSUPPORTED", "BLOCKED_CONTRADICTED"]:
        count = status_counts.get(status, 0)
        print(f"    {status:30s} {count}")

    # Verify sustain
    sustain_found = False
    for c in contracts.values():
        if c.target == "envelope_field_sustain":
            sustain_found = True
            print(f"\n  Sustain contract: status={c.status}")
            break

    if not sustain_found:
        print(f"\n  ERROR: Sustain contract NOT found!")

    # Check counts
    causal = status_counts.get("CAUSAL_VERIFIED", 0)
    struct = status_counts.get("STRUCTURAL_ONLY", 0)
    neg = status_counts.get("NEGATIVE_EVIDENCE", 0)
    total = len(contracts)

    print(f"\n=== STEP 6: Validate contract counts ===")
    print(f"Expected: {EXPECTED_CAUSAL_VERIFIED} CAUSAL_VERIFIED, {EXPECTED_STRUCTURAL_ONLY} STRUCTURAL_ONLY, {EXPECTED_NEGATIVE_EVIDENCE} NEGATIVE_EVIDENCE")
    print(f"Actual:   {causal} CAUSAL_VERIFIED, {struct} STRUCTURAL_ONLY, {neg} NEGATIVE_EVIDENCE, {total} TOTAL")

    regressions = []
    if causal < EXPECTED_CAUSAL_VERIFIED:
        regressions.append(f"CAUSAL_VERIFIED: {causal} < {EXPECTED_CAUSAL_VERIFIED}")
    if struct < EXPECTED_STRUCTURAL_ONLY:
        regressions.append(f"STRUCTURAL_ONLY: {struct} < {EXPECTED_STRUCTURAL_ONLY}")
    if neg < EXPECTED_NEGATIVE_EVIDENCE:
        regressions.append(f"NEGATIVE_EVIDENCE: {neg} < {EXPECTED_NEGATIVE_EVIDENCE}")

    if regressions:
        print("\nREGRESSIONS:")
        for msg in regressions:
            print(f"  - {msg}")
    else:
        print("\nAll counts validated OK!")

    # Save artifacts
    print(f"\n=== STEP 7: Save artifacts ===")
    with open(CONTRACTS_PKL, "wb") as f:
        pickle.dump(contracts, f)
    print(f"  Saved {len(contracts)} contracts to {CONTRACTS_PKL}")

    # Write audit
    decision = "CUMULATIVE_CONTRACT_STATE_RESTORED" if not regressions else "BLOCKED_CUMULATIVE_REBUILD"

    audit = {
        "step": "16.5.50.1",
        "current_contract_count_before": current_total,
        "rebuilt_contract_count": total,
        "causal_verified_count": causal,
        "structural_only_count": struct,
        "negative_evidence_count": neg,
        "expected_causal_verified": EXPECTED_CAUSAL_VERIFIED,
        "expected_structural_only": EXPECTED_STRUCTURAL_ONLY,
        "expected_negative_evidence": EXPECTED_NEGATIVE_EVIDENCE,
        "expected_total": EXPECTED_TOTAL,
        "sustain_found": sustain_found,
        "regressions": regressions,
        "serum_mutated": False,
        "render_performed": False,
        "new_evidence_created": False,
        "decision": decision,
    }

    with open(AUDIT_OUTPUT, "w") as f:
        json.dump(audit, f, indent=2)

    print(f"  Audit written to {AUDIT_OUTPUT}")

    print("\n" + "=" * 80)
    print(f"DECISION: {decision}")
    print("=" * 80)

    return 0 if decision == "CUMULATIVE_CONTRACT_STATE_RESTORED" else 1


if __name__ == "__main__":
    sys.exit(main())
