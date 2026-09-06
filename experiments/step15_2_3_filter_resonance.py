"""15.2.3a: Filter Resonance. Enable + a mid cutoff held identical in both
arms (so the resonant peak has something to act on); mutation is Resonance
alone."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

spec = ExperimentSpec(
    experiment_id="FILTER-RESONANCE",
    mutations=[Mutation("VoiceFilter0.plainParams.kParamReso", 90.0, "synthetic: high resonance")],
    prerequisites=[],
    baseline_overrides=[
        Mutation("VoiceFilter0.plainParams.kParamEnable", 1.0, "shared: filter must be enabled"),
        Mutation("VoiceFilter0.plainParams.kParamFreq", 0.35, "shared: mid-low cutoff so a resonant peak is audible"),
    ],
    isolation_level=SINGLE_FIELD,
    claim_subject="filter_field:VoiceFilter.kParamReso",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="overall_rms_db",
        target=TargetSpec("VoiceFilter0.plainParams.kParamReso", "VoiceFilter", "kParamReso"),
        expected_direction="increase",   # higher resonance -> peak gain -> more overall energy
        threshold=1.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="overall_rms_db.py",
    )],
    notes="both arms: Enable=1.0, Freq=0.35 (normalized). control: implicit default Reso. treatment: Reso=90.0.",
)
rec = harness.run(spec)
print("gates       :", rec.gate_completeness())
m = rec.causal_measurements[0]
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence :", rec.persistence_observation["status"], rec.persistence_observation.get("detail"))
import pickle
pickle.dump(rec, open(r"D:\ableton claude\experiments\_filter_reso_record.pkl", "wb"))
