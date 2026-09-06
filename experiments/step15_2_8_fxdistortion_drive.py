"""15.2.8.2: FXDistortion Drive. Real, unchanged FXRack0 (Aardvark) as shared
context via baseline_override; mutation reaches the specific leaf via the new
list-index path support. Range [0,100] confirmed via direct clamp probe."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2 import codec
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

AARD = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
_, aard_body = codec.load_preset_file(AARD)
fxrack0 = aard_body["FXRack0"]

spec = ExperimentSpec(
    experiment_id="FXDIST-DRIVE",
    mutations=[Mutation("FXRack0.FX.2.FXDistortion.plainParams.kParamDrive", 100.0,
                        "confirmed max via direct clamp probe (100->100, 150->100)")],
    prerequisites=[],
    baseline_overrides=[Mutation("FXRack0", fxrack0,
                                 "shared: Aardvark's real unchanged FXRack0 (Drive=36.75 baseline)")],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field:FXDistortion.kParamDrive", claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="wholesignal_centroid",
        target=TargetSpec("FXRack0.FX[FXDistortion].plainParams.kParamDrive", "FXDistortion", "kParamDrive"),
        expected_direction="increase",  # distortion adds harmonics -> brighter spectrum
        threshold=50.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="wholesignal_centroid.py")],
    notes="both arms share Aardvark's real, unmodified FXRack0. control: Drive stays at "
          "Aardvark's real 36.75. treatment: Drive=100.0 (confirmed max). List-index path "
          "means only the Drive leaf differs -- Wet/Mode/LevelOut/other FX units identical.",
)

rec = harness.run(spec)
print("gates:", rec.gate_completeness())
print("runtime verified:", rec.runtime_verified())
m = rec.causal_measurements[0]
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence:", rec.persistence_observation.get("status"), rec.persistence_observation.get("detail"))
print("state diff:", {k: rec.state_observation[k] for k in ("status","matches_intent","top_level_ok","fine_grained_ok")})

import pickle
pickle.dump(rec, open(r"D:/ableton claude/experiments/_fxdist_drive_record.pkl", "wb"))
