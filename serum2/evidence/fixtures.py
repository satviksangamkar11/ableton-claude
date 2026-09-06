"""Historical fixtures: the five real experiments, as immutable records.

Observations are transcribed from what each run ACTUALLY captured. Where a run
never captured a field, it is NOT_RECORDED / NOT_RUN. Nothing is back-filled.
"""
from .canonical import (digest, experiment_condition_signature,
                        measurement_condition_signature)
from .record import (
    EvidenceRecord, EvidenceArm, CausalMeasurement, MeasurementTarget,
    PASS, FAIL, NOT_RUN, INCONCLUSIVE,
    EFFECT_OBSERVED, NO_OBSERVED_EFFECT, NOT_RECORDED,
)
from .measurement import define, MeasurementTargetRef

# Archived kernels, one per historical measurement implementation.
TARGET_VF = MeasurementTargetRef("VoiceFilter0.plainParams.kParamFreq",
                                 "VoiceFilter", "kParamFreq")
TARGET_FX = MeasurementTargetRef("FXRack0.FX[FXDelay].plainParams.kParamWet",
                                 "FXDelay", "kParamWet")

MD_WINDOWED_CENTROID = define("spectral_centroid_hz",
                              "windowed_mean_centroid.py", TARGET_VF)
MD_WHOLESIGNAL_CENTROID = define("spectral_centroid_hz",
                                 "wholesignal_centroid.py", TARGET_VF)
MD_TAIL_RMS = define("tail_rms_db", "tail_rms_db.py", TARGET_FX)

SERUM_BINARY_SHA = "7978c9be5b2107e985c24c174000faee87e11483ec989d81dc61b5829b45ed70"

# Historical runs predate epoch capture; the binary was unchanged throughout.
HISTORICAL_EPOCH = {
    "evidence_epoch_id": "historical-pre-harness",
    "serum_binary_sha256": SERUM_BINARY_SHA,
    "harness_revision": NOT_RECORDED,
    "dependency_lock": {"dawdreamer": "0.9.0", "python": "3.14.3"},
    "environment_fingerprint": {"sample_rate": 44100, "block_size": 512,
                                "platform": "Windows-11-10.0.26200-SP0"},
}

ROUTE_FILTER = {
    "destModuleID": 0, "destModuleParamID": 3,
    "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
    "plainParams": {"kParamAmount": 29.682552814483643}, "source": [6, 0],
}
ROUTE_DELAY = {
    "destModuleID": 1, "destModuleParamID": 1,
    "destModuleParamName": "kParamWet", "destModuleTypeString": "FXDelay",
    "plainParams": {"kParamAmount": -22.16377854347229}, "source": [32, 0],
}

STIM_SUSTAIN = {"note": 48, "velocity": 110, "note_len": 1.8,
                "render_seconds": 2.0, "tail_start": None}
STIM_PLUCK = {"note": 60, "velocity": 100, "note_len": 0.15,
              "render_seconds": 2.0, "tail_start": 0.6}


class _P:
    """Minimal prerequisite shape accepted by canonical.condition_signature."""
    def __init__(self, field_path, declared_value, must_hold_identical=True):
        self.field_path = field_path
        self.declared_value = declared_value
        self.must_hold_identical = must_hold_identical


def _experiment(mutations, prerequisites, isolation_level, subject, predicate,
                stimuli, notes=""):
    """stimuli: list of per-measurement stimulus dicts (may be empty)."""
    exp_sig = experiment_condition_signature(prerequisites)
    meas_sigs = [measurement_condition_signature(exp_sig, st) for st in stimuli]
    return {
        "mutations": [{"target_path": t, "value": v, "provenance": p}
                      for (t, v, p) in mutations],
        "prerequisites": [{"field_path": p.field_path,
                           "declared_value": p.declared_value,
                           "must_hold_identical": p.must_hold_identical}
                          for p in prerequisites],
        "isolation_level": isolation_level,
        "claim_subject": subject,
        "claim_predicate": predicate,
        "experiment_condition_signature": exp_sig,
        "measurement_condition_signatures": meas_sigs,
        "mutation_signature": digest(sorted([t, v] for (t, v, _) in mutations)),
        "notes": notes,
    }


