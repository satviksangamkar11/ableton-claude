"""16.5.30: Persistence Discrepancy Audit.

Objective: Resolve the conflict between:
  - 16.5.29: Oscillator0.Volume=0.0 mutation showed persistence FAIL
  - Prior evidence: Oscillator Volume changes have been causally verified
    (implying persistence worked in that earlier case)

Correction from 16.5.29: The prior script incorrectly split control/treatment
into two separate harness.run() calls, with an invalid empty-mutation
"control" spec. harness.run() already produces both arms internally from
ONE ExperimentSpec. This experiment fixes that construction error.

Method:
  1. Search capability_contracts for prior Oscillator Volume evidence
  2. Extract exact historical tested value, persistence status, causal result
  3. Re-run a CORRECTLY constructed single-spec experiment:
     Oscillator0.Volume: current -> 0.0
  4. Compare persistence outcome against prior evidence
  5. Determine: value-specific (0.0 boundary) / path-specific / regression / experiment-error

No infrastructure changes. No FXEQ work. Pure discrepancy resolution.
"""
import sys, pickle, copy
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Stimulus, MeasurementPlan, TargetSpec, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import define, MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT

print("=" * 80)
print("16.5.30: Persistence Discrepancy Audit")
print("=" * 80)
print()

# ---- SECTION 1: Locate prior Oscillator Volume evidence ----
print("SECTION 1: Prior Oscillator Volume Evidence Search")
print("-" * 80)
print()

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

osc_contract = None
for target, c in contracts.items():
    if "osc" in str(target).lower() and "vol" in str(target).lower():
        osc_contract = c
        print("OBSERVED - Found candidate contract: %s" % (target,))
        break

if osc_contract is None:
    # Broaden search
    print("No exact 'osc...vol' match. Listing all contract targets containing 'osc':")
    for target in contracts.keys():
        if "osc" in str(target).lower():
            print("  %s" % (target,))
    print()
    print("Listing all contract targets containing 'vol':")
    for target in contracts.keys():
        if "vol" in str(target).lower():
            print("  %s" % (target,))
    print()

if osc_contract:
    print()
    print("OBSERVED - Contract details:")
    print("  target:      %s" % (osc_contract.target,))
    print("  status:      %s" % osc_contract.status)
    m = osc_contract.measurement or {}
    print("  metric:      %s" % m.get("metric"))
    print("  baseline:    %s" % m.get("baseline"))
    print("  treatment:   %s" % m.get("treatment"))
    print("  delta:       %s" % m.get("delta"))
    print("  status:      %s" % m.get("status"))
    print()
    print("  scope:")
    for k, v in (osc_contract.scope or {}).items():
        print("    %s: %s" % (k, v))
    print()

    hist_osc_treatment_value = osc_contract.scope.get("mutation_value_used")
else:
    print("No Oscillator Volume contract found by name search.")
    hist_osc_treatment_value = None

print()

# ---- SECTION 2: List ALL contracts for reference ----
print("SECTION 2: Full Contract Inventory (for context)")
print("-" * 80)
print()
print("All capability contract targets:")
for target in sorted(contracts.keys(), key=str):
    print("  %s (status=%s)" % (str(target), contracts[target].status))
print()

# ---- SECTION 3: Correctly constructed experiment ----
print("SECTION 3: Corrected Single-Spec Experiment")
print("-" * 80)
print()
print("Correction from 16.5.29: ONE ExperimentSpec, ONE mutation.")
print("harness.run() internally builds BOTH control (apply_mutations=False)")
print("AND treatment (apply_mutations=True) arms from this single spec.")
print()

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]

current_volume = body_base.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
print("OBSERVED - Current Oscillator0.kParamVolume: %.4f" % current_volume)
print()

if hist_osc_treatment_value is not None:
    print("OBSERVED - Prior historical treatment value tested: %.4f" % hist_osc_treatment_value)
    if abs(hist_osc_treatment_value - 0.0) < 1e-6:
        print("  Prior test ALSO used 0.0 -- discrepancy is NOT value-specific to 0.0")
    else:
        print("  Prior test used a DIFFERENT value than 0.0 -- 0.0 may be a boundary case")
    test_value = hist_osc_treatment_value
else:
    print("No prior treatment value found. Will test BOTH 0.0 and a mid-range value.")
    test_value = None

print()

TARGET_FXEQ = MeasurementTargetRef(
    "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",
    "FXEQ", "kParamFreq1"
)
STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)


