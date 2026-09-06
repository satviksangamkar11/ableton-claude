"""15.2.2: Oscillator -- Enable, Octave, Volume (numeric), Wavetable identity (asset).
Asset identity kept as its own distinct capability, not merged with numeric params."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

records = {}

def run(exp_id, target_path, value, provenance, metric, target, direction,
       threshold, kernel_artifact, subject, note_len=1.8):
    spec = ExperimentSpec(
        experiment_id=exp_id,
        mutations=[Mutation(target_path, value, provenance)],
        prerequisites=[], isolation_level=SINGLE_FIELD,
        claim_subject=subject, claim_predicate="produces_measurable_effect",
        measurement_plans=[MeasurementPlan(
            metric=metric, target=TargetSpec(target_path),
            expected_direction=direction, threshold=threshold,
            stimulus=Stimulus(note=60, velocity=110, note_len=note_len, render_seconds=2.0),
            kernel_artifact=kernel_artifact,
        )],
        notes="control: skeleton default. treatment: %s" % provenance,
    )
    rec = harness.run(spec)
    m = rec.causal_measurements[0]
    print("%-20s gates=%-50s base=%9.2f treat=%9.2f delta=%+9.2f dir=%-8s status=%-16s persist=%s"
          % (exp_id, rec.gate_completeness(), m.baseline, m.treatment, m.delta,
             m.observed_direction, m.status, rec.persistence_observation["status"]))
    records[exp_id] = rec
    return rec

print("=== Enable ===")
run("OSC-ENABLE", "Oscillator0.plainParams.kParamEnable", 0.0, "synthetic: disable oscillator A",
    "overall_rms_db", "Oscillator0.plainParams.kParamEnable", "decrease", 6.0,
    "overall_rms_db.py", "oscillator_field:Oscillator.kParamEnable")

print("=== Octave ===")
run("OSC-OCTAVE", "Oscillator0.plainParams.kParamOctave", 2.0, "synthetic: +2 octaves",
    "wholesignal_centroid", "Oscillator0.plainParams.kParamOctave", "increase", 100.0,
    "wholesignal_centroid.py", "oscillator_field:Oscillator.kParamOctave")

print("=== Volume ===")
run("OSC-VOLUME", "Oscillator0.plainParams.kParamVolume", 0.05, "synthetic: near-silent volume",
    "overall_rms_db", "Oscillator0.plainParams.kParamVolume", "decrease", 6.0,
    "overall_rms_db.py", "oscillator_field:Oscillator.kParamVolume")

print("=== Wavetable identity (asset, separate capability) ===")
run("OSC-WAVETABLE", "Oscillator0.WTOsc0",
    {"flex": {}, "numChannels": 1, "numFrames": 251904,
     "plainParams": {"kParamTablePos": 129.72312396764755},
     "relativePathToWT": "S2 Tables/Analog/Square Drift 303.wav", "sampleRate": 44100},
    "Aardvark's real WTOsc0 (Square Drift 303 vs default Basic Shapes)",
    "wholesignal_centroid", "Oscillator0.WTOsc0.relativePathToWT", "none", 50.0,
    "wholesignal_centroid.py", "oscillator_field:Oscillator.wavetable_identity")

pickle.dump(records, open(r"D:\ableton claude\experiments\_osc_records.pkl", "wb"))
