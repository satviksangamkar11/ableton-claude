"""15.2.5: Env Release. baseline_overrides holds Sustain=1.0 (clearly off the
implicit default only insofar as we need SOME held level to release from --
using explicit 1.0, matching Serum's own true default, is fine here since it's
shared identically in both arms, not the tested variable). Short note, measure
the tail after note-off. Reuses the already-proven tail_rms_db kernel."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

spec = ExperimentSpec(
    experiment_id="ENV-RELEASE",
    mutations=[Mutation("Env0.plainParams.kParamRelease", 1.0, "synthetic: long release")],
    prerequisites=[],
    baseline_overrides=[Mutation("Env0.plainParams.kParamDecay", 0.02,
                                 "shared: short decay so we're fully settled before note-off")],
    isolation_level=SINGLE_FIELD,
    claim_subject="envelope_field:Env.kParamRelease",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="tail_rms_db",
        target=TargetSpec("Env0.plainParams.kParamRelease", "Env", "kParamRelease"),
        expected_direction="increase",   # longer release -> more energy in the tail after note-off
        threshold=3.0,
        stimulus=Stimulus(note=60, velocity=110, note_len=0.4, render_seconds=2.0, tail_start=0.6),
        kernel_artifact="tail_rms_db.py",
    )],
    notes="both arms: Decay=0.02s. control: implicit default Release. treatment: Release=1.0s. "
          "note_len=0.4s so note-off happens well before the tail_start=0.6s measurement window.",
)
rec = harness.run(spec)
print("gates       :", rec.gate_completeness())
m = rec.causal_measurements[0]
print("measurement_definition_id:", m.measurement_definition_id)
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence :", rec.persistence_observation["status"], rec.persistence_observation.get("detail"))
import pickle
pickle.dump(rec, open(r"D:\ableton claude\experiments\_env_release_record.pkl", "wb"))
