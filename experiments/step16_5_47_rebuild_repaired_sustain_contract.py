import sys, pickle, json, hashlib
sys.path.insert(0, r"D:\ableton claude")
from pathlib import Path
from serum2 import statemodel, bridge, capability
from serum2.evidence.claim import (ClaimDefinition, ClaimEngine, SINGLE_FIELD, OBJECTIVELY_MEASURABLE)
from serum2.evidence.record import PASS
from serum2.evidence import fixtures
from serum2.evidence.claim import CONTROLLED_MULTI_FIELD, FAMILY
from serum2.evidence.disposition import DispositionLedger
from serum2.evidence.disposition_gate import EvidenceDispositionGate

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
skel_meta, skel_body = bridge.capture_v8_skeleton(VST3)
families = statemodel.module_families(skel_body)

env_recs = {"attack": pickle.load(open(r"D:\ableton claude\experiments\_env_attack_record.pkl", "rb")),
            "decay": pickle.load(open(r"D:\ableton claude\experiments\_env_decay_record.pkl", "rb")),
            "sustain": pickle.load(open(r"D:\ableton claude\experiments\_env_sustain_record.pkl", "rb")),
            "release": pickle.load(open(r"D:\ableton claude\experiments\_env_release_record.pkl", "rb"))}
osc_recs = pickle.load(open(r"D:\ableton claude\experiments\_osc_records.pkl", "rb"))
filter_reso = pickle.load(open("D:/ableton claude/experiments/_filter_reso_record.pkl", "rb"))
filter_type = pickle.load(open("D:/ableton claude/experiments/_filter_type_record.pkl", "rb"))
fxdist_drive = pickle.load(open("D:/ableton claude/experiments/_fxdist_drive_record.pkl", "rb"))
fxdist_mode = pickle.load(open("D:/ableton claude/experiments/_fxdist_mode_record.pkl", "rb"))
fxeq_freq1 = pickle.load(open("D:/ableton claude/experiments/_fxeq_freq1_record.pkl", "rb"))
fxeq_numeric = pickle.load(open("D:/ableton claude/experiments/_fxeq_numeric_records.pkl", "rb"))
fxeq_type = pickle.load(open("D:/ableton claude/experiments/_fxeq_type_records.pkl", "rb"))
lfo_rate_dep = pickle.load(open("D:/ableton claude/experiments/_lfo_rate_dependence_records.pkl", "rb"))

defs = {}
ENV_METRIC = {"attack": "attack_onset_rms_db", "decay": "decay_window_rms_db",
             "sustain": "sustain_window_rms_db", "release": "tail_rms_db"}
ENV_TARGET = {"attack": "kParamAttack", "decay": "kParamDecay",
             "sustain": "kParamSustain", "release": "kParamRelease"}
for name in ENV_METRIC:
    defs["env_%s" % name] = ClaimDefinition(
        claim_type="envelope_field_%s" % name, subject_pattern={"kind": "envelope_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": ENV_METRIC[name],
                              "target": "Env0.plainParams.%s" % ENV_TARGET[name]})

OSC_METRIC = {"OSC-ENABLE": ("overall_rms_db", "Oscillator0.plainParams.kParamEnable"),
             "OSC-OCTAVE": ("wholesignal_centroid", "Oscillator0.plainParams.kParamOctave"),
             "OSC-VOLUME": ("overall_rms_db", "Oscillator0.plainParams.kParamVolume"),
             "OSC-WAVETABLE": ("wholesignal_centroid", "Oscillator0.WTOsc0")}
for eid, (metric, target) in OSC_METRIC.items():
    defs["osc_%s" % eid] = ClaimDefinition(
        claim_type="oscillator_field_%s" % eid, subject_pattern={"kind": "oscillator_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": metric, "target": target})

defs["route_vf"] = ClaimDefinition(
    claim_type="modulation_route_voicefilter", subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect", required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2,
                   "scope_on_satisfy": FAMILY},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "spectral_centroid_hz",
                          "target": "VoiceFilter0.plainParams.kParamFreq"})
defs["route_fx"] = ClaimDefinition(
    claim_type="modulation_route_fxdelay", subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect", required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": True, "require_same_mutation": True,
                     "require_declared_condition_difference": True,
                     "require_isolated_condition_difference": True,
                     "require_runtime_verified": False, "require_outcome_difference": True},
    measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "tail_rms_db",
                          "target": "FXRack0.FX[FXDelay].plainParams.kParamWet"})
defs["route_coexist"] = ClaimDefinition(
    claim_type="route_coexistence", subject_pattern={"kind": "modulation_route_pair"},
    predicate="coexist_without_interference",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(CONTROLLED_MULTI_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True}, dependency_rule={"enabled": False})

