"""16.5.4: Test whether FXEQ.Freq1 causal behavior is stable across values.

Objective: find out what the evidence actually supports -- not to produce a domain.
Three outcomes are informative:
  A. All points causally pass -> multi-point causal capability; continuity still unproven.
  B. Mixed pass/fail        -> structural acceptance and causal behavior diverge.
  C. Original witness only  -> confirms POINT; parameterization even less justified.

Existing witness: 15000.0 Hz (FXEQ-FREQ1, already in _fxeq_freq1_record.pkl).
New points:
  P300  -- 300.0 Hz, below baseline 639.84, direction-reversed from witness
  P8000 -- 8000.0 Hz, between baseline and witness

Both are inside the structurally-accepted range [21.533, 20000.0].
Same corpus baseline, same kernel (wholesignal_centroid), same harness gates.
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]
assert fxrack0["FX"][1]["FXEQ"]["plainParams"]["kParamFreq1"] == 639.8384480408016

existing = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))

print("=== existing witness (15000.0 Hz) ===")
print("gates:", existing.gate_completeness())
m0 = existing.causal_measurements[0]
print("causal: base=%.2f treat=%.2f delta=%+.2f status=%s"
      % (m0.baseline, m0.treatment, m0.delta, m0.status))
print("persistence:", existing.persistence_observation.get("status"))

STIMULUS = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0)
BASELINE_OVERRIDE = Mutation(
    "FXRack0", fxrack0,
    "shared: real corpus FXRack0 (FX[1]=FXEQ, Freq1=639.84 baseline, Gain1=-3.77dB cut)")
MEAS_PLAN = lambda: MeasurementPlan(
    metric="wholesignal_centroid",
    target=TargetSpec("FXRack0.FX[FXEQ].plainParams.kParamFreq1", "FXEQ", "kParamFreq1"),
    expected_direction="none",
    threshold=50.0,
    stimulus=STIMULUS,
    kernel_artifact="wholesignal_centroid.py")

new_points = [
    ("FXEQ-FREQ1-P300", 300.0,
     "below baseline 639.84, direction-reversed from witness 15000; inside [21.533, 20000]"),
    ("FXEQ-FREQ1-P8000", 8000.0,
     "between baseline 639.84 and witness 15000; inside [21.533, 20000]"),
]

records = {}
for exp_id, val, rationale in new_points:
    print()
    print("=== %s (%.1f Hz) ===" % (exp_id, val))
    spec = ExperimentSpec(
        experiment_id=exp_id,
        mutations=[Mutation("FXRack0.FX.1.FXEQ.plainParams.kParamFreq1", val, rationale)],
        prerequisites=[],
        baseline_overrides=[BASELINE_OVERRIDE],
        isolation_level=SINGLE_FIELD,
        claim_subject="fx_field:FXEQ.kParamFreq1",
        claim_predicate="produces_measurable_effect",
        measurement_plans=[MEAS_PLAN()],
        notes="16.5.4 multi-point stability test. baseline Freq1=639.84. "
              "treatment Freq1=%.1f." % val,
    )
    rec = harness.run(spec)
    records[exp_id] = rec
    print("gates:", rec.gate_completeness())
    m = rec.causal_measurements[0]
    print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
          % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
    print("persistence:", rec.persistence_observation.get("status"),
          str(rec.persistence_observation.get("detail", ""))[:80])
    so = rec.state_observation
    print("state:", so["status"], "matches_intent=%s" % so["matches_intent"])

pickle.dump(records, open(r"D:\ableton claude\experiments\_fxeq_freq1_multipoint.pkl", "wb"))

print()
print("=== 16.5.4 classification ===")
pts = {
    "P15000": (m0.status, existing.persistence_observation.get("status")),
    "P300":   (records["FXEQ-FREQ1-P300"].causal_measurements[0].status,
               records["FXEQ-FREQ1-P300"].persistence_observation.get("status")),
    "P8000":  (records["FXEQ-FREQ1-P8000"].causal_measurements[0].status,
               records["FXEQ-FREQ1-P8000"].persistence_observation.get("status")),
}
for label, (causal, persist) in pts.items():
    print("  %s: causal=%s persistence=%s" % (label, causal, persist))

causal_pass = [label for label, (c, p) in pts.items() if c == "EFFECT_OBSERVED"]
causal_fail = [label for label, (c, p) in pts.items() if c != "EFFECT_OBSERVED"]
if len(causal_pass) == 3:
    print("OUTCOME A: all 3 points causal. Multi-point causal capability.")
elif len(causal_pass) >= 1 and causal_fail:
    print("OUTCOME B: mixed (%s pass, %s fail). Structural and causal diverge."
          % (causal_pass, causal_fail))
else:
    print("OUTCOME C: only original witness. POINT confirmed.")
