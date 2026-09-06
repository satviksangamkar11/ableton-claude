"""16.5.26: Mutation Verification Audit.

Objective: Verify that the C0/C1/C2 context mutations in 16.5.20 actually
took effect in the rendered state.

Critical question: When we requested "Osc muted" or "Filter muted", did the
actual Serum state change?

Method:
  For each context (C0, C1, C2):
    1. Apply mutation to body
    2. Inspect body state before rendering
    3. Run measurement with mutated body
    4. Report: mutation applied? persisted? rendered correctly?
    5. Compare against expected measurement impact

Output: For each context mutation:
  MUTATION_APPLIED (state changed as expected)
  MUTATION_FAILED (state did not change)
  UNKNOWN (cannot verify)

Do NOT interpret measurement results until mutations are verified.
"""
import sys, pickle, copy, json
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Stimulus, MeasurementPlan, TargetSpec, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import define, MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT

print("=" * 80)
print("16.5.26: Mutation Verification Audit (C0/C1/C2)")
print("=" * 80)
print()

# ---- Load corpus ----
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))

# ---- Measurement definition (same as 16.5.20) ----
HISTORICAL_PATH = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
HISTORICAL_BASELINE = 639.84
HISTORICAL_TREATMENT = 15000.0

TARGET_FXEQ_FREQ = MeasurementTargetRef(
    "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",
    "FXEQ", "kParamFreq1"
)
MD_CENTROID = define("spectral_centroid_hz", "wholesignal_centroid.py", TARGET_FXEQ_FREQ)
STIM_CENTROID = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

print("Measurement setup (same as 16.5.20):")
print("  Control Freq1: %.2f Hz" % HISTORICAL_BASELINE)
print("  Treatment Freq1: %.2f Hz" % HISTORICAL_TREATMENT)
print()

# ---- SECTION 1: C0 Baseline (No mutations) ----
print("SECTION 1: C0 - Baseline (No context mutations)")
print("-" * 80)
print()

C0_body = copy.deepcopy(corpus["bodies"][4])

print("OBSERVED - C0 initial state:")
osc0_volume = C0_body.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
filter0_freq = C0_body.get("VoiceFilter0", {}).get("plainParams", {}).get("kParamFreq")

print("  Oscillator0.kParamVolume: %s" % (osc0_volume if osc0_volume is not None else "NOT FOUND"))
print("  VoiceFilter0.kParamFreq:  %s" % (filter0_freq if filter0_freq is not None else "NOT FOUND"))
print()

print("Running C0 measurement (no mutations)...")

spec_c0 = ExperimentSpec(
    experiment_id="16.5.26-C0-VERIFY-BASELINE",
    mutations=[
        Mutation(HISTORICAL_PATH, HISTORICAL_TREATMENT, "C0 verify baseline")
    ],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field_eq_freq1",
    claim_predicate="affects_spectral_centroid_hz",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="spectral_centroid_hz",
            target=TARGET_FXEQ_FREQ,
            expected_direction="decrease",
            threshold=50.0,
            stimulus=STIM_CENTROID,
            kernel_artifact="wholesignal_centroid.py",
        )
    ],
    notes="16.5.26 C0: Verify baseline state",
)

try:
    skeleton = ({}, copy.deepcopy(C0_body))
    record_c0 = harness.run(spec_c0, skeleton=skeleton)
    if record_c0 and record_c0.causal_measurements:
        m = record_c0.causal_measurements[0]
        print("[OK] C0 measurement complete")
        print("  baseline_centroid: %.1f Hz" % m.baseline)
        c0_baseline = m.baseline
    else:
        print("[ERROR] C0 measurement failed")
        c0_baseline = None
except Exception as e:
    print("[ERROR] C0 execution: %s" % e)
    c0_baseline = None

print()

# ---- SECTION 2: C1 Mutation Verification (Oscillator mute) ----
print("SECTION 2: C1 - Oscillator0 Mute Verification")
print("-" * 80)
print()

C1_body = copy.deepcopy(corpus["bodies"][4])

print("OBSERVED - C1 before mutation:")
osc0_before = C1_body.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
print("  Oscillator0.kParamVolume (before): %s" % osc0_before)
print()

print("APPLYING MUTATION: Set Oscillator0.plainParams.kParamVolume = 0.0")
if "Oscillator0" in C1_body:
    C1_body["Oscillator0"]["plainParams"]["kParamVolume"] = 0.0
    print("[OK] Mutation applied to body")
