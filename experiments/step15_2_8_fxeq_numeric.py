"""15.2.8.6: FXEQ remaining numeric controls, each an independent single-field
capability, reusing the proven real corpus FXRack0 context (body_idx=4).
Ranges clamp-probed directly (not assumed):
  Freq2  [21.533, 20000.0] Hz  -- same curve as Freq1
  Reso1  [0.0, 100.0]
  Reso2  [0.0, 100.0]
  Gain1  [-24.0, 24.0] dB -- writing exactly 0.0 is dropped (sparse default)
  Gain2  [-24.0, 24.0] dB -- same sparse-default behavior
  LevelOut [0.0, 1.0]
LevelOut gets a directional claim (raising output level -> louder, a directly
justified hypothesis via overall_rms_db). All others stay magnitude-only:
their causal sign here would depend on the other band's Type/Gain interaction
at this specific baseline, not a general property of the field.
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]
pp = fxrack0["FX"][1]["FXEQ"]["plainParams"]

STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0)

FIELDS = [
    # (name, mutation_value, provenance, metric, expected_direction, threshold)
    ("kParamFreq2", 15000.0, "within clamp-probed [21.533,20000]; far from baseline %.2f" % pp["kParamFreq2"],
     "wholesignal_centroid", "none", 50.0),
    ("kParamReso1", 90.0, "within clamp-probed [0,100]; far from baseline %.2f" % pp["kParamReso1"],
     "wholesignal_centroid", "none", 50.0),
    ("kParamReso2", 90.0, "within clamp-probed [0,100]; far from baseline %.2f" % pp["kParamReso2"],
     "wholesignal_centroid", "none", 50.0),
    ("kParamGain1", 20.0, "within clamp-probed [-24,24]; far from baseline %.2f; avoids sparse-default 0.0" % pp["kParamGain1"],
     "wholesignal_centroid", "none", 50.0),
    ("kParamGain2", -20.0, "within clamp-probed [-24,24]; far from baseline %.2f; avoids sparse-default 0.0" % pp["kParamGain2"],
     "wholesignal_centroid", "none", 50.0),
    ("kParamLevelOut", 0.1, "within clamp-probed [0,1]; corpus sample lacked this sparse field (implicit default)",
     "overall_rms_db", "decrease", 3.0),
]

records = {}
for field, val, prov, metric, direction, threshold in FIELDS:
    path = "FXRack0.FX.1.FXEQ.plainParams.%s" % field
    spec = ExperimentSpec(
        experiment_id="FXEQ-%s" % field.upper(),
        mutations=[Mutation(path, val, prov)],
        prerequisites=[],
        baseline_overrides=[Mutation("FXRack0", fxrack0, "shared: real corpus FXRack0 (FX[1]=FXEQ)")],
        isolation_level=SINGLE_FIELD,
        claim_subject="fx_field:FXEQ.%s" % field, claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(
            metric=metric, target=TargetSpec("FXRack0.FX[FXEQ].plainParams.%s" % field, "FXEQ", field),
            expected_direction=direction, threshold=threshold, stimulus=STIM,
            kernel_artifact="%s.py" % metric)],
        notes="control: %s stays at corpus baseline. treatment: %s." % (field, val),
    )
    rec = harness.run(spec)
    m = rec.causal_measurements[0]
    so = rec.state_observation
    print("%-16s gates=%s persist=%s causal(base=%.2f treat=%.2f delta=%+.2f status=%s) diff_ok=%s" % (
        field, rec.gate_completeness(), rec.persistence_observation.get("status"),
        m.baseline, m.treatment, m.delta, m.status, so["matches_intent"]))
    records[field] = rec

pickle.dump(records, open(r"D:/ableton claude/experiments/_fxeq_numeric_records.pkl", "wb"))
