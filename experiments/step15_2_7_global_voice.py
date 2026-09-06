"""15.2.7: Global and Voice, one field at a time.
GLOBAL-MASTERVOLUME: causal+persistence (clean audio-level control).
GLOBAL-OVERSAMPLING: structural only (subtle anti-aliasing, causal not justified).
GLOBAL-MONOTOGGLE: structural only (voice-stealing behavior needs multi-note
    stimulus; our Stimulus dataclass sends exactly one note per plan --
    documented limitation, not silently skipped).
VOICE-RANDOMPAN: causal (new stereo_width kernel) + persistence, unison enabled
    via baseline_override so pan randomization has voices to act on.
VOICE-DETUNE: structural only (single unison-voice manual detune override).
"""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

specs = {}

specs["GLOBAL-MASTERVOLUME"] = ExperimentSpec(
    experiment_id="GLOBAL-MASTERVOLUME",
    mutations=[Mutation("Global0.plainParams.kParamMasterVolume", 0.1, "synthetic: low master volume")],
    prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
    claim_subject="global_field:Global.kParamMasterVolume", claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="overall_rms_db", target=TargetSpec("Global0.plainParams.kParamMasterVolume", "Global", "kParamMasterVolume"),
        expected_direction="decrease", threshold=3.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="overall_rms_db.py")],
    notes="control: implicit default master volume. treatment: 0.1 (near-silent).",
)

specs["GLOBAL-OVERSAMPLING"] = ExperimentSpec(
    experiment_id="GLOBAL-OVERSAMPLING",
    mutations=[Mutation("Global0.plainParams.kParamOversampling", 2.0, "corpus-verified real value (PML fixture); 4.0 was tried first and found OUT OF RANGE -- Serum silently clamped it to 2.0 on its own re-save, confirmed by direct probe")],
    prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
    claim_subject="global_field:Global.kParamOversampling", claim_predicate="constructs_mutates_persists",
    measurement_plans=[],
    notes="anti-aliasing quality setting -- causal effect is subtle/high-frequency-only, "
          "not claimed here. control: implicit default. treatment: 4.0 (real corpus value seen for PML fixture: 2.0).",
)

specs["GLOBAL-MONOTOGGLE"] = ExperimentSpec(
    experiment_id="GLOBAL-MONOTOGGLE",
    mutations=[Mutation("Global0.plainParams.kParamMonoToggle", 1.0, "synthetic: force mono/voice-stealing mode")],
    prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
    claim_subject="global_field:Global.kParamMonoToggle", claim_predicate="constructs_mutates_persists",
    measurement_plans=[],
    notes="KNOWN LIMITATION: mono vs poly voice-stealing behavior is only observable with "
          "OVERLAPPING notes; our Stimulus sends exactly one note per render, so no causal "
          "claim is attempted here. This is a real harness capability gap, documented not hidden.",
)

specs["VOICE-RANDOMPAN"] = ExperimentSpec(
    experiment_id="VOICE-RANDOMPAN",
    mutations=[Mutation("VoicePanel0.plainParams.kParamGlobalRandomOscPan", 100.0, "synthetic: max pan randomization")],
    prerequisites=[Prerequisite("host:A Unison", 1.0),
                  Prerequisite("host:A Uni Width", 0.0)],
    baseline_overrides=[], isolation_level=SINGLE_FIELD,
    claim_subject="voice_field:VoicePanel.kParamGlobalRandomOscPan", claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="stereo_width", target=TargetSpec("VoicePanel0.plainParams.kParamGlobalRandomOscPan", "VoicePanel", "kParamGlobalRandomOscPan"),
        expected_direction="increase", threshold=0.02,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="stereo_width.py")],
    notes="prerequisites: A Unison enabled AND A Uni Width FORCED TO 0 (both host, both arms "
          "identical) -- A Uni Width defaults to 1.0 and is Serum's OWN built-in unison stereo "
          "spread, independent of kParamGlobalRandomOscPan; discovered via direct host-default "
          "probe after the first attempt showed a ceiling effect (control width=0.503, already "
          "saturated). Neutralizing it isolates whether GlobalRandomOscPan alone can still widen "
          "the signal. control: implicit default randomization (0). treatment: kParamGlobalRandomOscPan=100.0.",
)

specs["VOICE-DETUNE"] = ExperimentSpec(
    experiment_id="VOICE-DETUNE",
    mutations=[Mutation("VoicePanel0.plainParams.kParamVoice1Detune", 50.0, "synthetic: manual voice-1 detune override")],
    prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
    claim_subject="voice_field:VoicePanel.kParamVoice1Detune", claim_predicate="constructs_mutates_persists",
    measurement_plans=[],
    notes="per-unison-voice manual override; causal effect requires unison active AND "
          "voice-index addressing not yet characterized -- structural claim only this round.",
)

records = {}
for eid, spec in specs.items():
    rec = harness.run(spec)
    print("%-20s gates=%s" % (eid, rec.gate_completeness()))
    if rec.causal_measurements:
        m = rec.causal_measurements[0]
        print("   causal: base=%.4f treat=%.4f delta=%+.4f dir=%s status=%s"
              % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
    print("   persistence:", rec.persistence_observation.get("status"), rec.persistence_observation.get("detail"))
    records[eid] = rec

import pickle
pickle.dump(records, open(r"D:/ableton claude/experiments/_global_voice_records.pkl", "wb"))
