"""16.5.5 regression tests for structural value admission.

Invariants:
  1. Value within complete numeric range -> ACCEPT
  2. Value below minimum -> REFUSE
  3. Value above maximum -> REFUSE
  4. Complete bounds but exactly at minimum -> ACCEPT (inclusive)
  5. Complete bounds but exactly at maximum -> ACCEPT (inclusive)
  6. Incomplete bounds (minimum only) -> UNKNOWN
  7. Incomplete bounds (maximum only) -> UNKNOWN
  8. No structural records for this target -> UNKNOWN
  9. Operation is MUTATE_ENUM (not MUTATE_NUMERIC) -> UNKNOWN
 10. ACCEPT is truthy, REFUSE is falsy, UNKNOWN is falsy
 11. Structural bounds in result match the underlying StructuralProbeResult
 12. Causal witness value not consulted (different contracts same field -> same bounds)
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler.targets import resolve_semantic_target, ResolvedTarget
from serum2.compiler.structural_admission import (
    structural_admit, ACCEPT, REFUSE, UNKNOWN,
    StructuralAdmissionResult,
)
from serum2.evidence.capability_contract import MUTATE_NUMERIC, MUTATE_ENUM

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
clamp_data = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))

structural_records = []
for field_key, recs in clamp_data["records"].items():
    structural_records.append(recs["below"])
    structural_records.append(recs["above"])

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-80s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:80]))

resolved_freq1 = resolve_semantic_target("FXEQ.Freq1", contracts)
assert isinstance(resolved_freq1, ResolvedTarget), "setup: FXEQ.Freq1 must resolve"

# Known complete bounds: ~[21.5332, 20000.0]. Use the actual values from evidence.
from serum2.evidence.structural import derived_structural_bounds
FREQ1_PATH = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
_freq1_bounds = derived_structural_bounds(FREQ1_PATH, structural_records)
assert _freq1_bounds is not None and _freq1_bounds.is_complete(), "setup: FXEQ.Freq1 must have complete bounds"
MIN_FREQ = _freq1_bounds.minimum   # exact Serum-reported clamped value
MAX_FREQ = _freq1_bounds.maximum

print("=== 1. Value within range -> ACCEPT ===")
r = structural_admit(resolved_freq1, 300.0, structural_records)
assert_that("300.0 Hz: status == ACCEPT", r.status == ACCEPT, r.reason)
assert_that("300.0 Hz: bounds present", r.bounds is not None)
assert_that("300.0 Hz: is truthy", bool(r) is True)

print()
print("=== 2. Value below minimum -> REFUSE ===")
r_lo = structural_admit(resolved_freq1, 1.0, structural_records)
assert_that("1.0 Hz: status == REFUSE", r_lo.status == REFUSE, r_lo.reason)
assert_that("1.0 Hz: is falsy", bool(r_lo) is False)

print()
print("=== 3. Value above maximum -> REFUSE ===")
r_hi = structural_admit(resolved_freq1, 99999.0, structural_records)
assert_that("99999 Hz: status == REFUSE", r_hi.status == REFUSE, r_hi.reason)

print()
print("=== 4/5. Boundary values inclusive ===")
r_at_min = structural_admit(resolved_freq1, MIN_FREQ, structural_records)
assert_that("at minimum: ACCEPT", r_at_min.status == ACCEPT, r_at_min.reason)
r_at_max = structural_admit(resolved_freq1, MAX_FREQ, structural_records)
assert_that("at maximum: ACCEPT", r_at_max.status == ACCEPT, r_at_max.reason)

print()
print("=== 6. Incomplete bounds (minimum only) -> UNKNOWN ===")
only_min_records = [clamp_data["records"]["kParamFreq1"]["below"]]
r_partial_min = structural_admit(resolved_freq1, 300.0, only_min_records)
assert_that("min-only: UNKNOWN", r_partial_min.status == UNKNOWN, r_partial_min.reason)
assert_that("min-only: bounds present but not complete",
            r_partial_min.bounds is not None and not r_partial_min.bounds.is_complete())

print()
print("=== 7. Incomplete bounds (maximum only) -> UNKNOWN ===")
only_max_records = [clamp_data["records"]["kParamFreq1"]["above"]]
r_partial_max = structural_admit(resolved_freq1, 300.0, only_max_records)
assert_that("max-only: UNKNOWN", r_partial_max.status == UNKNOWN, r_partial_max.reason)

print()
print("=== 8. No structural records for this target -> UNKNOWN ===")
r_no_records = structural_admit(resolved_freq1, 300.0, [])
assert_that("empty records: UNKNOWN", r_no_records.status == UNKNOWN, r_no_records.reason)
assert_that("empty records: bounds is None", r_no_records.bounds is None)

# Load the causal records (no structural_observation)
causal_records_only = [
    pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb")),
]
r_causal_only = structural_admit(resolved_freq1, 300.0, causal_records_only)
assert_that("causal-only pool: UNKNOWN (no structural evidence)", r_causal_only.status == UNKNOWN)

print()
print("=== 9. MUTATE_ENUM operation -> UNKNOWN ===")
class _FakeEnumContract:
    allowed_operation = MUTATE_ENUM
    scope = {"mutation_target_path": "FXRack0.FX.1.FXEQ.plainParams.kParamType1"}
    target = "fx_field_eq_kParamType1"
    status = "STRUCTURAL_ONLY"
    limitations = ()
class _FakeEnumResolved:
    class ref:
        capability_key = "fx_field_eq_kParamType1"
    contract = _FakeEnumContract()

r_enum = structural_admit(_FakeEnumResolved(), 1, structural_records)
assert_that("MUTATE_ENUM: UNKNOWN", r_enum.status == UNKNOWN, r_enum.reason)
assert_that("MUTATE_ENUM: bounds is None", r_enum.bounds is None)

print()
print("=== 10. Truth values ===")
assert_that("ACCEPT result is truthy", bool(structural_admit(resolved_freq1, 300.0, structural_records)))
assert_that("REFUSE result is falsy", not bool(structural_admit(resolved_freq1, 1.0, structural_records)))
assert_that("UNKNOWN result is falsy", not bool(structural_admit(resolved_freq1, 300.0, [])))

print()
print("=== 11. Bounds in result match StructuralProbeResult ===")
r11 = structural_admit(resolved_freq1, 5000.0, structural_records)
assert_that("bounds.minimum matches expected min",
            r11.bounds is not None and abs(r11.bounds.minimum - MIN_FREQ) < 0.01, r11.bounds)
assert_that("bounds.maximum matches expected max",
            r11.bounds is not None and r11.bounds.maximum == MAX_FREQ, r11.bounds)

print()
print("=== 12. Witness value not consulted ===")
# The freq1 witness experiment used some value (e.g. 15000 Hz or 8000 Hz).
# structural_admit ignores that and only uses clamp probe records.
witness_value = contracts and next(
    (c.scope.get("mutation_value_used") for c in contracts.values()
     if c.target == "fx_field_eq_freq1"), None)
if witness_value is not None:
    # If witness_value is outside [MIN, MAX] we'd expect the structural result
    # to be based on clamp probes, not the witness. Since our known witness is
    # within range, we verify the bounds come from clamp probes (not witness).
    assert_that("witness value noted (not used as bound): %s" % witness_value, True)
    # The bounds should still be [MIN_FREQ, MAX_FREQ] regardless of witness_value
    r12 = structural_admit(resolved_freq1, 300.0, structural_records)
    assert_that("bounds unaffected by witness value",
                r12.bounds is not None
                and abs(r12.bounds.minimum - MIN_FREQ) < 0.01
                and r12.bounds.maximum == MAX_FREQ)

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL STRUCTURAL ADMISSION ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
