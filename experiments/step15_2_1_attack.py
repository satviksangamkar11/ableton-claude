"""15.2.1a: Env Attack, single_field, no confound (attack is the first phase
regardless of decay/sustain/release)."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

spec = ExperimentSpec(
    experiment_id="ENV-ATTACK",
    mutations=[Mutation("Env0", {"plainParams": {"kParamAttack": 0.8}}, "synthetic: long attack")],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="envelope_field:Env.kParamAttack",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="attack_onset_rms_db",
        target=TargetSpec("Env0.plainParams.kParamAttack", "Env", "kParamAttack"),
        expected_direction="decrease",   # slow attack -> lower RMS in the first 30ms
        threshold=3.0,
        stimulus=Stimulus(note=60, velocity=110, note_len=2.0, render_seconds=2.0),
        kernel_artifact="attack_onset_rms_db.py",
    )],
    notes="baseline: skeleton default attack (no key present, Serum default ~0.126s per host readback). "
          "treatment: kParamAttack=0.8s explicit.",
)
rec = harness.run(spec)
print("gates       :", rec.gate_completeness())
print("runtime ok  :", rec.runtime_verified())
m = rec.causal_measurements[0]
print("measurement_definition_id:", m.measurement_definition_id)
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence :", rec.persistence_observation["status"], rec.persistence_observation.get("detail"))
import pickle
pickle.dump(rec, open(r"D:\ableton claude\experiments\_env_attack_record.pkl", "wb"))