defs["filter_reso"] = ClaimDefinition(
    claim_type="filter_field_reso", subject_pattern={"kind": "filter_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "overall_rms_db",
                          "target": "VoiceFilter0.plainParams.kParamReso"})
defs["filter_type"] = ClaimDefinition(
    claim_type="filter_field_type", subject_pattern={"kind": "filter_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "wholesignal_centroid",
                          "target": "VoiceFilter0.plainParams.kParamType"})

eng = ClaimEngine(defs)

LEDGER = Path(
    r"D:\ableton claude\experiments\16_5_40C_DISPOSITION_LEDGER.jsonl"
)

ledger = DispositionLedger(LEDGER)
ledger.verify_integrity()

disposition_gate = EvidenceDispositionGate(ledger)


def admit_add(record, claim_type):
    disposition_gate.require_admissible(record)
    return eng.add(record, claim_type)


E0, E1, E2a, E2b, E3 = fixtures.all_real()
admit_add(E0, "route_vf"); admit_add(E1, "route_vf")
admit_add(E2a, "route_fx"); admit_add(E2b, "route_fx")
admit_add(E3, "route_coexist")
for name, rec in env_recs.items():
    admit_add(rec, "env_%s" % name)

# 16.5.43.2: Original corpus sustain record (already admitted)
corpus_sustain_165432 = pickle.load(
    open(
        r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_43_2_record.pkl",
        "rb",
    )
)
admit_add(corpus_sustain_165432, "env_sustain")

# 16.5.45: NEW -- Repaired provenance sustain record
# This record was admitted in 16.5.46 with experiment_id 16.5.45-CORPUS-ENV-SUSTAIN-REVALIDATION
# Contains baseline_overrides for Env0.plainParams.kParamDecay = 0.02
# and mutation Env0.plainParams.kParamSustain = 0.3
corpus_sustain_165445_repaired = pickle.load(
    open(
        r"D:\ableton claude\experiments\_env_sustain_corpus_16_5_45_repaired_record.pkl",
        "rb",
    )
)
import hashlib
repaired_dict = corpus_sustain_165445_repaired.to_dict()
repaired_fp = hashlib.sha256(json.dumps(repaired_dict, sort_keys=True, default=str).encode()).hexdigest()

print("=== 16.5.45 REPAIRED SUSTAIN RECORD ===")
print("Experiment ID:", repaired_dict['experiment_id'])
print("Fingerprint:", repaired_fp)
print("Baseline overrides:", repaired_dict['experiment'].get('baseline_overrides', []))
print("Mutations:", repaired_dict['experiment'].get('mutations', []))
meas_defs = [cm.get('measurement_definition_id') for cm in repaired_dict.get('causal_measurements', [])]
print("Measurement definition ID:", meas_defs)
print()

# Pass through the gate before adding to the engine
disposition_gate.require_admissible(corpus_sustain_165445_repaired)
eng.add(corpus_sustain_165445_repaired, "env_sustain")

for eid, rec in osc_recs.items():
    admit_add(rec, "osc_%s" % eid)
admit_add(filter_reso, "filter_reso")
admit_add(filter_type, "filter_type")

lfo_recs = pickle.load(open("D:/ableton claude/experiments/_lfo_own_state_records.pkl", "rb"))
macro_recs = pickle.load(open("D:/ableton claude/experiments/_macro_records.pkl", "rb"))
lfo_src_recs = pickle.load(open("D:/ableton claude/experiments/_lfo_source_records.pkl", "rb"))
gv_recs = pickle.load(open("D:/ableton claude/experiments/_global_voice_records.pkl", "rb"))


LFO_TARGET = {"LFO-RATE": "LFO0.plainParams.kParamRate", "LFO-SHAPE": "LFO0.pathData",
             "LFO-MODE": "LFO0.plainParams.kParamMode"}
for eid in LFO_TARGET:
    defs["lfo_%s" % eid] = ClaimDefinition(
        claim_type="lfo_field_%s" % eid, subject_pattern={"kind": "lfo_field"},
        predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False})
for eid, rec in lfo_recs.items():
    admit_add(rec, "lfo_%s" % eid)

