"""16.5.29: Runtime State-Application Sanity Test.

Objective: Establish whether the Serum runtime actually uses the state
that the harness writes and loads.

Single question: When we set Oscillator0.Volume = 0.0, does the rendered
audio reflect that change?

Method:
  1. Render with Oscillator0.Volume = current (control)
  2. Render with Oscillator0.Volume = 0.0 (treatment)
  3. Observe independently:
     - State file value (what was written)
     - Runtime state value (what Serum loaded, if readable)
     - Audio consequence (did centroid change?)
     - Persistence (did state survive save/load?)
  4. Evaluate using success matrix
  5. Report: State -> DSP -> Audio pipeline working or broken?

No FXEQ work. No compiler/producer changes. Pure infrastructure test.
"""
import sys, pickle, copy, json
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Stimulus, MeasurementPlan, TargetSpec, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import define, MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT

print("=" * 80)
print("16.5.29: Runtime State-Application Sanity Test")
print("=" * 80)
print()
print("Single Question:")
print("  Does the Serum runtime actually render Oscillator0.Volume = 0.0?")
print()

# ---- Load corpus ----
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]

# ---- Measurement setup (use spectral centroid) ----
TARGET_FXEQ = MeasurementTargetRef(
    "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",
    "FXEQ", "kParamFreq1"
)
MD_CENTROID = define("spectral_centroid_hz", "wholesignal_centroid.py", TARGET_FXEQ)
STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

print("Measurement: spectral_centroid_hz (will change if oscillator volume affects signal)")
print("Stimulus: note 48, velocity 110, 1.8 beats, 2.0 sec render")
print()

# ---- SECTION 1: Inspect current state ----
print("SECTION 1: Current Oscillator0 State")
print("-" * 80)
print()

current_volume = body_base.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
print("OBSERVED - Current Oscillator0.kParamVolume: %s" % current_volume)
if current_volume is None:
    print("[ERROR] Oscillator0.kParamVolume not found")
    sys.exit(1)
print()

# ---- SECTION 2: Control render (volume unchanged) ----
print("SECTION 2: Control Render (Volume = %.4f)" % current_volume)
print("-" * 80)
print()

control_body = copy.deepcopy(body_base)

print("OBSERVED - Control body state:")
print("  Oscillator0.kParamVolume (before): %.4f" % current_volume)
print()

spec_control = ExperimentSpec(
    experiment_id="16.5.29-CONTROL-BASELINE-VOLUME",
    mutations=[],  # No mutations - baseline only
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="oscillator_volume",
    claim_predicate="affects_spectral_centroid_hz",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="spectral_centroid_hz",
            target=TARGET_FXEQ,
            expected_direction="decrease",
            threshold=50.0,
            stimulus=STIM,
            kernel_artifact="wholesignal_centroid.py",
        )
    ],
    notes="16.5.29 Control: Baseline Centroid with normal oscillator volume",
)

try:
    validate(spec_control)
    skeleton_control = ({}, copy.deepcopy(control_body))
    record_control = harness.run(spec_control, skeleton=skeleton_control)
    if record_control and record_control.causal_measurements:
        m_control = record_control.causal_measurements[0]
        print("[OK] Control measurement complete")
        print("  baseline_centroid: %.2f Hz" % m_control.baseline)
        control_centroid = m_control.baseline
    else:
        print("[ERROR] Control measurement failed")
        control_centroid = None
except Exception as e:
    print("[ERROR] Control execution: %s" % e)
    import traceback
    traceback.print_exc()
    control_centroid = None

print()

# ---- SECTION 3: Treatment render (volume = 0.0) ----
print("SECTION 3: Treatment Render (Volume = 0.0)")
print("-" * 80)
print()

treatment_body = copy.deepcopy(body_base)

print("APPLYING MUTATION: Oscillator0.kParamVolume -> 0.0")
treatment_body["Oscillator0"]["plainParams"]["kParamVolume"] = 0.0

treatment_volume_after = treatment_body.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
print("OBSERVED - Treatment body state after mutation:")
print("  Oscillator0.kParamVolume (after): %.4f" % treatment_volume_after)

if treatment_volume_after == 0.0:
    print("  [OK] Mutation applied to body")
    write_success = True
else:
    print("  [ERROR] Mutation not applied")
    write_success = False

print()

spec_treatment = ExperimentSpec(
    experiment_id="16.5.29-TREATMENT-VOLUME-ZERO",
    mutations=[
        Mutation(
            "Oscillator0.plainParams.kParamVolume",
            0.0,
            "16.5.29: Test if muting oscillator affects render"
        )
    ],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="oscillator_volume",
    claim_predicate="affects_spectral_centroid_hz",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="spectral_centroid_hz",
            target=TARGET_FXEQ,
            expected_direction="decrease",
            threshold=50.0,
            stimulus=STIM,
            kernel_artifact="wholesignal_centroid.py",
        )
    ],
    notes="16.5.29 Treatment: Centroid with oscillator muted (volume=0)",
)

