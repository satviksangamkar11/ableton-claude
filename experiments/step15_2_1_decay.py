"""15.2.3: Env Decay. baseline_overrides holds Sustain=0.0 IDENTICAL in both
arms; mutation changes only Decay. Path-merge means both target the SAME
Env0.plainParams dict without collision -- the control/treatment diff is
structurally provable to be exactly kParamDecay."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

spec = ExperimentSpec(
    experiment_id="ENV-DECAY",
    mutations=[Mutation("Env0.plainParams.kParamDecay", 1.5, "synthetic: long decay")],
    prerequisites=[],
    baseline_overrides=[Mutation("Env0.plainParams.kParamSustain", 0.0,
                                 "shared: sustain=0 so decay time is observable")],
    isolation_level=SINGLE_FIELD,
    claim_subject="envelope_field:Env.kParamDecay",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="decay_window_rms_db",
        target=TargetSpec("Env0.plainParams.kParamDecay", "Env", "kParamDecay"),
        expected_direction="increase",   # longer decay -> more energy remaining mid-note
        threshold=3.0,
        stimulus=Stimulus(note=60, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="decay_window_rms_db.py",
    )],
    notes="both arms: Sustain=0.0. control: implicit default Decay. treatment: Decay=1.5s.",
)
rec = harness.run(spec)
print("gates       :", rec.gate_completeness())
print("state diff  : control=%s treatment=%s matches_intent=%s" % (
    rec.state_observation["control_hash"], rec.state_observation["treatment_hash"],
    rec.state_observation["matches_intent"]))
m = rec.causal_measurements[0]
print("measurement_definition_id:", m.measurement_definition_id)
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence :", rec.persistence_observation["status"], rec.persistence_observation.get("detail"))
import pickle
pickle.dump(rec, open(r"D:\ableton claude\experiments\_env_decay_record.pkl", "wb"))
