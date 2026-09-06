"""16.5.38: Filter Resonance prerequisite reconstruction.

16.5.37 left Filter Resonance INCONCLUSIVE:
  current baseline -19.25 dB (native default) vs historical -26.38 dB
  no effect observed
  contract records prerequisites=() -- but a lower-than-default baseline
  is consistent with an engaged filter, and the sibling VoiceFilter capability
  (ModRoute VoiceFilter) DOES carry host:Filter 1 On=1.0 and DID reproduce.

Test: identical 16.5.37 spec for Filter Resonance, with ONE prerequisite added:
  host:Filter 1 On = 1.0

Same actuator path (harness.run, skeleton=None -> capture_v8_skeleton).
Same metric/kernel/threshold/direction/value as before. Only the prerequisite
changes. This isolates whether the omitted prerequisite explains the
INCONCLUSIVE result.
"""
import sys
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Prerequisite, Stimulus, MeasurementPlan, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT, WRONG_DIRECTION

STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

print("=" * 80)
print("16.5.38: Filter Resonance Prerequisite Reconstruction")
print("=" * 80)
print()

HIST_BASE = -26.38009085696747
HIST_TREAT = -7.924990259745385
HIST_DELTA = 18.455100597222085

print("Historical: baseline=%.2f treatment=%.2f delta=%.2f" % (HIST_BASE, HIST_TREAT, HIST_DELTA))
print("16.5.37 (no prerequisite): baseline=-19.25 treatment=-19.25 delta=0.00 NO_OBSERVED_EFFECT")
print()
print("Hypothesis: filter must be engaged (host:Filter 1 On=1.0) for resonance to matter.")
print()

spec = ExperimentSpec(
    experiment_id="16.5.38-FILTER-RESO-WITH-PREREQ",
    mutations=[Mutation("VoiceFilter0.plainParams.kParamReso", 90.0, "16.5.38 with filter-on prerequisite")],
    prerequisites=[Prerequisite("host:Filter 1 On", 1.0, True)],
    isolation_level=SINGLE_FIELD,
    claim_subject="filter_resonance",
    claim_predicate="affects_overall_rms_db",
    baseline_overrides=[],
    measurement_plans=[MeasurementPlan(
        metric="overall_rms_db",
        target=MeasurementTargetRef("VoiceFilter0.plainParams.kParamReso", None, None),
        expected_direction="increase", threshold=1.0,
        stimulus=STIM, kernel_artifact="overall_rms_db.py")],
    notes="16.5.38: reconstruct filter resonance with host:Filter 1 On prerequisite",
)

try:
    validate(spec)
    rec = harness.run(spec)  # skeleton=None -> capture_v8_skeleton()
    if not rec or not rec.causal_measurements:
        print("[ERROR] no measurement recorded")
        sys.exit(1)

    m = rec.causal_measurements[0]
    so = rec.state_observation
    pe = rec.persistence_observation
    rv = rec.runtime_verifications

    print("RESULT:")
    print("  current baseline:  %.2f dB" % m.baseline)
    print("  current treatment: %.2f dB" % m.treatment)
    print("  current delta:     %.2f dB" % m.delta)
    print("  status:            %s" % m.status)
    print()
    print("  state_diff matches_intent: %s" % so.get("matches_intent"))
    print("  persistence status:        %s" % pe.get("status"))
    if rv:
        print("  runtime_verifications: %s" % rv[0])
    print()

    base_close = abs(m.baseline - HIST_BASE) < max(2.0, abs(HIST_BASE) * 0.10)
    print("Baseline vs historical: %s (%.2f vs %.2f)" %
          ("MATCH" if base_close else "DIFFERS", m.baseline, HIST_BASE))
    print()

    if m.status == EFFECT_OBSERVED and m.observed_direction == "increase":
        if base_close:
            verdict = "CURRENTLY_REPRODUCED"
            print("VERDICT: CURRENTLY_REPRODUCED")
            print("  Effect observed, correct direction, baseline matches historical context.")
            print("  => Omitted prerequisite CONFIRMED as the cause of 16.5.37's INCONCLUSIVE result.")
            print("  => Contract-completeness defect: filter_field_reso's stored prerequisites=()")
            print("     does not match its witness experiment's actual execution context.")
        else:
            verdict = "REPRODUCED_DIFFERENT_CONTEXT"
            print("VERDICT: REPRODUCED_DIFFERENT_CONTEXT")
            print("  Effect observed and correct direction, but baseline does not match")
            print("  historical -26.38 dB. The prerequisite helps but does not fully")
            print("  reconstruct the historical context. Flag for 16.5.40 context recovery.")
    elif m.status == NO_OBSERVED_EFFECT:
        verdict = "CURRENTLY_NOT_REPRODUCED"
        print("VERDICT: CURRENTLY_NOT_REPRODUCED")
        print("  Adding host:Filter 1 On=1.0 did not restore the effect.")
        print("  => The omitted-prerequisite hypothesis is REJECTED.")
        print("  => Context recovery must search the archived witness record directly")
        print("     (16.5.40) rather than inferring from the sibling ModRoute contract.")
    elif m.status == WRONG_DIRECTION:
        verdict = "CURRENTLY_NOT_REPRODUCED"
        print("VERDICT: CURRENTLY_NOT_REPRODUCED (wrong direction)")
    else:
        verdict = "INCONCLUSIVE"
        print("VERDICT: INCONCLUSIVE")

except Exception as e:
    print("[ERROR] %s" % e)
    import traceback
    traceback.print_exc()
    verdict = "INCONCLUSIVE"

print()
print("=" * 80)
print("16.5.38 COMPLETE   Verdict: %s" % verdict)
print("=" * 80)