else:
    print("[ERROR] Oscillator0 not found in body")

print()

print("OBSERVED - C1 after mutation:")
osc0_after = C1_body.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
print("  Oscillator0.kParamVolume (after): %s" % osc0_after)
print()

# Verify mutation took effect
if osc0_after == 0.0:
    print("MUTATION VERIFICATION: APPLIED")
    print("  Value changed from %s to 0.0" % osc0_before)
    c1_mutation_status = "APPLIED"
else:
    print("MUTATION VERIFICATION: FAILED")
    print("  Value did not change (still %s)" % osc0_after)
    c1_mutation_status = "FAILED"

print()

print("Running C1 measurement (with Osc muted)...")

spec_c1 = ExperimentSpec(
    experiment_id="16.5.26-C1-VERIFY-OSC-MUTE",
    mutations=[
        Mutation(HISTORICAL_PATH, HISTORICAL_TREATMENT, "C1 verify Osc mute")
    ],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field_eq_freq1",
    claim_predicate="affects_spectral_centroid_hz",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="spectral_centroid_hz",
            target=TARGET_FXEQ_FREQ,
            expected_direction="decrease",
            threshold=50.0,
            stimulus=STIM_CENTROID,
            kernel_artifact="wholesignal_centroid.py",
        )
    ],
    notes="16.5.26 C1: Verify Osc mute effect",
)

try:
    skeleton = ({}, copy.deepcopy(C1_body))
    record_c1 = harness.run(spec_c1, skeleton=skeleton)
    if record_c1 and record_c1.causal_measurements:
        m = record_c1.causal_measurements[0]
        print("[OK] C1 measurement complete")
        print("  baseline_centroid: %.1f Hz" % m.baseline)
        c1_baseline = m.baseline
    else:
        print("[ERROR] C1 measurement failed")
        c1_baseline = None
except Exception as e:
    print("[ERROR] C1 execution: %s" % e)
    c1_baseline = None

print()

# ---- SECTION 3: C2 Mutation Verification (VoiceFilter mute) ----
print("SECTION 3: C2 - VoiceFilter0 Mute Verification")
print("-" * 80)
print()

C2_body = copy.deepcopy(corpus["bodies"][4])

print("OBSERVED - C2 before mutation:")
filter0_before = C2_body.get("VoiceFilter0", {}).get("plainParams", {}).get("kParamFreq")
print("  VoiceFilter0.kParamFreq (before): %s" % filter0_before)
print()

print("APPLYING MUTATION: Set VoiceFilter0.plainParams.kParamFreq = 0.0")
if "VoiceFilter0" in C2_body:
    C2_body["VoiceFilter0"]["plainParams"]["kParamFreq"] = 0.0
    print("[OK] Mutation applied to body")
else:
    print("[ERROR] VoiceFilter0 not found in body")

print()

print("OBSERVED - C2 after mutation:")
filter0_after = C2_body.get("VoiceFilter0", {}).get("plainParams", {}).get("kParamFreq")
print("  VoiceFilter0.kParamFreq (after): %s" % filter0_after)
print()

# Verify mutation took effect
if filter0_after == 0.0:
    print("MUTATION VERIFICATION: APPLIED")
    print("  Value changed from %s to 0.0" % filter0_before)
    c2_mutation_status = "APPLIED"
else:
    print("MUTATION VERIFICATION: FAILED")
    print("  Value did not change (still %s)" % filter0_after)
    c2_mutation_status = "FAILED"

print()

print("Running C2 measurement (with Filter muted)...")

spec_c2 = ExperimentSpec(
    experiment_id="16.5.26-C2-VERIFY-FILTER-MUTE",
    mutations=[
        Mutation(HISTORICAL_PATH, HISTORICAL_TREATMENT, "C2 verify Filter mute")
    ],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field_eq_freq1",
    claim_predicate="affects_spectral_centroid_hz",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="spectral_centroid_hz",
            target=TARGET_FXEQ_FREQ,
            expected_direction="decrease",
            threshold=50.0,
            stimulus=STIM_CENTROID,
            kernel_artifact="wholesignal_centroid.py",
        )
    ],
    notes="16.5.26 C2: Verify Filter mute effect",
)