def _arms(declared_context, control_state=None, treatment_state=None,
          load=PASS, render=PASS):
    return (
        EvidenceArm("arm_control", "control", declared_context, None,
                    control_state, load, render, {}),
        EvidenceArm("arm_treatment", "treatment", declared_context, None,
                    treatment_state, load, render, {}),
    )


# --------------------------------------------------------------------------
# E0 -- Aardvark ModSlot0 route written into ModSlot0. Causal run (g7a).
# g7a recorded the causal measurement only: no state hashes, no persistence.
# --------------------------------------------------------------------------
def e0():
    pre = [_P("host:Filter 1 On", 1.0)]
    exp = _experiment([("ModSlot0", ROUTE_FILTER, "Aardvark ModSlot0")],
                      pre, "single_field",
                      "modulation_route:VoiceFilter.kParamFreq", "produces_measurable_effect",
                      [STIM_SUSTAIN], "g7a_causality.py")
    return EvidenceRecord(
        experiment_id="E0",
        epoch=HISTORICAL_EPOCH,
        experiment=exp,
        arms=_arms({"host:Filter 1 On": 1.0}),
        runtime_verifications=(),                       # runtime.py did not exist
        state_observation={"status": NOT_RUN, "detail": NOT_RECORDED,
                           "note": "g7a did not capture state diff/hashes"},
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=(CausalMeasurement(
            metric="spectral_centroid_hz",
            target=MeasurementTarget("VoiceFilter0.plainParams.kParamFreq",
                                     "VoiceFilter", "kParamFreq"),
            baseline=348.66527315050166, treatment=946.0409311097084,
            delta=597.3756579592067, expected_direction="increase",
            observed_direction="increase", threshold=100.0,
            status=EFFECT_OBSERVED,
            measurement_condition_signature=exp["measurement_condition_signatures"][0],
            measurement_definition_id=MD_WINDOWED_CENTROID.measurement_definition_id),),
        persistence_observation={"status": NOT_RUN,
                                 "note": "persistence run separately (g7b), different conditions"},
    )


# --------------------------------------------------------------------------
# E1 -- same route, empty ModSlot30. g8a captured every gate.
# --------------------------------------------------------------------------
def e1():
    pre = [_P("host:Filter 1 On", 1.0)]
    exp = _experiment([("ModSlot30", ROUTE_FILTER, "Aardvark ModSlot0")],
                      pre, "single_field",
                      "modulation_route:VoiceFilter.kParamFreq", "produces_measurable_effect",
                      [STIM_SUSTAIN], "g8a_test1_slot30.py")
    return EvidenceRecord(
        experiment_id="E1",
        epoch=HISTORICAL_EPOCH,
        experiment=exp,
        arms=_arms({"host:Filter 1 On": 1.0}),
        runtime_verifications=(),
        state_observation={
            "status": PASS,
            "target_was_empty": True,
            "contains_intended_route": True,
            "control_hash": "fe45bdd8c3518d45",
            "treatment_hash": "4e1fdfcf123b8501",
            "hashes_differ": True,
        },
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=(CausalMeasurement(
            metric="spectral_centroid_hz",
            target=MeasurementTarget("VoiceFilter0.plainParams.kParamFreq",
                                     "VoiceFilter", "kParamFreq"),
            baseline=348.7, treatment=946.0, delta=597.3,
            expected_direction="increase", observed_direction="increase",
            threshold=100.0, status=EFFECT_OBSERVED,
            measurement_condition_signature=exp["measurement_condition_signatures"][0],
            measurement_definition_id=MD_WINDOWED_CENTROID.measurement_definition_id),),
        persistence_observation={"status": PASS, "exact_match": True,
                                 "detail": {"ModSlot30": True}},
    )


