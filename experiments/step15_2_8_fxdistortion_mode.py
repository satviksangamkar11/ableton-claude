"""15.2.8.3: FXDistortion Mode. Independent ClaimGroup from Drive. Real corpus
enum values only (kOverdrive=Aardvark's own value, 38 corpus occurrences;
kHardClip=16 occurrences, a genuinely different waveshaping family). Magnitude-
only observable: mode identity has no principled increase/decrease direction,
only whether switching it produces a measurable spectral change."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2 import codec
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

AARD = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
_, aard_body = codec.load_preset_file(AARD)
fxrack0 = aard_body["FXRack0"]
assert fxrack0["FX"][2]["FXDistortion"]["plainParams"]["kParamMode"] == "kOverdrive", \
    "baseline assumption violated -- Aardvark's real Mode value changed or was misread"

spec = ExperimentSpec(
    experiment_id="FXDIST-MODE",
    mutations=[Mutation("FXRack0.FX.2.FXDistortion.plainParams.kParamMode", "kHardClip",
                        "real corpus value (16 occurrences), contrasts with Aardvark's "
                        "own real baseline kOverdrive (38 occurrences)")],
    prerequisites=[],
    baseline_overrides=[Mutation("FXRack0", fxrack0,
                                 "shared: Aardvark's real unchanged FXRack0 (Mode=kOverdrive baseline)")],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field:FXDistortion.kParamMode", claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="wholesignal_centroid",
        target=TargetSpec("FXRack0.FX[FXDistortion].plainParams.kParamMode", "FXDistortion", "kParamMode"),
        expected_direction="none",  # magnitude-only: no principled direction for a mode switch
        threshold=50.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="wholesignal_centroid.py")],
    notes="both arms share Aardvark's real, unmodified FXRack0 (Drive=36.75, Mode=kOverdrive). "
          "control: Mode stays kOverdrive. treatment: Mode=kHardClip. Magnitude-only causal claim "
          "-- kept separate from Drive's directional claim per instruction to keep the two "
          "capabilities independent.",
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

import pickle
pickle.dump(rec, open(r"D:/ableton claude/experiments/_fxdist_mode_record.pkl", "wb"))
