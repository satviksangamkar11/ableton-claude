"""16.5.2.3/4: Re-run the 7 FXEQ clamp probes with probe_semantics="NUMERIC_CLAMP_RANGE".

For each field, two probes are run:
  BELOW: a value well below the expected lower boundary -> Serum clamps UP to minimum
  ABOVE: a value well above the expected upper boundary -> Serum clamps DOWN to maximum

Both arms use persistence_observation.stored_values to capture the clamped readback.
structural_observation is populated by the harness (not by hand) and carries
the typed bound (clamped_to, bound_type). derive_structural_bounds() then combines
the two records into a StructuralProbeResult.

Source of truth: Serum readback values, not prose. Provenance strings remain
explanatory only.
"""
import sys, pickle, copy
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import ExperimentSpec, Mutation, SINGLE_FIELD
from serum2.evidence.structural import derive_structural_bounds, StructuralProbeResult

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]

SHARED_CTX = Mutation("FXRack0", fxrack0, "shared corpus FXRack0 context")

# field_key: (param_path_suffix, probe_below, probe_above)
FIELDS = {
    "kParamFreq1":    ("FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",   0.001,    50000.0),
    "kParamFreq2":    ("FXRack0.FX.1.FXEQ.plainParams.kParamFreq2",   0.001,    50000.0),
    "kParamReso1":    ("FXRack0.FX.1.FXEQ.plainParams.kParamReso1",   -100.0,   200.0),
    "kParamReso2":    ("FXRack0.FX.1.FXEQ.plainParams.kParamReso2",   -100.0,   200.0),
    "kParamGain1":    ("FXRack0.FX.1.FXEQ.plainParams.kParamGain1",   -100.0,   100.0),
    "kParamGain2":    ("FXRack0.FX.1.FXEQ.plainParams.kParamGain2",   -100.0,   100.0),
    "kParamLevelOut": ("FXRack0.FX.1.FXEQ.plainParams.kParamLevelOut", -5.0,     5.0),
}

def make_clamp_spec(exp_id, path, probe_val):
    return ExperimentSpec(
        experiment_id=exp_id,
        mutations=[Mutation(path, probe_val,
                            "clamp boundary probe: expected to be rejected/clamped by Serum")],
        prerequisites=[],
        baseline_overrides=[SHARED_CTX],
        isolation_level=SINGLE_FIELD,
        claim_subject="structural_probe",
        claim_predicate="clamp_boundary",
        measurement_plans=[],
        probe_semantics="NUMERIC_CLAMP_RANGE",
    )

results = {}   # field_key -> StructuralProbeResult
all_records = {}

print("=== 16.5.2 FXEQ Clamp Probes (structured) ===")
print()
for field_key, (path, probe_below, probe_above) in FIELDS.items():
    print("--- %s ---" % field_key)
    rec_below = harness.run(make_clamp_spec(
        "CLAMP-%s-LO" % field_key, path, probe_below))
    rec_above = harness.run(make_clamp_spec(
        "CLAMP-%s-HI" % field_key, path, probe_above))

    so_below = rec_below.structural_observation.get(path, {})
    so_above = rec_above.structural_observation.get(path, {})

    print("  BELOW probe=%.4f  clamped_to=%s  bound_type=%s" % (
        probe_below,
        so_below.get("clamped_to", "NO_MISMATCH"),
        so_below.get("bound_type", "n/a")))
    print("  ABOVE probe=%.4f  clamped_to=%s  bound_type=%s" % (
        probe_above,
        so_above.get("clamped_to", "NO_MISMATCH"),
        so_above.get("bound_type", "n/a")))

    try:
        result = derive_structural_bounds(path, [rec_below, rec_above])
        results[field_key] = result
        all_records[field_key] = {"below": rec_below, "above": rec_above}
        print("  -> StructuralProbeResult: min=%.6f max=%.6f complete=%s"
              % (result.minimum, result.maximum, result.is_complete()))
    except ValueError as e:
        print("  -> DERIVATION FAILED: %s" % e)

    print()

print("=== Summary ===")
for field_key, result in results.items():
    status = "COMPLETE" if result.is_complete() else "PARTIAL"
    print("  %-20s min=%-12s max=%-12s [%s]" % (
        field_key,
        ("%.6f" % result.minimum) if result.minimum is not None else "UNKNOWN",
        ("%.6f" % result.maximum) if result.maximum is not None else "UNKNOWN",
        status))

print()
# Cross-check against old prose values (not source of truth -- verification only)
KNOWN_FROM_PROSE = {
    "kParamFreq1":    (21.533, 20000.0),
    "kParamFreq2":    (21.533, 20000.0),
    "kParamReso1":    (0.0, 100.0),
    "kParamReso2":    (0.0, 100.0),
    "kParamGain1":    (-24.0, 24.0),
    "kParamGain2":    (-24.0, 24.0),
    "kParamLevelOut": (0.0, 1.0),
}
print("=== Cross-check vs old prose bounds (VERIFICATION ONLY, not source of truth) ===")
all_agree = True
for field_key, (prose_min, prose_max) in KNOWN_FROM_PROSE.items():
    result = results.get(field_key)
    if result is None:
        print("  %-20s MISSING from new probes" % field_key)
        all_agree = False
        continue
    min_ok = result.minimum is not None and abs(result.minimum - prose_min) < 0.01
    max_ok = result.maximum is not None and abs(result.maximum - prose_max) < 0.01
    status = "AGREE" if (min_ok and max_ok) else "DISAGREE"
    if status == "DISAGREE":
        all_agree = False
    print("  %-20s prose=[%.3f,%.3f] new=[%s,%s] -> %s" % (
        field_key, prose_min, prose_max,
        ("%.3f" % result.minimum) if result.minimum is not None else "?",
        ("%.3f" % result.maximum) if result.maximum is not None else "?",
        status))

print()
if all_agree:
    print("All 7 fields: new structured bounds agree with old prose values.")
else:
    print("DISAGREEMENT -- investigate before using new bounds.")

pickle.dump({
    "results": results,
    "records": all_records,
}, open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "wb"))
print()
print("Saved to _fxeq_clamp_probes_structured.pkl")
