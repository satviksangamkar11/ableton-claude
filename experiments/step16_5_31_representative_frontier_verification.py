"""16.5.31: Representative Current-Render Verification.

Objective: Determine whether the OSC-VOLUME reproduction failure (16.5.30)
is oscillator-specific, or evidence of a general historical-evidence ->
current-render reproducibility gap.

Rule now locked: A historical CAUSAL_VERIFIED capability is NOT
automatically producer-usable. It becomes PRODUCER_USABLE only after
current execution reproduces the control->effect->measurement relationship.

Method: Test 4 representative capabilities across independent families,
each reconstructed EXACTLY from its capability contract (same kernel,
same mutation value, same path, same prerequisites where applicable):

  1. envelope_field_attack   (Env0 whole-key mutation)
  2. filter_field_reso       (VoiceFilter0 nested-path mutation)
  3. global_field_mastervolume (Global0 nested-path mutation)
  4. modulation_route_voicefilter (ModSlot0 whole-key + host prerequisite)

Classification per test:
  CURRENTLY_VERIFIED               - current render reproduces historical effect
  CURRENTLY_CONTRADICTED           - current render shows no/different effect
  UNKNOWN                          - execution error, cannot determine

No producer/compiler changes. Pure verification.
"""
import sys, pickle, copy
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Prerequisite, Stimulus, MeasurementPlan, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT, WRONG_DIRECTION

print("=" * 80)
print("16.5.31: Representative Current-Render Verification")
print("=" * 80)
print()
print("Question: Is the OSC-VOLUME reproduction failure oscillator-specific,")
print("or a general historical-evidence -> current-render reproducibility gap?")
print()

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]

STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

results = []


def run_representative_test(label, target_path, mutation_value, metric, kernel_artifact,
                             expected_direction, threshold, hist_baseline, hist_treatment,
                             hist_delta, prerequisites=None):
    print("=" * 80)
    print("TEST: %s" % label)
    print("=" * 80)
    print()
    print("Reconstructed from capability contract:")
    print("  target_path:   %s" % target_path)
    print("  mutation:      %s" % (str(mutation_value)[:100]))
    print("  metric:        %s" % metric)
    print("  kernel:        %s" % kernel_artifact)
    print("  expected_dir:  %s  threshold: %s" % (expected_direction, threshold))
    print("  historical:    baseline=%.2f treatment=%.2f delta=%.2f" %
          (hist_baseline, hist_treatment, hist_delta))
    print()

    prereqs = prerequisites or []
    if prereqs:
        print("  prerequisites: %s" % [(p.field_path, p.declared_value) for p in prereqs])
        print()

    target = MeasurementTargetRef(target_path, None, None)
    body = copy.deepcopy(body_base)

    spec = ExperimentSpec(
        experiment_id="16.5.31-%s" % label.upper().replace(" ", "-").replace(".", "-"),
        mutations=[Mutation(target_path, mutation_value, "16.5.31: %s reproduction test" % label)],
        prerequisites=list(prereqs),
        isolation_level=SINGLE_FIELD,
        claim_subject=label.lower().replace(" ", "_"),
        claim_predicate="affects_%s" % metric,
        baseline_overrides=[],
        measurement_plans=[
            MeasurementPlan(
                metric=metric,
                target=target,
                expected_direction=expected_direction,
                threshold=threshold,
                stimulus=STIM,
                kernel_artifact=kernel_artifact,
            )
        ],
        notes="16.5.31: Reproduction test for %s, reconstructed from contract" % label,
    )

    try:
        validate(spec)
        skeleton = ({}, copy.deepcopy(body))
        record = harness.run(spec, skeleton=skeleton)
        if not record or not record.causal_measurements:
            print("[ERROR] No measurement recorded")
            return {"label": label, "verdict": "UNKNOWN", "reason": "no measurement recorded"}

        m = record.causal_measurements[0]
        print("[OK] Rendered via render_arm() (direct render path)")
        print("  current baseline:  %.2f" % m.baseline)
        print("  current treatment: %.2f" % m.treatment)
        print("  current delta:     %.2f" % m.delta)
        print("  current status:    %s" % m.status)
        print()

        baseline_matches = abs(m.baseline - hist_baseline) < max(2.0, abs(hist_baseline) * 0.1)
        print("Baseline consistency check: %s (current %.2f vs historical %.2f)" %
              ("MATCH" if baseline_matches else "DIFFERS", m.baseline, hist_baseline))

        if m.status == EFFECT_OBSERVED:
            direction_matches = m.observed_direction == expected_direction
            print("VERDICT: CURRENTLY_VERIFIED")
            print("  Effect reproduced. Direction: %s" % ("matches" if direction_matches else "DIFFERS"))
            verdict = "CURRENTLY_VERIFIED"
        elif m.status == NO_OBSERVED_EFFECT:
            print("VERDICT: CURRENTLY_CONTRADICTED")
            print("  No effect observed where historical evidence showed delta=%.2f" % hist_delta)
            verdict = "CURRENTLY_CONTRADICTED"
        elif m.status == WRONG_DIRECTION:
            print("VERDICT: CURRENTLY_CONTRADICTED")
            print("  Effect observed but WRONG DIRECTION vs historical")
            verdict = "CURRENTLY_CONTRADICTED"
        else:
            verdict = "UNKNOWN"

        return {
            "label": label, "verdict": verdict,
            "current_baseline": m.baseline, "current_treatment": m.treatment,
            "current_delta": m.delta, "current_status": m.status,
            "baseline_matches_historical": baseline_matches,
        }

    except Exception as e:
        print("[ERROR] Execution failed: %s" % e)
        import traceback
        traceback.print_exc()
        return {"label": label, "verdict": "UNKNOWN", "reason": str(e)}
    finally:
        print()