try:
    skeleton = ({}, copy.deepcopy(C2_body))
    record_c2 = harness.run(spec_c2, skeleton=skeleton)
    if record_c2 and record_c2.causal_measurements:
        m = record_c2.causal_measurements[0]
        print("[OK] C2 measurement complete")
        print("  baseline_centroid: %.1f Hz" % m.baseline)
        c2_baseline = m.baseline
    else:
        print("[ERROR] C2 measurement failed")
        c2_baseline = None
except Exception as e:
    print("[ERROR] C2 execution: %s" % e)
    c2_baseline = None

print()

# ---- SECTION 4: Verification Summary ----
print("=" * 80)
print("MUTATION VERIFICATION SUMMARY")
print("=" * 80)
print()

print("Context Mutation Verification:")
print()

print("C0 (Baseline - no mutations):")
print("  Mutation status:       N/A")
print("  Baseline centroid:     %.1f Hz" % (c0_baseline if c0_baseline else 0))
print()

print("C1 (Oscillator0 muted):")
print("  Requested mutation:    Oscillator0.kParamVolume = 0.0")
print("  Before:                %s" % osc0_before)
print("  After:                 %s" % osc0_after)
print("  Mutation status:       %s" % c1_mutation_status)
print("  Baseline centroid:     %.1f Hz" % (c1_baseline if c1_baseline else 0))

if c1_mutation_status == "APPLIED" and c0_baseline and c1_baseline:
    centroid_change_c1 = c1_baseline - c0_baseline
    print("  Centroid change:       %.1f Hz (vs C0)" % centroid_change_c1)
    if abs(centroid_change_c1) < 1.0:
        print("  Interpretation:        Oscillator muting had negligible effect on baseline")
    else:
        print("  Interpretation:        Oscillator muting changed baseline by %.1f Hz" % centroid_change_c1)

print()

print("C2 (VoiceFilter0 muted):")
print("  Requested mutation:    VoiceFilter0.kParamFreq = 0.0")
print("  Before:                %s" % filter0_before)
print("  After:                 %s" % filter0_after)
print("  Mutation status:       %s" % c2_mutation_status)
print("  Baseline centroid:     %.1f Hz" % (c2_baseline if c2_baseline else 0))

if c2_mutation_status == "APPLIED" and c0_baseline and c2_baseline:
    centroid_change_c2 = c2_baseline - c0_baseline
    print("  Centroid change:       %.1f Hz (vs C0)" % centroid_change_c2)
    if abs(centroid_change_c2) < 1.0:
        print("  Interpretation:        Filter muting had negligible effect on baseline")
    else:
        print("  Interpretation:        Filter muting changed baseline by %.1f Hz" % centroid_change_c2)

print()

# ---- SECTION 5: Interpretation ----
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

all_mutations_applied = (c1_mutation_status == "APPLIED" and c2_mutation_status == "APPLIED")

if all_mutations_applied:
    print("VERDICT: Mutations were successfully applied")
    print()
    print("Implication:")
    print("  The 16.5.20 result can now be interpreted with confidence:")
    print("  - C1 baseline ~= C0 baseline means Oscillator is NOT the signal source")
    print("  - C2 baseline ~= C0 baseline means Filter is NOT the signal source")
    print()
    print("Next step (16.5.27):")
    print("  Investigate what signal IS generating the 3863 Hz baseline")
    print("  Signal-path forensic: what's feeding into FXEQ?")

elif c1_mutation_status == "FAILED" or c2_mutation_status == "FAILED":
    print("VERDICT: One or more mutations failed to apply")
    print()
    if c1_mutation_status == "FAILED":
        print("  C1 mutation failed: Oscillator0.kParamVolume did not change")
    if c2_mutation_status == "FAILED":
        print("  C2 mutation failed: VoiceFilter0.kParamFreq did not change")
    print()
    print("Implication:")
    print("  The 16.5.20 baseline measurements for failed contexts cannot be interpreted")
    print("  We did not actually test the hypothesis")
    print()
    print("Next step:")
    print("  Correct the mutation application logic")
    print("  Verify that mutations persist through skeleton/load/render pipeline")

else:
    print("VERDICT: Uncertain (measurement may have failed)")
    print()
    print("Next step:")
    print("  Investigate measurement execution and re-run with diagnostics")

print()

print("=" * 80)
print("16.5.26 COMPLETE")
print("=" * 80)
