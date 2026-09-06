import sys, pickle
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

# Cumulative: fold in the original ModSlot/VoiceFilter/FXRack route evidence
# too, so this inventory snapshot reflects ALL evidence gathered so far, not
# just this round. A promotion script that only sees its own round's records
# would silently regress prior families back to UNKNOWN in the saved artifact.
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

# LFO-source discovery: negative result, kept as evidence (audit trail), not
# promoted. required_gate needs causal=PASS to ever promote anything here --
# all 6 candidates show causal=FAIL, so this correctly stays UNKNOWN/no-op.
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

# Each of the five gets its OWN ClaimDefinition/ClaimGroup -- do not merge
# unrelated Global/Voice semantics into one family-wide claim.
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

# 15.2.8.2: FXDistortion Drive. Own ClaimDefinition/ClaimGroup, independent of
# Mode/Enable per user instruction ("keep the two capabilities independent").
# Target is a nested list-index path (FXRack0.FX.2.FXDistortion.plainParams.
# kParamDrive) reached via a baseline_override(FXRack0) + mutation(deep path) --
# only possible after the directional path/conflict fix.
defs["fx_distortion_drive"] = ClaimDefinition(
    claim_type="fx_field_distortion_drive", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxdist_drive, "fx_distortion_drive")

# 15.2.8.3: FXDistortion Mode. Own ClaimGroup, deliberately independent of
# Drive. Magnitude-only (no expected_direction claim baked in here either --
# that lives in the measurement plan's expected_direction="none").
defs["fx_distortion_mode"] = ClaimDefinition(
    claim_type="fx_field_distortion_mode", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxdist_mode, "fx_distortion_mode")

# 15.2.8.5: FXEQ Freq1 -- first field of the next FX family by corpus
# prevalence. Own ClaimGroup, independent of FXDistortion's two claims.
defs["fx_eq_freq1"] = ClaimDefinition(
    claim_type="fx_field_eq_freq1", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxeq_freq1, "fx_eq_freq1")

# 15.2.8.6: remaining FXEQ numeric controls, each its own independent
# ClaimGroup -- distinct fields, distinct capabilities.
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

# 15.2.8.7: FXEQ Type1/Type2, real corpus enum values (1.0/2.0), magnitude-only.
# Type2: EFFECT_OBSERVED, causal-required definition (same pattern as above).
defs["fx_eq_type2"] = ClaimDefinition(
    claim_type="fx_field_eq_kParamType2", subject_pattern={"kind": "fx_field"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE)
admit_add(fxeq_type["kParamType2"], "fx_eq_type2")

# Type1: causal was actually RUN and returned NO_OBSERVED_EFFECT (not
# NOT_RUN) -- an honest negative at this baseline/kernel/stimulus, not a
# contradiction. Promoted structurally (construct+mutate+persist proven);
# does not claim a causal effect this measurement didn't find.
defs["fx_eq_type1"] = ClaimDefinition(
    claim_type="fx_field_eq_kParamType1", subject_pattern={"kind": "fx_field"},
    predicate="constructs_mutates_persists",
    required_gate={"load": PASS, "persistence": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 1},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False})
admit_add(fxeq_type["kParamType1"], "fx_eq_type1")

# 16.4.3c-10: formal, scoped evidence for source[0]=6's rate-dependent causal
# effect under an explicit LFO0 baseline_override. Deliberately does NOT
# assert universal source-ID semantics (see LFO-SOURCE-CANDIDATES-UNVERIFIED-1
# and the still-untouched LFO-SOURCE-IDENTITY-1). Separate ClaimGroup from
# the pre-existing modulation_route_voicefilter capability -- that capability
# was already CAUSAL_VERIFIED independent of this finding and is not being
# retroactively relabeled.
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
print()
print("Oscillator family:", inv["Oscillator"].to_dict())
print("VoiceFilter family:", inv["VoiceFilter"].to_dict())
print("LFO family:", inv["LFO"].to_dict())
print("Macro family:", inv["Macro"].to_dict())
print("Global family:", inv["Global"].to_dict())
print("VoicePanel family:", inv.get("VoicePanel", "N/A (check statemodel key name)"))
print("FXRack family (carries FXDistortion.Drive evidence):", inv["FXRack"].to_dict())
print()
print("=== LFO-as-source claim (expected: no promotion, negative evidence kept) ===")
lfo_src_key = [k for k in eng.groups if k[0].startswith("lfo_as_modulation_source")]
for k in lfo_src_key:
    g = eng.groups[k]
    print(" group:", k, "-> status:", capability.status_from_claim_group(g),
          "supporting:", g.supporting_evidence, "contradicting:", g.contradicting_evidence)
pickle.dump(inv, open(r"D:\ableton claude\experiments\_capability_inventory.pkl", "wb"))

# 15.3: Capability Contracts -- read-only derived layer over the ClaimEngine.
# Built AFTER every promotion above, from the SAME eng.groups -- no separate
# construction path, so there is exactly one source of truth per group.
from serum2.evidence import capability_contract as cc
contracts = cc.build_all_contracts(eng)
print()
print("=== 15.3 CAPABILITY CONTRACTS ===")
print(cc.report(contracts))
pickle.dump(contracts, open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "wb"))
