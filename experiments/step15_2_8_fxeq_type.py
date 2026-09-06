"""15.2.8.7: FXEQ Type1/Type2. Real corpus enum values only -- Type1 observed
as {1.0: 241, 2.0: 301}, Type2 as {1.0: 346, 2.0: 70} across 810 corpus FXEQ
instances; no other values ever observed, so we test the switch between the
two real values without inventing a third. Baseline (body_idx=4) has both at
1.0 -- treatment flips each to 2.0 independently. Magnitude-only: a filter-
band type switch (e.g. bell vs shelf) has no single principled direction."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]
pp = fxrack0["FX"][1]["FXEQ"]["plainParams"]
assert pp["kParamType1"] == 1.0 and pp["kParamType2"] == 1.0

STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0)
records = {}
for field in ("kParamType1", "kParamType2"):
    path = "FXRack0.FX.1.FXEQ.plainParams.%s" % field
    spec = ExperimentSpec(
        experiment_id="FXEQ-%s" % field.upper(),
        mutations=[Mutation(path, 2.0, "real corpus value (2.0), contrasts with baseline's real 1.0")],
        prerequisites=[],
        baseline_overrides=[Mutation("FXRack0", fxrack0, "shared: real corpus FXRack0 (FX[1]=FXEQ)")],
        isolation_level=SINGLE_FIELD,
        claim_subject="fx_field:FXEQ.%s" % field, claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(
            metric="wholesignal_centroid", target=TargetSpec("FXRack0.FX[FXEQ].plainParams.%s" % field, "FXEQ", field),
            expected_direction="none", threshold=50.0, stimulus=STIM,
            kernel_artifact="wholesignal_centroid.py")],
        notes="control: %s stays 1.0 (real baseline). treatment: 2.0 (real corpus value)." % field,
    )
    rec = harness.run(spec)
    m = rec.causal_measurements[0]
    so = rec.state_observation
    print("%-16s gates=%s persist=%s causal(base=%.2f treat=%.2f delta=%+.2f status=%s) diff_ok=%s" % (
        field, rec.gate_completeness(), rec.persistence_observation.get("status"),
        m.baseline, m.treatment, m.delta, m.status, so["matches_intent"]))
    records[field] = rec

pickle.dump(records, open(r"D:/ableton claude/experiments/_fxeq_type_records.pkl", "wb"))
