"""15.2.4: Env Sustain. baseline_overrides holds Decay=0.02 (short) IDENTICAL
in both arms, so by t=0.9s decay has fully settled and sustain level dominates."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

spec = ExperimentSpec(
    experiment_id="ENV-SUSTAIN",
    mutations=[Mutation("Env0.plainParams.kParamSustain", 0.3, "synthetic: partial sustain, clearly off Serum default (1.0)")],
    prerequisites=[],
    baseline_overrides=[Mutation("Env0.plainParams.kParamDecay", 0.02,
                                 "shared: short decay so we're in sustain phase by 0.9s")],
    notes="control: implicit default Sustain=1.0 (confirmed via host readback). "
          "treatment: Sustain=0.3, clearly off default.",
    isolation_level=SINGLE_FIELD,
    claim_subject="envelope_field:Env.kParamSustain",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="sustain_window_rms_db",
        target=TargetSpec("Env0.plainParams.kParamSustain", "Env", "kParamSustain"),
        expected_direction="decrease",   # implicit default sustain=1.0 -> treatment 0.3 is a decrease
        threshold=3.0,
        stimulus=Stimulus(note=60, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="sustain_window_rms_db.py",
    )],
)
rec = harness.run(spec)
print("gates       :", rec.gate_completeness())
m = rec.causal_measurements[0]
print("measurement_definition_id:", m.measurement_definition_id)
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence :", rec.persistence_observation["status"], rec.persistence_observation.get("detail"))
import pickle
pickle.dump(rec, open(r"D:\ableton claude\experiments\_env_sustain_record.pkl", "wb"))