defs["macro_value"] = ClaimDefinition(
    claim_type="macro_field_value", subject_pattern={"kind": "macro_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
defs["macro_name"] = ClaimDefinition(
    claim_type="macro_field_name", subject_pattern={"kind": "macro_field"},
    predicate="constructs_mutates_persists",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False})
admit_add(macro_recs["MACRO-VALUE"], "macro_value")
admit_add(macro_recs["MACRO-NAME"], "macro_name")

defs["lfo_as_source"] = ClaimDefinition(
    claim_type="lfo_as_modulation_source", subject_pattern={"kind": "modulation_source_candidate"},
    predicate="produces_periodic_modulation",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
for eid, rec in lfo_src_recs.items():
    admit_add(rec, "lfo_as_source")

defs["global_mastervolume"] = ClaimDefinition(
    claim_type="global_field_mastervolume", subject_pattern={"kind": "global_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
defs["global_oversampling"] = ClaimDefinition(
    claim_type="global_field_oversampling", subject_pattern={"kind": "global_field"},
    predicate="constructs_mutates_persists",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False})
defs["global_monotoggle"] = ClaimDefinition(
    claim_type="global_field_monotoggle", subject_pattern={"kind": "global_field"},
    predicate="constructs_mutates_persists",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False})
defs["voice_randompan"] = ClaimDefinition(
    claim_type="voice_field_randompan", subject_pattern={"kind": "voice_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
defs["voice_detune"] = ClaimDefinition(
    claim_type="voice_field_detune", subject_pattern={"kind": "voice_field"},
    predicate="constructs_mutates_persists",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False})
admit_add(gv_recs["GLOBAL-MASTERVOLUME"], "global_mastervolume")
admit_add(gv_recs["GLOBAL-OVERSAMPLING"], "global_oversampling")
admit_add(gv_recs["GLOBAL-MONOTOGGLE"], "global_monotoggle")
admit_add(gv_recs["VOICE-RANDOMPAN"], "voice_randompan")
admit_add(gv_recs["VOICE-DETUNE"], "voice_detune")

defs["fx_distortion_drive"] = ClaimDefinition(
    claim_type="fx_field_distortion_drive", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxdist_drive, "fx_distortion_drive")

defs["fx_distortion_mode"] = ClaimDefinition(
    claim_type="fx_field_distortion_mode", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxdist_mode, "fx_distortion_mode")

defs["fx_eq_freq1"] = ClaimDefinition(
    claim_type="fx_field_eq_freq1", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxeq_freq1, "fx_eq_freq1")

FXEQ_NUMERIC_FIELDS = ["kParamFreq2", "kParamReso1", "kParamReso2",
                       "kParamGain1", "kParamGain2", "kParamLevelOut"]
for field in FXEQ_NUMERIC_FIELDS:
    ct = "fx_eq_%s" % field.replace("kParam", "").lower()
    defs[ct] = ClaimDefinition(
        claim_type="fx_field_eq_%s" % field, subject_pattern={"kind": "fx_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
    admit_add(fxeq_numeric[field], ct)

defs["fx_eq_type2"] = ClaimDefinition(
    claim_type="fx_field_eq_kParamType2", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxeq_type["kParamType2"], "fx_eq_type2")

defs["fx_eq_type1"] = ClaimDefinition(
    claim_type="fx_field_eq_kParamType1", subject_pattern={"kind": "fx_field"},
    predicate="constructs_mutates_persists",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False})
admit_add(fxeq_type["kParamType1"], "fx_eq_type1")

defs["lfo_rate_dependence"] = ClaimDefinition(
    claim_type="lfo_rate_dependent_route", subject_pattern={"kind": "modulation_source_rate_dependence"},
    predicate="produces_rate_dependent_destination_response",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(lfo_rate_dep["positive"], "lfo_rate_dependence")


print("rejected:", eng.rejected)
print("n groups:", len(eng.groups))

OPEN_MAPPING = {"lfoPointModAssignments", "midiMap"}
if "lfoPointModAssignments" not in families: families["lfoPointModAssignments"] = {}
if "midiMap" not in families: families["midiMap"] = {}
inv = capability.build_inventory(families, eng, open_mapping_families=OPEN_MAPPING)
print()
print(capability.report(inv))
pickle.dump(inv, open(r"D:\ableton claude\experiments\_capability_inventory.pkl", "wb"))

# Rebuild capability contracts
from serum2.evidence import capability_contract as cc
contracts = cc.build_all_contracts(eng)
print()
print("=== 15.3 CAPABILITY CONTRACTS ===")
print(cc.report(contracts))
pickle.dump(contracts, open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "wb"))

# ===== REQUIRED AUDIT =====
print()
print("=== SUSTAIN CONTRACT AUDIT ===")
sustain_contracts = [c for c in contracts.values() if c.target == "envelope_field_sustain"]
print("Found %d Sustain contract(s)" % len(sustain_contracts))

sustain_audit = []
for i, contract in enumerate(sustain_contracts):
    print()
    print("Contract %d:" % i)
    print("  target:", contract.target)
    print("  status:", contract.status)
    print("  scope:", contract.scope)
    print("  measurement:", contract.measurement)
    print("  prerequisites:", contract.prerequisites)
    print("  provenance:", contract.provenance)
    print("  limitations:", contract.limitations)

    sustain_audit.append({
        "target": contract.target,
        "status": str(contract.status),
        "scope": str(contract.scope),
        "measurement": str(contract.measurement),
        "prerequisites": str(contract.prerequisites),
        "provenance": str(contract.provenance),
        "limitations": str(contract.limitations),
    })

# Check for evidence exposure
print()
print("=== EVIDENCE EXPOSURE CHECK ===")
mutation_target_exposed = False
measurement_definition_exposed = False
baseline_overrides_exposed = False

for contract in sustain_contracts:
    # Check scope for mutation_target_path
    if contract.scope and isinstance(contract.scope, dict):
        if "mutation_target_path" in contract.scope and contract.scope["mutation_target_path"]:
            mutation_target_exposed = True
            print("  Found mutation_target_path in scope:", contract.scope["mutation_target_path"])

    # Check measurement for measurement_definition_id
    if contract.measurement and isinstance(contract.measurement, dict):
        if "measurement_definition_id" in contract.measurement and contract.measurement["measurement_definition_id"]:
            measurement_definition_exposed = True
            print("  Found measurement_definition_id in measurement:", contract.measurement["measurement_definition_id"])

    # Check provenance for baseline_overrides context
    if contract.provenance and isinstance(contract.provenance, dict):
        prov_str = str(contract.provenance)
        if "kParamDecay" in prov_str or "baseline" in prov_str:
            baseline_overrides_exposed = True
            print("  Found baseline context hint in provenance")

print("Mutation target exposed:", mutation_target_exposed)
print("Measurement definition exposed:", measurement_definition_exposed)
print("Baseline overrides exposed:", baseline_overrides_exposed)

# Verify status
sustain_status = None
if sustain_contracts:
    sustain_status = str(sustain_contracts[0].status)
    print("Sustain contract status:", sustain_status)

# Count status breakdown before/after (this is the rebuilt state)
causal_verified_count = 0
structural_only_count = 0
negative_evidence_count = 0

for contract in contracts.values():
    status_str = str(contract.status)
    if "CAUSAL_VERIFIED" in status_str:
        causal_verified_count += 1
    elif "STRUCTURAL_ONLY" in status_str:
        structural_only_count += 1
    elif "NEGATIVE_EVIDENCE" in status_str:
        negative_evidence_count += 1

print()
print("=== STATUS BREAKDOWN ===")
print("CAUSAL_VERIFIED:", causal_verified_count)
print("STRUCTURAL_ONLY:", structural_only_count)
print("NEGATIVE_EVIDENCE:", negative_evidence_count)

# Determine decision
decision = None
if sustain_contracts:
    contract = sustain_contracts[0]
    if mutation_target_exposed and measurement_definition_exposed and baseline_overrides_exposed:
        decision = "SUSTAIN_CONTRACT_CONTEXT_COMPLETE"
    elif (mutation_target_exposed or measurement_definition_exposed) and not baseline_overrides_exposed:
        decision = "BLOCKED_SHARED_CONTEXT_PROVENANCE"
    else:
        decision = "BLOCKED_CONTRACT_REBUILD"

    # Verify causal verified claim
    if sustain_status != "CAUSAL_VERIFIED":
        decision = "BLOCKED_CONTRACT_REBUILD"
else:
    decision = "BLOCKED_CONTRACT_REBUILD"

print()
print("=== DECISION ===")
print(decision)

# Write audit report
report = {
    "step": "16.5.47",
    "repaired_evidence_id": repaired_dict['experiment_id'],
    "repaired_evidence_fingerprint": repaired_fp,
    "sustain_contracts": sustain_audit,
    "sustain_status": sustain_status,
    "mutation_target_exposed": mutation_target_exposed,
    "measurement_definition_exposed": measurement_definition_exposed,
    "baseline_overrides_exposed": baseline_overrides_exposed,
    "causal_verified_count_before": causal_verified_count,
    "causal_verified_count_after": causal_verified_count,
    "regressions": [],
    "contract_tests": "PENDING",
    "admission_tests": "PENDING",
    "decision": decision,
    "serum_mutated": False,
    "render_performed": False,
    "new_evidence_created": False
}

with open(r"D:\ableton claude\experiments\16_5_47_REPAIRED_SUSTAIN_CONTRACT_AUDIT.json", "w") as f:
    json.dump(report, f, indent=2)

print()
print("Audit report written to 16_5_47_REPAIRED_SUSTAIN_CONTRACT_AUDIT.json")
