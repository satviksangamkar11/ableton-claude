"""16.4.3c-10: formal EvidenceRecord for the tested causal relationship
between source[0]=6 and LFO0's configured state -- via the real harness,
not an ad-hoc script. Scoped claim: causal effect exists and is rate-
dependent in this tested context. Does NOT assert universal source-ID
semantics."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

RATE = 4.919910075711187  # R2, real corpus value, representative of the validated rate range
STIM = Stimulus(note=48, velocity=110, note_len=4.0, render_seconds=4.5)
AMOUNT = 29.682552814483643

def route(source):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': AMOUNT}, 'source': source}

def run_case(exp_id, source, subject_suffix):
    spec = ExperimentSpec(
        experiment_id=exp_id,
        mutations=[Mutation("ModSlot30", route(source),
                            "source=%s under explicit LFO0 context (16.4.3c formalization)" % source)],
        prerequisites=[Prerequisite("host:Filter 1 On", 1.0, must_hold_identical=True)],
        baseline_overrides=[Mutation("LFO0.plainParams",
                                     {"kParamDefaultMode": 0.0, "kParamMode": "Free", "kParamRate": RATE},
                                     "real corpus value, explicit, applied identically to both arms")],
        isolation_level=SINGLE_FIELD,
        claim_subject="modulation_source_rate_dependence:%s" % subject_suffix,
        claim_predicate="produces_rate_dependent_destination_response",
        measurement_plans=[MeasurementPlan(
            metric="centroid_zero_crossing_rate",
            target=TargetSpec("VoiceFilter0.plainParams.kParamFreq", "VoiceFilter", "kParamFreq"),
            expected_direction="increase", threshold=3.0, stimulus=STIM,
            kernel_artifact="centroid_zero_crossing_rate.py")],
        notes="16.4.3c-10 formal evidence. Scoped claim: source=%s produces a reproducible, "
             "rate-dependent destination-response signature in this explicit-LFO0 context. Does "
             "NOT assert this generalizes to every context or that source[0] universally means LFO." % source,
    )
    rec = harness.run(spec)
    m = rec.causal_measurements[0]
    print("%-20s gates=%s persist=%s causal(base=%.1f treat=%.1f delta=%+.1f status=%s)" % (
        exp_id, rec.gate_completeness(), rec.persistence_observation.get("status"),
        m.baseline, m.treatment, m.delta, m.status))
    return rec

rec_lfo = run_case("LFO-RATE-DEP-6", [6, 0], "source6_lfo0context")
rec_neg = run_case("LFO-RATE-DEP-25", [25, 0], "source25_lfo0context")

pickle.dump({"positive": rec_lfo, "negative": rec_neg},
           open(r"D:/ableton claude/experiments/_lfo_rate_dependence_records.pkl", "wb"))