try:
    validate(spec_treatment)
    skeleton_treatment = ({}, copy.deepcopy(treatment_body))
    record_treatment = harness.run(spec_treatment, skeleton=skeleton_treatment)
    if record_treatment and record_treatment.causal_measurements:
        m_treatment = record_treatment.causal_measurements[0]
        print("[OK] Treatment measurement complete")
        print("  treatment_centroid: %.2f Hz" % m_treatment.treatment)
        treatment_centroid = m_treatment.treatment
    else:
        print("[ERROR] Treatment measurement failed")
        treatment_centroid = None
except Exception as e:
    print("[ERROR] Treatment execution: %s" % e)
    import traceback
    traceback.print_exc()
    treatment_centroid = None

print()

# ---- SECTION 4: Analyze results ----
print("=" * 80)
print("SECTION 4: Evidence Analysis")
print("=" * 80)
print()

print("State Write:")
print("  Requested: Oscillator0.Volume = 0.0")
print("  Written to body: %s" % ("YES" if write_success else "NO"))
print()

print("State File Value:")
print("  Would be: 0.0 (if correctly written)")
print("  Status: %s (not directly readable from file)" % ("WRITTEN" if write_success else "FAILED"))
print()

print("Runtime State Value:")
print("  Can Serum runtime be directly read? UNKNOWN")
print("  (Not directly observable in current harness API)")
print("  Inference from persistence: TBD")
print()

if control_centroid is not None and treatment_centroid is not None:
    rms_delta = treatment_centroid - control_centroid
    print("Audio Consequence:")
    print("  Control Centroid:     %.2f Hz" % control_centroid)
    print("  Treatment Centroid:   %.2f Hz" % treatment_centroid)
    print("  Delta:           %.2f Hz" % rms_delta)
    print()

    if rms_delta < -1.0:
        print("  OBSERVED: Audio changed significantly (muting had effect)")
        audio_changed = True
    elif rms_delta > 1.0:
        print("  OBSERVED: Audio changed significantly (opposite direction)")
        audio_changed = True
    else:
        print("  OBSERVED: Audio did NOT change (delta within noise)")
        audio_changed = False
else:
    print("Audio Consequence:")
    print("  MEASUREMENT FAILED - cannot evaluate")
    audio_changed = None

print()

# ---- SECTION 5: Persistence check ----
print("Persistence (Fifth Observation):")
print("  Whether mutations persisted after save/load cycle")
print("  Record contains: persistence_observation field")

if record_treatment:
    persist = record_treatment.persistence_observation
    print("  Status: %s" % persist.get("status", "?"))
    if persist.get("checked"):
        print("  Exact match: %s" % persist.get("exact_match"))
        if persist.get("detail"):
            print("  Detail: %s" % str(persist.get("detail"))[:100])
print()

# ---- SECTION 6: Success Matrix ----
print("=" * 80)
print("SUCCESS MATRIX EVALUATION")
print("=" * 80)
print()

print("State write (to body): %s" % ("correct" if write_success else "failed"))
print("Runtime readback: unknown (not directly observable)")
print("Audio change: %s" % ("yes" if audio_changed else "no" if audio_changed is not None else "unknown"))
print()

print("Row from matrix:")
if write_success:
    if audio_changed:
        print("  State->DSP->Audio path: WORKING")
        print("  Interpretation: Runtime state is used in rendering")
    elif audio_changed is False:
        print("  State write successful but no audio change")
        print("  Interpretation: Either DSP doesn't use the state, or render caches")
    else:
        print("  State write successful but audio measurement failed")
        print("  Interpretation: Cannot evaluate audio consequence")
else:
    print("  State write to body failed")
    print("  Interpretation: Mutation mechanism broken")

print()

# ---- SECTION 7: Verdict ----
print("=" * 80)
print("VERDICT")
print("=" * 80)
print()

if write_success and audio_changed:
    print("RESULT: State->DSP->Audio pipeline WORKS")
    print()
    print("Implication:")
    print("  The harness successfully writes state and Serum renders it.")
    print("  Producer sonic-effect experiments can proceed with confidence.")
    print("  Return to FXEQ investigation.")
    verdict = "PASS"

elif write_success and audio_changed is False:
    print("RESULT: State applied but audio unchanged")
    print()
    print("Implication:")
    print("  State mutation succeeded but did not affect rendered audio.")
    print("  Possible causes:")
    print("    1. DSP does not respect the loaded state")
    print("    2. Audio is cached/not re-rendered per state")
    print("    3. Render path bypasses Oscillator")
    print("  Foundational defect: State does not control sound.")
    verdict = "FAIL_AUDIO"

elif not write_success:
    print("RESULT: State write failed")
    print()
    print("Implication:")
    print("  Mutation to body did not take effect.")
    print("  Foundational defect: State mutation mechanism broken.")
    verdict = "FAIL_WRITE"

else:
    print("RESULT: Cannot evaluate")
    print()
    print("Implication:")
    print("  Audio measurement or harness execution failed.")
    print("  Cannot determine state->DSP->Audio integrity.")
    verdict = "UNKNOWN"

print()
print("=" * 80)
print("16.5.29 COMPLETE")
print("=" * 80)
print()
print("Verdict: %s" % verdict)
print()
print("Next step:")
if verdict == "PASS":
    print("  16.5.30: Return to FXEQ investigation")
else:
    print("  STOP: Foundational infrastructure issue detected")
    print("  Resolve state-application pipeline before continuing")
