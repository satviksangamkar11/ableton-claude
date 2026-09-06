"""15.2.8.5: FXEQ Freq1 -- first field of the next-highest-prevalence FX family
(FXEQ: 810 corpus occurrences, the most prevalent untested family). Real
corpus baseline (body_idx=4 in _corpus_cache.pkl, FX[1]=FXEQ, Freq1=639.84Hz,
Gain1=-3.77dB cut). Range clamp-probed: [21.533, 20000.0] Hz -- neither bound
assumed. Magnitude-only causal claim: Freq1's effect on this kernel's
direction depends on the sign/magnitude of Gain1 at this specific baseline,
not a general property of "raising a band frequency" -- no directional
hypothesis is justified without testing across multiple Gain1 signs, which is
out of scope for a single-field isolation experiment."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]
assert fxrack0["FX"][1]["FXEQ"]["plainParams"]["kParamFreq1"] == 639.8384480408016

spec = ExperimentSpec(
    experiment_id="FXEQ-FREQ1",
    mutations=[Mutation("FXRack0.FX.1.FXEQ.plainParams.kParamFreq1", 15000.0,
                        "within clamp-probed range [21.533, 20000.0]; far from baseline 639.84")],
    prerequisites=[],
    baseline_overrides=[Mutation("FXRack0", fxrack0,
                                 "shared: real corpus FXRack0 (FX[1]=FXEQ, Freq1=639.84 baseline, "
                                 "Gain1=-3.77dB cut)")],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field:FXEQ.kParamFreq1", claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="wholesignal_centroid",
        target=TargetSpec("FXRack0.FX[FXEQ].plainParams.kParamFreq1", "FXEQ", "kParamFreq1"),
        expected_direction="none",  # magnitude-only, see module docstring
        threshold=50.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="wholesignal_centroid.py")],
    notes="both arms share the real corpus FXRack0. control: Freq1 stays at 639.84. "
          "treatment: Freq1=15000.0.",
)

rec = harness.run(spec)
print("gates:", rec.gate_completeness())
print("runtime verified:", rec.runtime_verified())
m = rec.causal_measurements[0]
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence:", rec.persistence_observation.get("status"), rec.persistence_observation.get("detail"))
so = rec.state_observation
print("state diff:", {k: so[k] for k in ("status","matches_intent","top_level_ok","fine_grained_ok")})
print("diff_keys:", so["diff_keys"], "intended:", so["intended_targets"])

pickle.dump(rec, open(r"D:/ableton claude/experiments/_fxeq_freq1_record.pkl", "wb"))
