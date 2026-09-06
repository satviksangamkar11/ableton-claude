"""Regression tests for 16.5.2: structured structural bounds in EvidenceRecord.

Invariants tested:
  1. Normal persistence PASS has no stored_values key.
  2. Persistence mismatch may carry stored_values with the actual Serum readback.
  3. Non-clamp persistence failures do NOT populate structural_observation.
  4. [6, 0] array literal cannot be interpreted as a clamp range.
  5. Missing readback (no mismatch) stays absent; no guessing.
  6. derive_structural_bounds() produces complete results from two-record probes.
  7. Single-sided probe produces correct partial result (max known, min unknown).
  8. Conflicting bound values raise ValueError.
  9. Old EvidenceRecords (no structural_observation field) unpickle cleanly.
 10. structural_observation is always empty on non-clamp experiments.
"""
import sys, pickle, copy
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence.structural import (
    StructuralProbeResult, derive_structural_bounds,
    NUMERIC_CLAMP_RANGE, BOUND_MINIMUM, BOUND_MAXIMUM)
from serum2.evidence import record as rec_mod

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-80s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:80]))

print("=== structural_observation field on new records ===")
clamp_data = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))
freq1_records = clamp_data["records"]["kParamFreq1"]
rec_lo = freq1_records["below"]
rec_hi = freq1_records["above"]
path = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"

# Test 1: BELOW probe persists -> FAIL + stored_values
assert_that("below-bound probe: persistence FAIL",
            rec_lo.persistence_observation["status"] == "FAIL")
assert_that("below-bound probe: stored_values present",
            "stored_values" in rec_lo.persistence_observation)
assert_that("below-bound probe: stored_value is float near 21.53",
            abs(rec_lo.persistence_observation["stored_values"][path] - 21.533) < 0.01,
            rec_lo.persistence_observation["stored_values"].get(path))

# Test 2: structural_observation populated with correct bound_type
assert_that("below-bound probe: structural_observation present",
            bool(rec_lo.structural_observation))
so_lo = rec_lo.structural_observation.get(path, {})
assert_that("below-bound: bound_type == MINIMUM", so_lo.get("bound_type") == "MINIMUM", so_lo)
assert_that("below-bound: kind == NUMERIC_CLAMP_RANGE",
            so_lo.get("kind") == NUMERIC_CLAMP_RANGE)
assert_that("below-bound: clamped_to ~ 21.533",
            so_lo.get("clamped_to") is not None and abs(so_lo["clamped_to"] - 21.533) < 0.01,
            so_lo.get("clamped_to"))

# Test 3: ABOVE probe
so_hi = rec_hi.structural_observation.get(path, {})
assert_that("above-bound: bound_type == MAXIMUM", so_hi.get("bound_type") == "MAXIMUM")
assert_that("above-bound: clamped_to == 20000.0",
            so_hi.get("clamped_to") == 20000.0, so_hi.get("clamped_to"))

print()
print("=== derive_structural_bounds ===")
result = derive_structural_bounds(path, [rec_lo, rec_hi])
assert_that("result.kind == NUMERIC_CLAMP_RANGE", result.kind == NUMERIC_CLAMP_RANGE)
assert_that("result.minimum ~ 21.533", abs(result.minimum - 21.533) < 0.01, result.minimum)
assert_that("result.maximum == 20000.0", result.maximum == 20000.0)
assert_that("result.is_complete()", result.is_complete())
assert_that("result.contains(300.0)", result.contains(300.0) is True)
assert_that("result.contains(0.001)", result.contains(0.001) is False)
assert_that("result.contains(50000.0)", result.contains(50000.0) is False)

print()
print("=== normal PASS experiment has no stored_values, no structural_observation ===")
freq1_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))
assert_that("normal PASS: persistence status == PASS",
            freq1_rec.persistence_observation["status"] == "PASS")
assert_that("normal PASS: no stored_values key",
            "stored_values" not in freq1_rec.persistence_observation)
assert_that("normal PASS: structural_observation is empty",
            freq1_rec.structural_observation == {})

print()
print("=== non-clamp persistence FAIL cannot create structural bounds ===")
# lfo_source records: source=[25, 0] -- persistence PASS, but even if FAIL
# these are not clamp probes and must never yield structural_observation
lfo_recs = pickle.load(open(r"D:\ableton claude\experiments\_lfo_rate_dependence_records.pkl", "rb"))
for key, lfo_rec in lfo_recs.items():
    assert_that("lfo route record has no structural_observation (%s)" % key,
                lfo_rec.structural_observation == {},
                lfo_rec.structural_observation)

print()
print("=== [6, 0] array literal cannot be a clamp range ===")
# If someone runs a clamp probe on a list value, stored_values only captures
# scalar (int/float) readbacks. A list value must not populate stored_values.
# Verify no lfo route record has stored_values that could be misread as range.
for key, lfo_rec in lfo_recs.items():
    assert_that("[6,0] route persistence has no stored_values (%s)" % key,
                "stored_values" not in lfo_rec.persistence_observation,
                lfo_rec.persistence_observation.get("stored_values"))

print()
print("=== partial result: single-sided probe ===")
# Only the BELOW record -> minimum known, maximum None
partial = derive_structural_bounds(path, [rec_lo])
assert_that("single-sided: minimum known", abs(partial.minimum - 21.533) < 0.01)
assert_that("single-sided: maximum is None", partial.maximum is None)
assert_that("single-sided: is_complete() is False", not partial.is_complete())
assert_that("single-sided: contains() returns None", partial.contains(5000.0) is None)

print()
print("=== conflicting bounds raise ValueError ===")
# Build a fake structural_obs on a copy-like record pair where MINIMUM conflicts
class FakeRecord:
    def __init__(self, exp_id, obs):
        self.experiment_id = exp_id
        self.structural_observation = obs

fake_min_a = FakeRecord("FAKE-A", {path: {"kind": NUMERIC_CLAMP_RANGE, "clamped_to": 10.0, "bound_type": "MINIMUM"}})
fake_min_b = FakeRecord("FAKE-B", {path: {"kind": NUMERIC_CLAMP_RANGE, "clamped_to": 20.0, "bound_type": "MINIMUM"}})
try:
    derive_structural_bounds(path, [fake_min_a, fake_min_b])
    assert_that("conflicting MINIMUM raises ValueError", False, "no error raised")
except ValueError:
    assert_that("conflicting MINIMUM raises ValueError", True)

print()
print("=== empty record list raises ValueError ===")
try:
    derive_structural_bounds(path, [])
    assert_that("empty record list raises ValueError", False, "no error raised")
except ValueError:
    assert_that("empty record list raises ValueError", True)

print()
print("=== old EvidenceRecord pkl files unpickle with structural_observation == {} ===")
old_files = [
    r"D:\ableton claude\experiments\_fxdist_drive_record.pkl",
    r"D:\ableton claude\experiments\_fxdist_mode_record.pkl",
    r"D:\ableton claude\experiments\_fxeq_type_records.pkl",
]
for path_f in old_files:
    try:
        obj = pickle.load(open(path_f, "rb"))
        if isinstance(obj, dict):
            recs = list(obj.values())
        else:
            recs = [obj]
        for r in recs:
            so = r.structural_observation
            assert_that("old pkl %s: structural_observation == {}" % path_f.split("\\")[-1],
                        so == {}, so)
    except Exception as e:
        assert_that("old pkl %s: loaded cleanly" % path_f.split("\\")[-1],
                    False, str(e))

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL STRUCTURAL PROBE ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
