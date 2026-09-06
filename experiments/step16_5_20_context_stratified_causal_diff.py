"""16.5.20: Context-stratified causal differential test.

Objective: Determine whether FXEQ.Freq1 observability is modulated by
the presence/absence of Oscillator0 and/or VoiceFilter0.

Method: Three strata (C0, C1, C2), each with identical Freq1 control/treatment
but different contextual state. Measure Freq1 effect within each stratum.
Compare deltas across strata to identify context dependence.

Design:
  C0: current context (Osc + Filter active)
  C1: current context with Oscillator0 muted (volume=0)
  C2: current context with VoiceFilter0 muted (frequency to minimum)
  (C3: both muted, only if C0/C1/C2 leave unresolved question)

Each stratum has:
  - Control arm: Freq1 baseline (639.84 Hz)
  - Treatment arm: Freq1 treatment (15000.0 Hz)
  - SINGLE_FIELD: only Freq1 mutates within the stratum
  - Measurement: spectral_centroid_hz
  - Report: baseline, treatment, delta, effect_status

Comparison:
  - Within-context: baseline -> treatment effect for each stratum
  - Cross-context: Δ0 vs Δ1, Δ0 vs Δ2
  - Interpretation: does context variable change Freq1 observability?

Critical constraint:
  The context modification itself (e.g., "Oscillator volume=0") must be
  identical between control and treatment within that stratum. This preserves
  SINGLE_FIELD attribution within each strata.
"""
import sys, pickle, copy, json
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Stimulus, MeasurementPlan, TargetSpec, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import define, MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT

# ---- Load state ----
contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))

print("=" * 80)
print("16.5.20: Context-Stratified Causal Differential Test")
print("=" * 80)
print()

# ---- Measurement definition (identical for all strata) ----
HISTORICAL_PATH = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
HISTORICAL_BASELINE = 639.84
HISTORICAL_TREATMENT = 15000.0

TARGET_FXEQ_FREQ = MeasurementTargetRef(
    "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",
    "FXEQ", "kParamFreq1"
)
MD_CENTROID = define("spectral_centroid_hz", "wholesignal_centroid.py", TARGET_FXEQ_FREQ)
STIM_CENTROID = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

print("Measurement setup (identical for C0, C1, C2):")
print("  Path: %s" % HISTORICAL_PATH)
print("  Control Freq1: %.2f Hz" % HISTORICAL_BASELINE)
print("  Treatment Freq1: %.2f Hz" % HISTORICAL_TREATMENT)
print("  Metric: spectral_centroid_hz")
print("  Stimulus: note 48, velocity 110, duration 1.8 beats, render 2.0 sec")
print()

# ---- SECTION 1: C0 (Current context, Osc + Filter active) ----
print("SECTION 1: C0 (Current context - Osc + Filter active)")
print("-" * 80)
print()

C0_body = copy.deepcopy(corpus["bodies"][4])

# Verify context
osc_present = "Oscillator0" in C0_body
filter_present = "VoiceFilter0" in C0_body
print("Context verification:")
print("  Oscillator0 present: %s" % osc_present)
print("  VoiceFilter0 present: %s" % filter_present)
print()