# ---- TEST 1: Envelope Attack (whole-key mutation) ----
r1 = run_representative_test(
    label="Envelope Attack",
    target_path="Env0",
    mutation_value={"plainParams": {"kParamAttack": 0.8}},
    metric="attack_onset_rms_db",
    kernel_artifact="attack_onset_rms_db.py",
    expected_direction="decrease",
    threshold=3.0,
    hist_baseline=-19.113398409784892,
    hist_treatment=-44.975847140950734,
    hist_delta=-25.86244873116584,
)
results.append(r1)

# ---- TEST 2: Filter Resonance (nested-path mutation) ----
r2 = run_representative_test(
    label="Filter Resonance",
    target_path="VoiceFilter0.plainParams.kParamReso",
    mutation_value=90.0,
    metric="overall_rms_db",
    kernel_artifact="overall_rms_db.py",
    expected_direction="increase",
    threshold=1.0,
    hist_baseline=-26.38009085696747,
    hist_treatment=-7.924990259745385,
    hist_delta=18.455100597222085,
)
results.append(r2)

# ---- TEST 3: Global Master Volume (nested-path mutation) ----
r3 = run_representative_test(
    label="Global Master Volume",
    target_path="Global0.plainParams.kParamMasterVolume",
    mutation_value=0.1,
    metric="overall_rms_db",
    kernel_artifact="overall_rms_db.py",
    expected_direction="decrease",
    threshold=3.0,
    hist_baseline=-19.248245789506942,
    hist_treatment=-26.23365813883149,
    hist_delta=-6.985412349324548,
)
results.append(r3)

# ---- TEST 4: Modulation Route VoiceFilter (whole-key + prerequisite) ----
r4 = run_representative_test(
    label="Modulation Route VoiceFilter",
    target_path="ModSlot0",
    mutation_value={
        "destModuleID": 0, "destModuleParamID": 3,
        "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
        "plainParams": {"kParamAmount": 29.682552814483643},
        "source": [6, 0],
    },
    metric="spectral_centroid_hz",
    kernel_artifact="wholesignal_centroid.py",
    expected_direction="increase",
    threshold=100.0,
    hist_baseline=348.66527315050166,
    hist_treatment=946.0409311097084,
    hist_delta=597.3756579592067,
    prerequisites=[Prerequisite("host:Filter 1 On", 1.0, True)],
)
results.append(r4)

# ---- SUMMARY ----
print("=" * 80)
print("SECTION: Summary Across Representative Families")
print("=" * 80)
print()

print("%-30s %-25s" % ("CAPABILITY", "VERDICT"))
print("-" * 60)
for r in results:
    print("%-30s %-25s" % (r["label"], r["verdict"]))
print()

verified_count = sum(1 for r in results if r["verdict"] == "CURRENTLY_VERIFIED")
contradicted_count = sum(1 for r in results if r["verdict"] == "CURRENTLY_CONTRADICTED")
unknown_count = sum(1 for r in results if r["verdict"] == "UNKNOWN")

print("CURRENTLY_VERIFIED:     %d / %d" % (verified_count, len(results)))
print("CURRENTLY_CONTRADICTED: %d / %d" % (contradicted_count, len(results)))
print("UNKNOWN:                %d / %d" % (unknown_count, len(results)))
print()

print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

if contradicted_count == 0 and verified_count >= 3:
    print("FINDING: The OSC-VOLUME reproduction failure appears OSCILLATOR-SPECIFIC.")
    print("  Representative controls across other families (envelope, filter,")
    print("  global, modulation route) DO reproduce their historical effects")
    print("  via the current direct render path.")
    print()
    print("Implication:")
    print("  Safe to build the first musical goal using controls that passed")
    print("  THIS verification (not the full 26-contract historical table).")
    print("  Oscillator-family controls remain excluded pending investigation.")
    overall = "OSCILLATOR_SPECIFIC_GAP"

elif contradicted_count >= 2:
    print("FINDING: MULTIPLE independent families show reproduction failure.")
    print("  This is NOT oscillator-specific. It indicates a broader")
    print("  historical-evidence -> current-render reproducibility gap")
    print("  affecting the corpus/skeleton used across this investigation.")
    print()
    print("Implication:")
    print("  Do NOT build producer reasoning on ANY historical CAUSAL_VERIFIED")
    print("  contract without first re-verifying it via direct render.")
    print("  This is now a corpus-level or skeleton-level concern, not a")
    print("  single-parameter concern.")
    overall = "GENERAL_REPRODUCIBILITY_GAP"

else:
    print("FINDING: Mixed/inconclusive result (1 contradiction, or execution errors).")
    print("  Needs individual inspection of the failing case(s) before")
    print("  concluding oscillator-specific vs. general.")
    overall = "MIXED_INCONCLUSIVE"

print()
print("=" * 80)
print("16.5.31 COMPLETE")
print("=" * 80)
print()
print("Overall: %s" % overall)
print()
print("Producer-usable controls from THIS test (CURRENTLY_VERIFIED only):")
for r in results:
    if r["verdict"] == "CURRENTLY_VERIFIED":
        print("  - %s" % r["label"])
