"""15.2.3b: Filter Type (identity/enum -- kept separate from numeric params,
same principle as wavetable identity). Enable + a fixed cutoff held shared."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

spec = ExperimentSpec(
    experiment_id="FILTER-TYPE",
    mutations=[Mutation("VoiceFilter0.plainParams.kParamType", "BP12", "synthetic: bandpass type, confirmed real enum value from corpus")],
    prerequisites=[],
    baseline_overrides=[
        Mutation("VoiceFilter0.plainParams.kParamEnable", 1.0, "shared: filter must be enabled"),
        Mutation("VoiceFilter0.plainParams.kParamFreq", 0.35, "shared: fixed cutoff"),
    ],
    isolation_level=SINGLE_FIELD,
    claim_subject="filter_field:VoiceFilter.kParamType",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="wholesignal_centroid",
        target=TargetSpec("VoiceFilter0.plainParams.kParamType", "VoiceFilter", "kParamType"),
        expected_direction="none",   # type change direction not physically predictable a priori -- just require a real effect
        threshold=50.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="wholesignal_centroid.py",
    )],
    notes="both arms: Enable=1.0, Freq=0.35. control: implicit default Type. treatment: Type=BP12 (bandpass).",
)
rec = harness.run(spec)
print("gates       :", rec.gate_completeness())
m = rec.causal_measurements[0]
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence :", rec.persistence_observation["status"], rec.persistence_observation.get("detail"))
import pickle
pickle.dump(rec, open(r"D:\ableton claude\experiments\_filter_type_record.pkl", "wb"))
