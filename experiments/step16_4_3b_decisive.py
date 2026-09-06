"""16.4.3b-2: the decisive [6,0] vs [25,0] experiment. Explicit, real,
non-invented LFO0 configuration (mode=Free, rate~4.92, real corpus values)
applied identically to BOTH arms via baseline_override, so LFO0's own state
can no longer be ambiguous the way it was in E0/E1. Same destination/amount/
stimulus as the original SRC-6/SRC-25 sweep. Discriminator is periodicity
(modulation_frequency_hz + modulation_depth), not centroid movement."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

# real corpus LFO0 config: mode=Free, rate~4.92Hz (median-adjacent, real, not invented)
REAL_LFO0_PLAINPARAMS = {'kParamDefaultMode': 0.0, 'kParamMode': 'Free',
                         'kParamRate': 4.919910075711187}

STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0)
AMOUNT = 29.682552814483643  # Aardvark's real ModSlot0 amount, unchanged from E0/E1/SRC-*

def route(source):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': AMOUNT},
           'source': source}

def run_candidate(label, source):
    spec = ExperimentSpec(
        experiment_id="DECISIVE-%s" % label,
        mutations=[Mutation("ModSlot30", route(source),
                            "candidate source=%s, explicit LFO0 context" % source)],
        prerequisites=[Prerequisite("host:Filter 1 On", 1.0, must_hold_identical=True)],
        baseline_overrides=[Mutation("LFO0.plainParams", REAL_LFO0_PLAINPARAMS,
                                     "real corpus LFO0 config (Free, rate~4.92), applied "
                                     "IDENTICALLY to both arms so LFO0's own state is no "
                                     "longer ambiguous/unconfigured")],
        isolation_level=SINGLE_FIELD,
        claim_subject="modulation_source_decisive:source=%s" % source,
        claim_predicate="produces_periodic_modulation",
        measurement_plans=[
            MeasurementPlan(metric="modulation_frequency_hz",
                            target=TargetSpec("VoiceFilter0.plainParams.kParamFreq", "VoiceFilter", "kParamFreq"),
                            expected_direction="none", threshold=0.5, stimulus=STIM,
                            kernel_artifact="modulation_frequency_hz.py"),
            MeasurementPlan(metric="modulation_depth",
                            target=TargetSpec("VoiceFilter0.plainParams.kParamFreq", "VoiceFilter", "kParamFreq"),
                            expected_direction="none", threshold=0.005, stimulus=STIM,
                            kernel_artifact="modulation_depth.py"),
        ],
        notes="Decisive discriminator for source=%s under an EXPLICIT, real, non-default LFO0 "
             "config -- control has no route (empty ModSlot30), treatment has the route." % source,
    )
    rec = harness.run(spec)
    print("=== %s (source=%s) ===" % (label, source))
    print(" gates:", rec.gate_completeness())
    print(" persistence:", rec.persistence_observation.get("status"))
    for m in rec.causal_measurements:
        print(" %-24s base=%.5f treat=%.5f delta=%+.5f status=%s" % (m.metric, m.baseline, m.treatment, m.delta, m.status))
    return rec

rec_a = run_candidate("A-source6", [6, 0])
print()
rec_b = run_candidate("B-source25", [25, 0])

pickle.dump({"A": rec_a, "B": rec_b}, open(r"D:/ableton claude/experiments/_decisive_lfo_records.pkl", "wb"))
