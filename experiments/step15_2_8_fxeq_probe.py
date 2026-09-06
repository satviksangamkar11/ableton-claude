"""15.2.8.5 prep: FXEQ Freq1 clamp probe. Real corpus baseline (body_idx=4,
fx_index=1, Freq1=639.84). Probe several out-of-typical-range values through
the harness's own persistence check (Serum's own re-save) to find the real
range empirically -- do not assume 20-20000Hz."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import ExperimentSpec, Mutation, SINGLE_FIELD

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]

for probe_val in (100.0, 20000.0, 50000.0, 100000.0):
    spec = ExperimentSpec(
        experiment_id="FXEQ-FREQ1-PROBE-%s" % probe_val,
        mutations=[Mutation("FXRack0.FX.1.FXEQ.plainParams.kParamFreq1", probe_val, "clamp probe")],
        prerequisites=[], isolation_level=SINGLE_FIELD,
        claim_subject="s", claim_predicate="p",
        baseline_overrides=[Mutation("FXRack0", fxrack0, "shared corpus FXRack0 context")],
        measurement_plans=[],
    )
    rec = harness.run(spec)
    print("probe=%s -> persistence=%s detail=%s" % (
        probe_val, rec.persistence_observation.get("status"), rec.persistence_observation.get("detail")))