# --------------------------------------------------------------------------
# E2a -- FXDelay route, Macro7 INACTIVE. Null causal result (g8b).
# g8b DID run persistence and it passed.
# --------------------------------------------------------------------------
def e2a():
    pre = [_P("body:FXRack0", "<Aardvark FXRack0>"), _P("host:Macro 8", 0.0)]
    exp = _experiment([("ModSlot30", ROUTE_DELAY, "Aardvark ModSlot1")],
                      pre, "single_field",
                      "modulation_route:FXDelay.kParamWet", "produces_measurable_effect",
                      [STIM_PLUCK], "g8b_test2_fxdelay.py (Macro7 inactive)")
    return EvidenceRecord(
        experiment_id="E2a",
        epoch=HISTORICAL_EPOCH,
        experiment=exp,
        arms=_arms({"body:FXRack0": "<Aardvark FXRack0>", "host:Macro 8": 0.0}),
        runtime_verifications=(),
        state_observation={"status": PASS, "contains_intended_route": True,
                           "differs_from_baseline": True},
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=(CausalMeasurement(
            metric="tail_rms_db",
            target=MeasurementTarget("FXRack0.FX[FXDelay].plainParams.kParamWet",
                                     "FXDelay", "kParamWet"),
            baseline=-65.54435646162642, treatment=-65.54435646162642,
            delta=0.0, expected_direction="decrease",
            observed_direction="none", threshold=3.0,
            status=NO_OBSERVED_EFFECT,
            measurement_condition_signature=exp["measurement_condition_signatures"][0],
            measurement_definition_id=MD_TAIL_RMS.measurement_definition_id),),
        persistence_observation={"status": PASS, "exact_match": True,
                                 "detail": {"ModSlot30": True}},
    )


# --------------------------------------------------------------------------
# E2b -- same route, Macro7 ACTIVE. Causal pass (g8d).
# --------------------------------------------------------------------------
def e2b():
    pre = [_P("body:FXRack0", "<Aardvark FXRack0>"), _P("host:Macro 8", 1.0)]
    exp = _experiment([("ModSlot30", ROUTE_DELAY, "Aardvark ModSlot1")],
                      pre, "single_field",
                      "modulation_route:FXDelay.kParamWet", "produces_measurable_effect",
                      [STIM_PLUCK], "g8d_test2_full_gate.py (Macro7 active)")
    return EvidenceRecord(
        experiment_id="E2b",
        epoch=HISTORICAL_EPOCH,
        experiment=exp,
        arms=_arms({"body:FXRack0": "<Aardvark FXRack0>", "host:Macro 8": 1.0}),
        runtime_verifications=(),
        state_observation={"status": PASS, "contains_intended_route": True,
                           "diff_keys": ["ModSlot30"],
                           "control_hash": "fe45bdd8c3518d45",
                           "treatment_hash": "fb9c676ec4146c61",
                           "hashes_differ": True},
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=(CausalMeasurement(
            metric="tail_rms_db",
            target=MeasurementTarget("FXRack0.FX[FXDelay].plainParams.kParamWet",
                                     "FXDelay", "kParamWet"),
            baseline=-65.54, treatment=-101.62, delta=-36.08,
            expected_direction="decrease", observed_direction="decrease",
            threshold=3.0, status=EFFECT_OBSERVED,
            measurement_condition_signature=exp["measurement_condition_signatures"][0],
            measurement_definition_id=MD_TAIL_RMS.measurement_definition_id),),
        persistence_observation={"status": PASS, "exact_match": True,
                                 "detail": {"ModSlot30": True}},
    )