def run_single_spec_test(treatment_value, label):
    print("Test: Oscillator0.Volume %.4f -> %.4f (%s)" % (current_volume, treatment_value, label))
    body = copy.deepcopy(body_base)

    spec = ExperimentSpec(
        experiment_id="16.5.30-OSC-VOLUME-%s" % label.upper().replace(" ", "-"),
        mutations=[
            Mutation(
                "Oscillator0.plainParams.kParamVolume",
                treatment_value,
                "16.5.30: %s persistence/causal test" % label
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
        notes="16.5.30: %s (single-spec, both arms from one harness.run())" % label,
    )

    try:
        validate(spec)
        print("  [OK] Spec validated (single mutation, SINGLE_FIELD)")
    except Exception as e:
        print("  [ERROR] Validation failed: %s" % e)
        return None

    try:
        skeleton = ({}, copy.deepcopy(body))
        record = harness.run(spec, skeleton=skeleton)
        if not record or not record.causal_measurements:
            print("  [ERROR] No measurement recorded")
            return None
        m = record.causal_measurements[0]
        print("  [OK] Executed. baseline=%.1f Hz, treatment=%.1f Hz, delta=%.1f Hz, status=%s" %
              (m.baseline, m.treatment, m.delta, m.status))

        persist = record.persistence_observation
        print("  Persistence: status=%s exact_match=%s" %
              (persist.get("status"), persist.get("exact_match")))
        if persist.get("detail"):
            print("    detail: %s" % persist.get("detail"))
        if persist.get("stored_values"):
            print("    stored_values (actual Serum readback on mismatch): %s" % persist.get("stored_values"))

        state_obs = record.state_observation
        print("  State-diff check: matches_intent=%s top_level_ok=%s fine_grained_ok=%s" %
              (state_obs.get("matches_intent"), state_obs.get("top_level_ok"), state_obs.get("fine_grained_ok")))

        return {
            "baseline": m.baseline, "treatment": m.treatment, "delta": m.delta,
            "status": m.status, "persistence": persist, "state_obs": state_obs,
        }
    except Exception as e:
        print("  [ERROR] Execution failed: %s" % e)
        import traceback
        traceback.print_exc()
        return None


print()
result_zero = run_single_spec_test(0.0, "volume zero")
print()

result_hist = None
if test_value is not None and abs(test_value - 0.0) > 1e-6:
    result_hist = run_single_spec_test(test_value, "historical value")
    print()
elif test_value is None:
    result_hist = run_single_spec_test(0.05, "mid-range probe")
    print()

# ---- SECTION 4: Comparison and Verdict ----
print("=" * 80)
print("SECTION 4: Discrepancy Resolution")
print("=" * 80)
print()

print("16.5.29 (malformed experiment) reported:")
print("  Persistence: FAIL, detail={'Oscillator0.plainParams.kParamVolume': False}")
print("  BUT: this came from a two-spec construction with an invalid empty-mutation")
print("       control arm -- NOT a valid harness.run() execution pattern.")
print()

print("16.5.30 (corrected single-spec) result for Volume=0.0:")
if result_zero:
    p = result_zero["persistence"]
    print("  Persistence: %s, exact_match=%s" % (p.get("status"), p.get("exact_match")))
    print("  Causal: baseline=%.1f Hz treatment=%.1f Hz delta=%.1f Hz status=%s" %
          (result_zero["baseline"], result_zero["treatment"], result_zero["delta"], result_zero["status"]))
else:
    print("  Execution failed -- see errors above")

print()

if result_hist:
    label = "historical value (%.4f)" % test_value if test_value is not None else "mid-range probe (0.05)"
    print("16.5.30 result for %s:" % label)
    p = result_hist["persistence"]
    print("  Persistence: %s, exact_match=%s" % (p.get("status"), p.get("exact_match")))
    print("  Causal: baseline=%.1f Hz treatment=%.1f Hz delta=%.1f Hz status=%s" %
          (result_hist["baseline"], result_hist["treatment"], result_hist["delta"], result_hist["status"]))
    print()

# ---- Verdict logic ----
print("-" * 80)
print("VERDICT")
print("-" * 80)
print()

if result_zero is None:
    print("Cannot resolve -- corrected experiment failed to execute.")
    verdict = "UNRESOLVED_EXECUTION_ERROR"
else:
    zero_persist_fail = (result_zero["persistence"].get("status") != "PASS")

    if not zero_persist_fail:
        print("With CORRECT single-spec construction, Volume=0.0 persistence PASSES.")
        print("=> 16.5.29's FAIL was an artifact of the malformed two-spec experiment,")
        print("   NOT evidence of a broken state-application pipeline.")
        verdict = "EXPERIMENT_ERROR_NOT_INFRASTRUCTURE"
    else:
        print("With CORRECT single-spec construction, Volume=0.0 STILL shows persistence FAIL.")
        if result_hist and result_hist["persistence"].get("status") == "PASS":
            print("=> But the alternate test value PASSES persistence.")
            print("=> This is VALUE-SPECIFIC: 0.0 is likely a boundary/clamp/default-drop case,")
            print("   not a general pipeline defect.")
            verdict = "VALUE_SPECIFIC_BOUNDARY"
        elif result_hist and result_hist["persistence"].get("status") != "PASS":
            print("=> The alternate value ALSO fails persistence.")
            print("=> This is NOT value-specific to 0.0 -- broader discrepancy confirmed.")
            print("=> Warrants further audit of path/skeleton/harness before declaring")
            print("   infrastructure broken -- but this is real signal, not artifact.")
            verdict = "CONFIRMED_DISCREPANCY_NOT_VALUE_SPECIFIC"
        else:
            print("=> No comparison value available to disambiguate.")
            print("=> Persistence FAIL for 0.0 persists even under correct construction.")
            print("=> Recommend testing additional non-zero values before any infra conclusion.")
            verdict = "PERSISTS_UNDER_CORRECTION_NEEDS_MORE_VALUES"

print()
print("=" * 80)
print("16.5.30 COMPLETE")
print("=" * 80)
print()
print("Verdict: %s" % verdict)
print()
print("Explicit non-conclusion:")
print("  This audit does NOT declare the state-application pipeline broken or working.")
print("  It isolates whether 16.5.29's FAIL was an experiment-construction artifact,")
print("  a value-specific boundary behavior, or a reproducible discrepancy.")
