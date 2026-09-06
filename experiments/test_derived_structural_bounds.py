"""16.5.3 regression tests for derived_structural_bounds().

Invariants:
  1. All 7 FXEQ fields: complete StructuralProbeResult from structured probe records.
  2. FXDistortion.Drive (no structural probes run): returns None.
  3. Lower bound present, upper absent: partial result, maximum is None.
  4. Upper bound present, lower absent: partial result, minimum is None.
  5. Causal EvidenceRecord in the pool: does NOT affect structural bounds.
  6. Mixed pool (structural + causal + persistence-only): result identical to structural-only.
  7. No structural observations in any record: returns None (not ValueError).
  8. Conflicting MINIMUM values: raises ValueError (same as low-level).
  9. target_path with no matching records in pool: returns None.
 10. StructuralProbeResult.contains() invariants for known-complete fields.
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence.structural import (derived_structural_bounds,
                                         NUMERIC_CLAMP_RANGE)

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-80s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:80]))

# ---- load evidence pools ----
clamp_data = pickle.load(
    open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))
structural_records = []
for field_key, recs in clamp_data["records"].items():
    structural_records.append(recs["below"])
    structural_records.append(recs["above"])

causal_records = [
    pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb")),
    pickle.load(open(r"D:\ableton claude\experiments\_fxdist_drive_record.pkl", "rb")),
    pickle.load(open(r"D:\ableton claude\experiments\_fxdist_mode_record.pkl", "rb")),
]
lfo_recs = pickle.load(
    open(r"D:\ableton claude\experiments\_lfo_rate_dependence_records.pkl", "rb"))
causal_records += list(lfo_recs.values())

mixed_pool = structural_records + causal_records

FREQ1_PATH  = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
FREQ2_PATH  = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq2"
RESO1_PATH  = "FXRack0.FX.1.FXEQ.plainParams.kParamReso1"
RESO2_PATH  = "FXRack0.FX.1.FXEQ.plainParams.kParamReso2"
GAIN1_PATH  = "FXRack0.FX.1.FXEQ.plainParams.kParamGain1"
GAIN2_PATH  = "FXRack0.FX.1.FXEQ.plainParams.kParamGain2"
LVLOUT_PATH = "FXRack0.FX.1.FXEQ.plainParams.kParamLevelOut"
DRIVE_PATH  = "FXRack0.FX.2.FXDistortion.plainParams.kParamDrive"

EXPECTED = {
    FREQ1_PATH:  (21.533201, 20000.0),
    FREQ2_PATH:  (21.533201, 20000.0),
    RESO1_PATH:  (0.0, 100.0),
    RESO2_PATH:  (0.0, 100.0),
    GAIN1_PATH:  (-24.0, 24.0),
    GAIN2_PATH:  (-24.0, 24.0),
    LVLOUT_PATH: (0.0, 1.0),
}

print("=== test 1: all 7 FXEQ fields complete from structural pool ===")
for path, (exp_min, exp_max) in EXPECTED.items():
    r = derived_structural_bounds(path, structural_records)
    assert_that("%-40s not None" % path, r is not None)
    assert_that("%-40s kind == NUMERIC_CLAMP_RANGE" % path,
                r is not None and r.kind == NUMERIC_CLAMP_RANGE)
    assert_that("%-40s minimum ~ %.4f" % (path, exp_min),
                r is not None and r.minimum is not None and abs(r.minimum - exp_min) < 0.01,
                r.minimum if r else None)
    assert_that("%-40s maximum == %.1f" % (path, exp_max),
                r is not None and r.maximum == exp_max)
    assert_that("%-40s is_complete()" % path, r is not None and r.is_complete())

print()
print("=== test 2: FXDistortion.Drive returns None (no structural probes) ===")
r_drive = derived_structural_bounds(DRIVE_PATH, structural_records)
assert_that("Drive: returns None", r_drive is None)

print()
print("=== test 3/4: one-sided probes produce partial result ===")
# Only the MINIMUM record for FREQ1
only_min = [clamp_data["records"]["kParamFreq1"]["below"]]
r_min_only = derived_structural_bounds(FREQ1_PATH, only_min)
assert_that("min-only: result not None", r_min_only is not None)
assert_that("min-only: minimum set", r_min_only is not None and r_min_only.minimum is not None)
assert_that("min-only: maximum is None", r_min_only is not None and r_min_only.maximum is None)
assert_that("min-only: is_complete() False", r_min_only is not None and not r_min_only.is_complete())
assert_that("min-only: contains() returns None", r_min_only is not None and r_min_only.contains(5000.0) is None)

only_max = [clamp_data["records"]["kParamFreq1"]["above"]]
r_max_only = derived_structural_bounds(FREQ1_PATH, only_max)
assert_that("max-only: result not None", r_max_only is not None)
assert_that("max-only: minimum is None", r_max_only is not None and r_max_only.minimum is None)
assert_that("max-only: maximum set", r_max_only is not None and r_max_only.maximum == 20000.0)

print()
print("=== test 5/6: causal records in pool do not affect result ===")
r_mixed = derived_structural_bounds(FREQ1_PATH, mixed_pool)
r_struct_only = derived_structural_bounds(FREQ1_PATH, structural_records)
assert_that("mixed pool: result not None", r_mixed is not None)
assert_that("mixed == structural-only: minimum",
            r_mixed is not None and r_struct_only is not None
            and r_mixed.minimum == r_struct_only.minimum)
assert_that("mixed == structural-only: maximum",
            r_mixed is not None and r_struct_only is not None
            and r_mixed.maximum == r_struct_only.maximum)

# Specifically: causal-only records yield None for FREQ1_PATH
r_causal_only = derived_structural_bounds(FREQ1_PATH, causal_records)
assert_that("causal-only pool for structural target: returns None", r_causal_only is None)

print()
print("=== test 7: no matching records -> None, not ValueError ===")
r_nobody = derived_structural_bounds("Nonexistent.path", mixed_pool)
assert_that("unknown path: returns None", r_nobody is None)
r_empty = derived_structural_bounds(FREQ1_PATH, [])
assert_that("empty pool: returns None", r_empty is None)

print()
print("=== test 8: conflicting MINIMUM raises ValueError ===")
class FakeRecord:
    def __init__(self, eid, obs):
        self.experiment_id = eid
        self.structural_observation = obs

path = FREQ1_PATH
fake_a = FakeRecord("FA", {path: {"kind": NUMERIC_CLAMP_RANGE,
                                   "clamped_to": 10.0, "bound_type": "MINIMUM"}})
fake_b = FakeRecord("FB", {path: {"kind": NUMERIC_CLAMP_RANGE,
                                   "clamped_to": 30.0, "bound_type": "MINIMUM"}})
try:
    derived_structural_bounds(path, [fake_a, fake_b])
    assert_that("conflicting MINIMUM raises ValueError", False)
except ValueError:
    assert_that("conflicting MINIMUM raises ValueError", True)

print()
print("=== test 9: Drive not present in mixed pool ===")
r_drive_mixed = derived_structural_bounds(DRIVE_PATH, mixed_pool)
assert_that("Drive in mixed pool: None", r_drive_mixed is None)

print()
print("=== test 10: contains() for all complete fields ===")
for path, (exp_min, exp_max) in EXPECTED.items():
    r = derived_structural_bounds(path, structural_records)
    mid = (exp_min + exp_max) / 2.0
    assert_that("%-42s contains(midpoint)" % path, r is not None and r.contains(mid) is True)
    assert_that("%-42s not contains(max+1)" % path,
                r is not None and r.contains(exp_max + 1.0) is False)
    if exp_min > 0:
        assert_that("%-42s not contains(min-1)" % path,
                    r is not None and r.contains(exp_min - 1.0) is False)

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL DERIVED STRUCTURAL BOUNDS ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
