"""15.2.6: Macro capability discovery.

Three claim angles, kept separate per project convention (identity/asset-like
fields are never merged with numeric-effect claims):

  1. MACRO-VALUE  -- Macro{N}.plainParams.kParamValue, numeric, causal + persistence.
                     Reuses the ALREADY-CONFIRMED source=[32,0] -> Macro7 (host
                     "Macro 8") mapping from g8c_macro_isolation.py, but drives
                     the value at the BODY level (Macro7.plainParams.kParamValue)
                     rather than through the host "Macro 8" parameter, so the
                     capability under test is the body-level macro value field
                     itself. A fresh route is built in the (empty, skeleton-
                     default) ModSlot30: destination fields (destModuleID/
                     destModuleParamID/destModuleParamName/destModuleTypeString)
                     copied from Aardvark's real ModSlot0 (VoiceFilter/kParamFreq,
                     a destination already proven extremely sensitive/clean in
                     g8a_test1_slot30.py); source=[32,0] copied from Aardvark's
                     real ModSlot1 (the confirmed Macro7 source id); kParamAmount
                     is a synthetic-but-plausible 50.0 (real corpus ModSlot0
                     amount was 29.68). This merged route is a baseline_override
                     (identical in both arms) -- the tested mutation is ONLY
                     Macro7.plainParams.kParamValue (0/implicit vs 100.0, the
                     real 0-100 native range seen in Aardvark's Macro3=100.0).
                     claim_subject is phrased "macro_field:Macro.kParamValue" so
                     family attribution resolves to Macro (not FXDelay/ModSlot),
                     and this experiment, if PERSISTENT, also independently
                     satisfies claim angle 3 (macro source-behavior end-to-end
                     confirmation) for the Macro family specifically.

  2. MACRO-NAME   -- Macro{N}.name, identity/label. construct/mutate/load/
                     persist only, NO measurement_plans (a name has no direct
                     audio effect) -- expected to land PERSISTENT_STRUCTURAL
                     (causal: NOT_RUN), exactly like LFO-SHAPE/LFO-MODE. Uses a
                     DIFFERENT macro (Macro6) than MACRO-VALUE (Macro7) to keep
                     the two experiments' body keys disjoint. Treatment value is
                     'REVERB SIZE', Aardvark's real Macro6 name.

A pre-check (see probe_macro_value.py investigation) confirmed the physics
before locking expected_direction: skeleton-default (no macro value) control
centroid = 349.14 Hz; Macro7.kParamValue=100.0 treatment centroid = 3740.77 Hz;
delta +3391.63 Hz -- large, monotonic, in the "increase" direction (higher
macro value -> higher kParamAmount contribution -> higher VoiceFilter cutoff ->
higher spectral centroid), consistent with the destination's already-proven
sensitivity. threshold=100.0 Hz leaves large margin below the observed effect.
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

records = {}

# Real destination fields from Aardvark ModSlot0 (VoiceFilter/kParamFreq);
# real source id [32,0] from Aardvark ModSlot1 (confirmed Macro7 mapping,
# g8c_macro_isolation.py); kParamAmount synthetic within the real observed range.
MACRO_ROUTE = {
    "destModuleID": 0,
    "destModuleParamID": 3,
    "destModuleParamName": "kParamFreq",
    "destModuleTypeString": "VoiceFilter",
    "plainParams": {"kParamAmount": 50.0},
    "source": [32, 0],
}

print("=== MACRO-VALUE ===")
spec_value = ExperimentSpec(
    experiment_id="MACRO-VALUE",
    mutations=[Mutation("Macro7.plainParams.kParamValue", 100.0,
                        "synthetic: high macro value; real corpus range 0-100 "
                        "(Aardvark Macro3 'NOISE' = 100.0)")],
    prerequisites=[Prerequisite("host:Filter 1 On", 1.0)],
    baseline_overrides=[
        Mutation("ModSlot30", MACRO_ROUTE,
                 "corpus-merged: destination from Aardvark ModSlot0 (real "
                 "VoiceFilter/kParamFreq route), source=[32,0] from Aardvark "
                 "ModSlot1 (confirmed causal Macro7 source id), kParamAmount "
                 "synthetic 50.0 (real ModSlot0 amount was 29.68)"),
    ],
    isolation_level=SINGLE_FIELD,
    claim_subject="macro_field:Macro.kParamValue",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="wholesignal_centroid",
        target=TargetSpec("Macro7.plainParams.kParamValue", "Macro", "kParamValue"),
        expected_direction="increase",
        threshold=100.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="wholesignal_centroid.py",
    )],
    notes="both arms: ModSlot30 = VoiceFilter/kParamFreq route, source=[32,0], "
          "amount=50.0 (baseline_override, identical). Filter 1 On=1.0 (host "
          "prerequisite, identical). control: Macro7 untouched (skeleton "
          "default, {'plainParams': 'default'}). treatment: "
          "Macro7.plainParams.kParamValue=100.0. Pre-checked physics: "
          "control centroid=349.14Hz, treatment=3740.77Hz, delta=+3391.63Hz.",
)
rec_value = harness.run(spec_value)
print("gates       :", rec_value.gate_completeness())
mv = rec_value.causal_measurements[0]
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (mv.baseline, mv.treatment, mv.delta, mv.observed_direction, mv.status))
print("runtime_verified:", rec_value.runtime_verified())
print("persistence :", rec_value.persistence_observation["status"], rec_value.persistence_observation.get("detail"))
records["MACRO-VALUE"] = rec_value

print()
print("=== MACRO-NAME ===")
spec_name = ExperimentSpec(
    experiment_id="MACRO-NAME",
    mutations=[Mutation("Macro6.name", "REVERB SIZE",
                        "corpus: Aardvark's real Macro6 name")],
    prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
    claim_subject="macro_field:Macro.name", claim_predicate="constructs_mutates_persists",
    measurement_plans=[],
    notes="no causal claim -- a macro NAME is a label, not something with a "
          "direct audio effect (same principle as LFO-SHAPE/OSC-WAVETABLE). "
          "Uses Macro6 (distinct from MACRO-VALUE's Macro7) so the two "
          "experiments' body keys are fully disjoint. control: implicit "
          "default (skeleton Macro6 has no 'name' key at all). treatment: "
          "name='REVERB SIZE'.",
)
rec_name = harness.run(spec_name)
print("gates       :", rec_name.gate_completeness())
print("persistence detail:", rec_name.persistence_observation.get("detail"))
records["MACRO-NAME"] = rec_name

pickle.dump(records, open(r"D:\ableton claude\experiments\_macro_records.pkl", "wb"))
print()
print("saved:", list(records.keys()))
