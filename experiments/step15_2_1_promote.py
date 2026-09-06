import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2 import statemodel, bridge, capability
from serum2.evidence.claim import (ClaimDefinition, ClaimEngine, SINGLE_FIELD, OBJECTIVELY_MEASURABLE)
from serum2.evidence.record import PASS

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
skel_meta, skel_body = bridge.capture_v8_skeleton(VST3)
families = statemodel.module_families(skel_body)

recs = {
    "attack": pickle.load(open(r"D:\ableton claude\experiments\_env_attack_record.pkl", "rb")),
    "decay": pickle.load(open(r"D:\ableton claude\experiments\_env_decay_record.pkl", "rb")),
    "sustain": pickle.load(open(r"D:\ableton claude\experiments\_env_sustain_record.pkl", "rb")),
    "release": pickle.load(open(r"D:\ableton claude\experiments\_env_release_record.pkl", "rb")),
}

defs = {}
METRIC_BY_FIELD = {"attack": "attack_onset_rms_db", "decay": "decay_window_rms_db",
                   "sustain": "sustain_window_rms_db", "release": "tail_rms_db"}
for name, target in [("attack", "kParamAttack"), ("decay", "kParamDecay"),
                     ("sustain", "kParamSustain"), ("release", "kParamRelease")]:
    defs[name] = ClaimDefinition(
        claim_type="envelope_field_%s" % name,
        subject_pattern={"kind": "envelope_field"},
        predicate="produces_measurable_effect",
        required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
        required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
        coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
        contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
        dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
        required_measurement={"metric_name": METRIC_BY_FIELD[name],
                              "target": "Env0.plainParams.%s" % target},
    )

eng = ClaimEngine(defs)
for name, rec in recs.items():
    g = eng.add(rec, name)
    print("%-10s claim_group=%s  gate=%s" % (name, g is not None, rec.gate_completeness()))

OPEN_MAPPING = {"lfoPointModAssignments", "midiMap"}
if "lfoPointModAssignments" not in families:
    families["lfoPointModAssignments"] = {}
if "midiMap" not in families:
    families["midiMap"] = {}
inv = capability.build_inventory(families, eng, open_mapping_families=OPEN_MAPPING)
print()
print(capability.report(inv))
print()
print("Env family:", inv["Env"].to_dict())
pickle.dump(inv, open(r"D:\ableton claude\experiments\_capability_inventory.pkl", "wb"))