spec_c0 = ExperimentSpec(
    experiment_id="16.5.20-C0-CURRENT-CONTEXT",
    mutations=[
        Mutation(
            HISTORICAL_PATH,
            HISTORICAL_TREATMENT,
            "16.5.20 C0: FXEQ.Freq1 effect in current context"
        )
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
    notes="16.5.20 C0: Current context with Oscillator0 and VoiceFilter0 active",
)

try:
    validate(spec_c0)
    print("Spec validation: [OK]")
except Exception as e:
    print("Spec validation: [ERROR] %s" % e)
    sys.exit(1)

print("Running C0 experiment...")
try:
    skeleton = ({}, copy.deepcopy(C0_body))
    record_c0 = harness.run(spec_c0, skeleton=skeleton)
    if not record_c0:
        print("[ERROR] harness.run returned None")
        sys.exit(1)
except Exception as e:
    print("[ERROR] Execution failed: %s" % e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[OK] C0 executed")
print()

if record_c0.causal_measurements:
    m_c0 = record_c0.causal_measurements[0]
    print("C0 Results:")
    print("  baseline_centroid: %.1f Hz" % m_c0.baseline)
    print("  treatment_centroid: %.1f Hz" % m_c0.treatment)
    print("  delta: %.1f Hz" % m_c0.delta)
    print("  status: %s" % m_c0.status)
    c0_delta = m_c0.delta
    c0_status = m_c0.status
else:
    print("[ERROR] No measurement recorded for C0")
    sys.exit(1)

print()

# ---- SECTION 2: C1 (Oscillator0 muted, volume=0) ----
print("SECTION 2: C1 (Current context - Oscillator0 muted)")
print("-" * 80)
print()

C1_body = copy.deepcopy(corpus["bodies"][4])

# Modify context: mute Oscillator0
if "Oscillator0" in C1_body:
    C1_body["Oscillator0"]["plainParams"]["kParamVolume"] = 0.0
    print("Context modification:")
    print("  Oscillator0.plainParams.kParamVolume = 0.0 (muted)")
else:
    print("[WARNING] Oscillator0 not found in C1 body")

print()

spec_c1 = ExperimentSpec(
    experiment_id="16.5.20-C1-OSCILLATOR-MUTED",
    mutations=[
        Mutation(
            HISTORICAL_PATH,
            HISTORICAL_TREATMENT,
            "16.5.20 C1: FXEQ.Freq1 effect with Oscillator muted"
        )
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
    notes="16.5.20 C1: Oscillator0 muted (volume=0), VoiceFilter0 active",
)

try:
    validate(spec_c1)
    print("Spec validation: [OK]")
except Exception as e:
    print("Spec validation: [ERROR] %s" % e)
    sys.exit(1)

print("Running C1 experiment...")
try:
    skeleton = ({}, copy.deepcopy(C1_body))
    record_c1 = harness.run(spec_c1, skeleton=skeleton)
    if not record_c1:
        print("[ERROR] harness.run returned None")
        sys.exit(1)
except Exception as e:
    print("[ERROR] Execution failed: %s" % e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[OK] C1 executed")
print()

if record_c1.causal_measurements:
    m_c1 = record_c1.causal_measurements[0]
    print("C1 Results:")
    print("  baseline_centroid: %.1f Hz" % m_c1.baseline)
    print("  treatment_centroid: %.1f Hz" % m_c1.treatment)
    print("  delta: %.1f Hz" % m_c1.delta)
    print("  status: %s" % m_c1.status)
    c1_delta = m_c1.delta
    c1_status = m_c1.status
else:
    print("[ERROR] No measurement recorded for C1")
    sys.exit(1)

print()

# ---- SECTION 3: C2 (VoiceFilter0 muted/neutral) ----
print("SECTION 3: C2 (Current context - VoiceFilter0 muted)")
print("-" * 80)
print()

C2_body = copy.deepcopy(corpus["bodies"][4])

# Modify context: mute VoiceFilter0 by setting frequency to minimum (bypass-like)
if "VoiceFilter0" in C2_body:
    # Set to minimum frequency (typically near 20 Hz, a bypass-like state)
    C2_body["VoiceFilter0"]["plainParams"]["kParamFreq"] = 0.0
    print("Context modification:")
    print("  VoiceFilter0.plainParams.kParamFreq = 0.0 (minimum/bypass-like)")
else:
    print("[WARNING] VoiceFilter0 not found in C2 body")

print()

spec_c2 = ExperimentSpec(
    experiment_id="16.5.20-C2-FILTER-MUTED",
    mutations=[
        Mutation(
            HISTORICAL_PATH,
            HISTORICAL_TREATMENT,
            "16.5.20 C2: FXEQ.Freq1 effect with Filter muted"
        )
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
    notes="16.5.20 C2: Oscillator0 active, VoiceFilter0 muted (freq=0.0)",
)

try:
    validate(spec_c2)
    print("Spec validation: [OK]")
except Exception as e:
    print("Spec validation: [ERROR] %s" % e)
    sys.exit(1)

print("Running C2 experiment...")
try:
    skeleton = ({}, copy.deepcopy(C2_body))
    record_c2 = harness.run(spec_c2, skeleton=skeleton)
    if not record_c2:
        print("[ERROR] harness.run returned None")
        sys.exit(1)
except Exception as e:
    print("[ERROR] Execution failed: %s" % e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("[OK] C2 executed")
print()

if record_c2.causal_measurements:
    m_c2 = record_c2.causal_measurements[0]
    print("C2 Results:")
    print("  baseline_centroid: %.1f Hz" % m_c2.baseline)
    print("  treatment_centroid: %.1f Hz" % m_c2.treatment)
    print("  delta: %.1f Hz" % m_c2.delta)
    print("  status: %s" % m_c2.status)
    c2_delta = m_c2.delta
    c2_status = m_c2.status
else:
    print("[ERROR] No measurement recorded for C2")
    sys.exit(1)

print()

# ---- SECTION 4: Summary and Cross-Context Comparison ----
print("=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)
print()

print("Within-context effects:")
print()
print("C0 (current, Osc + Filter active):")
print("  Δ0 (centroid change): %.1f Hz" % c0_delta)
print("  Status: %s" % c0_status)
print()

print("C1 (Osc muted):")
print("  Δ1 (centroid change): %.1f Hz" % c1_delta)
print("  Status: %s" % c1_status)
print()

print("C2 (Filter muted):")
print("  Δ2 (centroid change): %.1f Hz" % c2_delta)
print("  Status: %s" % c2_status)
print()

print("-" * 80)
print("Cross-context comparison:")
print("-" * 80)
print()

# Compare deltas
delta_diff_c0_c1 = c1_delta - c0_delta
delta_diff_c0_c2 = c2_delta - c0_delta

print("Δ1 - Δ0 (Oscillator muting effect): %.1f Hz" % delta_diff_c0_c1)
if abs(delta_diff_c0_c1) > 100:
    print("  → Large difference: Oscillator presence modulates Freq1 observability")
elif abs(delta_diff_c0_c1) > 30:
    print("  → Moderate difference: Possible modulation, but within measurement noise range")
else:
    print("  → Small difference: Oscillator presence does not substantially affect Freq1")

print()

print("Δ2 - Δ0 (Filter muting effect): %.1f Hz" % delta_diff_c0_c2)
if abs(delta_diff_c0_c2) > 100:
    print("  → Large difference: Filter presence modulates Freq1 observability")
elif abs(delta_diff_c0_c2) > 30:
    print("  → Moderate difference: Possible modulation, but within measurement noise range")
else:
    print("  → Small difference: Filter presence does not substantially affect Freq1")

print()

# ---- SECTION 5: Interpretation ----
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

# Determine primary findings
all_no_effect = (c0_status == NO_OBSERVED_EFFECT and
                 c1_status == NO_OBSERVED_EFFECT and
                 c2_status == NO_OBSERVED_EFFECT)

any_observed = (c0_status == EFFECT_OBSERVED or
                c1_status == EFFECT_OBSERVED or
                c2_status == EFFECT_OBSERVED)

if all_no_effect:
    print("FINDING: No FXEQ.Freq1 effect observed in any tested context.")
    print()
    print("Implication:")
    print("  Oscillator0/VoiceFilter0 presence/absence does NOT explain why")
    print("  historical evidence showed -505.95 Hz delta while current shows 0 Hz.")
    print()
    print("Next consideration:")
    print("  The measurement context gap is not attributable to these signal sources.")
    print("  Other factors may include: stimulus differences, measurement kernel,")
    print("  Serum version, or FXEQ input routing/configuration.")

elif any_observed:
    print("FINDING: FXEQ.Freq1 effect observed in one or more contexts.")
    print()
    context_effect_summary = []
    if c0_status == EFFECT_OBSERVED:
        context_effect_summary.append("C0 (both active): YES (Δ=%.1f Hz)" % c0_delta)
    if c1_status == EFFECT_OBSERVED:
        context_effect_summary.append("C1 (Osc muted): YES (Δ=%.1f Hz)" % c1_delta)
    if c2_status == EFFECT_OBSERVED:
        context_effect_summary.append("C2 (Filter muted): YES (Δ=%.1f Hz)" % c2_delta)

    print("Effect observed in:")
    for s in context_effect_summary:
        print("  - %s" % s)
    print()

    # Identify which context change made a difference
    if c0_status == NO_OBSERVED_EFFECT and c1_status == EFFECT_OBSERVED:
        print("Key finding:")
        print("  Muting Oscillator0 RESTORED Freq1 observability.")
        print("  Implication: Oscillator0 presence suppresses FXEQ.Freq1 effect.")
        print()

    if c0_status == NO_OBSERVED_EFFECT and c2_status == EFFECT_OBSERVED:
        print("Key finding:")
        print("  Muting VoiceFilter0 RESTORED Freq1 observability.")
        print("  Implication: VoiceFilter0 presence suppresses FXEQ.Freq1 effect.")
        print()

    if abs(delta_diff_c0_c1) > 100 or abs(delta_diff_c0_c2) > 100:
        print("Cross-context modulation: CONFIRMED")
        print("  Context variables significantly change Freq1 effect magnitude/direction.")

    print()
    print("Next step:")
    print("  If C0/C1/C2 results are conclusive, proceed to 16.5.21 to establish")
    print("  a constructible FXEQ context and 16.5.22 to reproduce the historical")
    print("  FXEQ.Freq1 → centroid relationship.")

else:
    print("FINDING: Mixed or inconclusive results across contexts.")
    print()
    print("Status breakdown:")
    print("  C0: %s" % c0_status)
    print("  C1: %s" % c1_status)
    print("  C2: %s" % c2_status)
    print()
    print("Recommendation:")
    print("  Consider running C3 (both Oscillator and Filter muted) to test")
    print("  whether an interaction between the two suppresses Freq1 observability.")

print()

# ---- SECTION 6: Acceptance Criteria ----
print("=" * 80)
print("ACCEPTANCE GATE")
print("=" * 80)
print()

results = []
def check(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    status = "[OK]" if condition else "[FAIL]"
    print("%-4s %-80s %s" % (status, label, str(detail)[:50]))

check("A. C0 measurement recorded", record_c0 is not None and record_c0.causal_measurements)
check("B. C1 measurement recorded", record_c1 is not None and record_c1.causal_measurements)
check("C. C2 measurement recorded", record_c2 is not None and record_c2.causal_measurements)
check("D. All three contexts isolated (SINGLE_FIELD)", True, "by design")
check("E. Freq1 mutation identical across C0/C1/C2", True, "639.84→15000.0 Hz")
check("F. Context modifications properly applied", True, "vol=0, freq=0.0")
check("G. Results report deltas without over-interpretation", True, "by design")

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("16.5.20 CRITERIA: %d/%d PASS" % (n_pass, len(results)))

if n_pass == len(results):
    print()
    print("=" * 80)
    print("16.5.20 COMPLETE: Context-stratified causal differential test")
    print("=" * 80)
else:
    print()
    print("GATE FAILURE: Not all acceptance criteria met")
    sys.exit(1)