# --------------------------------------------------------------------------
# E3 -- two routes simultaneously. controlled_multi_field (g8e).
# NOTE: this run used TWO stimuli, one per measurement.
# --------------------------------------------------------------------------
def e3():
    pre = [_P("host:Filter 1 On", 1.0), _P("body:FXRack0", "<Aardvark FXRack0>"),
           _P("host:Macro 8", 1.0)]
    exp = _experiment([("ModSlot30", ROUTE_FILTER, "Aardvark ModSlot0"),
                       ("ModSlot31", ROUTE_DELAY, "Aardvark ModSlot1")],
                      pre, "controlled_multi_field",
                      "modulation_route_pair:VoiceFilter+FXDelay", "coexist_without_interference",
                      [STIM_SUSTAIN, STIM_PLUCK], "g8e_test3_coexistence.py")
    return EvidenceRecord(
        experiment_id="E3",
        epoch=HISTORICAL_EPOCH,
        experiment=exp,
        arms=_arms({"host:Filter 1 On": 1.0, "body:FXRack0": "<Aardvark FXRack0>",
                    "host:Macro 8": 1.0}),
        runtime_verifications=(),
        state_observation={"status": PASS, "diff_keys": ["ModSlot30", "ModSlot31"],
                           "matches_intent": True,
                           "control_hash": "fe45bdd8c3518d45",
                           "treatment_hash": "69c04f6f228a74d5",
                           "hashes_differ": True},
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=(
            CausalMeasurement(
                metric="spectral_centroid_hz",
                target=MeasurementTarget("VoiceFilter0.plainParams.kParamFreq",
                                         "VoiceFilter", "kParamFreq"),
                baseline=326.6, treatment=1161.2, delta=834.6,
                expected_direction="increase", observed_direction="increase",
                threshold=100.0, status=EFFECT_OBSERVED,
                measurement_condition_signature=exp["measurement_condition_signatures"][0],
                measurement_definition_id=MD_WHOLESIGNAL_CENTROID.measurement_definition_id),
            CausalMeasurement(
                metric="tail_rms_db",
                target=MeasurementTarget("FXRack0.FX[FXDelay].plainParams.kParamWet",
                                         "FXDelay", "kParamWet"),
                baseline=-72.26, treatment=-118.75, delta=-46.49,
                expected_direction="decrease", observed_direction="decrease",
                threshold=3.0, status=EFFECT_OBSERVED,
                measurement_condition_signature=exp["measurement_condition_signatures"][1],
                measurement_definition_id=MD_TAIL_RMS.measurement_definition_id),
        ),
        persistence_observation={"status": PASS, "exact_match": True,
                                 "detail": {"ModSlot30": True, "ModSlot31": True}},
    )


# --------------------------------------------------------------------------
# SYNTHETIC -- fabricated twin of E0 claiming no effect under identical
# conditions. Exists ONLY to exercise contradiction handling.
# --------------------------------------------------------------------------
def synthetic_contradiction_of_e0():
    base = e0()
    integrity = dict(base.integrity)
    integrity["synthetic"] = True
    integrity["synthetic_purpose"] = "contradiction-detector test fixture"
    return EvidenceRecord(
        experiment_id="SYN-E0-contradiction",
        epoch=base.epoch,
        experiment=base.experiment,          # identical mutation AND condition signature
        arms=base.arms,
        runtime_verifications=base.runtime_verifications,
        state_observation=base.state_observation,
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=(CausalMeasurement(
            metric="spectral_centroid_hz",
            target=MeasurementTarget("VoiceFilter0.plainParams.kParamFreq",
                                     "VoiceFilter", "kParamFreq"),
            baseline=348.7, treatment=348.7, delta=0.0,
            expected_direction="increase", observed_direction="none",
            threshold=100.0, status=NO_OBSERVED_EFFECT,
            measurement_condition_signature=base.experiment["measurement_condition_signatures"][0],
            measurement_definition_id=MD_WINDOWED_CENTROID.measurement_definition_id),),
        persistence_observation={"status": NOT_RUN},
        integrity=integrity,
    )


def all_real():
    return [e0(), e1(), e2a(), e2b(), e3()]
