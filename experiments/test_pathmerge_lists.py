"""Mandatory proof test for list-index path support + the directional,
operation-aware conflict rule. Not optional -- this is the isolation
guarantee for any future experiment reaching into a list (FX racks, ModSlot
arrays accessed by path, etc.), so it gets its own regression coverage."""
import sys, copy
sys.path.insert(0, r"D:\ableton claude")

from serum2 import codec
from serum2.pathmerge import (apply_path_value, read_path_value, PathError,
                              path_relationship_conflicts, MUTATION, SHARED_CONTEXT)
from serum2.evidence.spec import (ExperimentSpec, Mutation, SINGLE_FIELD, validate, ValidityError)

results = []


def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-64s %s" % ("PASS" if condition else "FAIL", label, detail))


AARD = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
_, aard_body = codec.load_preset_file(AARD)
base_rack = aard_body["FXRack0"]

print("=== A: functional proof (control == base, treatment differs at exactly the leaf) ===")

base = copy.deepcopy(base_rack)
control = copy.deepcopy(base_rack)  # unchanged
treatment = copy.deepcopy(base_rack)
apply_path_value(treatment, "FX.2.FXDistortion.plainParams.kParamDrive", 100.0)

assert_that("control == base (untouched)", control == base)
assert_that("treatment differs from base", treatment != base)

# exactly the declared leaf differs
orig_drive = read_path_value(base, "FX.2.FXDistortion.plainParams.kParamDrive")
new_drive = read_path_value(treatment, "FX.2.FXDistortion.plainParams.kParamDrive")
assert_that("declared leaf actually changed", orig_drive != new_drive,
           "orig=%s new=%s" % (orig_drive, new_drive))
assert_that("read_path_value round-trips the write", new_drive == 100.0)

# every OTHER field under FX[2] (the FXDistortion unit itself) is identical
base_fx2 = base["FX"][2]["FXDistortion"]["plainParams"]
treat_fx2 = treatment["FX"][2]["FXDistortion"]["plainParams"]
siblings_identical = all(base_fx2[k] == treat_fx2[k] for k in base_fx2 if k != "kParamDrive")
assert_that("every sibling field under FX[2] is identical", siblings_identical,
           "base=%s treat=%s" % (base_fx2, treat_fx2))

# every OTHER FX unit in the array is completely untouched
other_indices_identical = all(
    base["FX"][i] == treatment["FX"][i]
    for i in range(len(base["FX"])) if i != 2
)
assert_that("FX[0], FX[1], FX[3]... are all identical", other_indices_identical)

print()
print("=== B: list-index path mechanics ===")
try:
    apply_path_value(treatment, "FX.999.FXDistortion.plainParams.kParamDrive", 1.0)
    assert_that("out-of-range list index raises PathError", False, "no exception raised")
except PathError as e:
    assert_that("out-of-range list index raises PathError", True, str(e))

try:
    apply_path_value({"FX": {"not": "a list"}}, "FX.2.foo", 1.0)
    assert_that("numeric segment on a dict node raises PathError", False, "no exception raised")
except PathError as e:
    assert_that("numeric segment on a dict node raises PathError", True, str(e))

try:
    bad = {"FX": [1, 2, 3]}
    apply_path_value(bad, "FX.notanumber", 1.0)
    assert_that("non-numeric segment on a list node raises PathError", False, "no exception raised")
except PathError as e:
    assert_that("non-numeric segment on a list node raises PathError", True, str(e))

print()
print("=== C: directional, operation-aware conflict rule -- all 5 cases ===")

# 1. identical path, any roles -> CONFLICT
assert_that("1. identical path (mutation, shared_context) -> CONFLICT",
           path_relationship_conflicts("A.B", MUTATION, "A.B", SHARED_CONTEXT) is True)
assert_that("1. identical path (mutation, mutation) -> CONFLICT",
           path_relationship_conflicts("A.B", MUTATION, "A.B", MUTATION) is True)

# 2. two mutations, one prefixes other -> CONFLICT
assert_that("2. mutation prefixes mutation -> CONFLICT",
           path_relationship_conflicts("A", MUTATION, "A.B", MUTATION) is True)

# 3. two shared-context ops, one prefixes other -> CONFLICT
assert_that("3. shared_context prefixes shared_context -> CONFLICT",
           path_relationship_conflicts("A", SHARED_CONTEXT, "A.B", SHARED_CONTEXT) is True)

# 4. shared-context prefixes mutation -> ALLOWED (directional, the case that unblocked FXDistortion)
assert_that("4. shared_context prefixes mutation -> ALLOWED",
           path_relationship_conflicts("A", SHARED_CONTEXT, "A.B", MUTATION) is False)
assert_that("4. symmetric argument order -> ALLOWED",
           path_relationship_conflicts("A.B", MUTATION, "A", SHARED_CONTEXT) is False)

# 5. mutation prefixes shared-context -> CONFLICT (the REVERSE is NOT safe)
assert_that("5. mutation prefixes shared_context -> CONFLICT",
           path_relationship_conflicts("A", MUTATION, "A.B", SHARED_CONTEXT) is True)
assert_that("5. symmetric argument order -> CONFLICT",
           path_relationship_conflicts("A.B", SHARED_CONTEXT, "A", MUTATION) is True)

# unrelated paths -> no conflict
assert_that("unrelated paths -> no conflict",
           path_relationship_conflicts("A.B", MUTATION, "C.D", SHARED_CONTEXT) is False)

print()
print("=== D: end-to-end through real ExperimentSpec.validate() ===")

spec_ok = ExperimentSpec(
    experiment_id="proof-allowed",
    mutations=[Mutation("FXRack0.FX.2.FXDistortion.plainParams.kParamDrive", 100.0, "test")],
    prerequisites=[], isolation_level=SINGLE_FIELD,
    claim_subject="s", claim_predicate="p",
    baseline_overrides=[Mutation("FXRack0", base_rack, "shared context")],
)
try:
    validate(spec_ok)
    assert_that("shared_context(FXRack0) + mutation(FXRack0.FX.2...) -> spec is VALID", True)
except ValidityError as e:
    assert_that("shared_context(FXRack0) + mutation(FXRack0.FX.2...) -> spec is VALID", False, str(e))

spec_bad = ExperimentSpec(
    experiment_id="proof-rejected",
    mutations=[Mutation("FXRack0", base_rack, "test")],
    prerequisites=[], isolation_level=SINGLE_FIELD,
    claim_subject="s", claim_predicate="p",
    baseline_overrides=[Mutation("FXRack0.FX.2.FXDistortion.plainParams.kParamDrive", 100.0, "shared context")],
)
try:
    validate(spec_bad)
    assert_that("mutation(FXRack0) + shared_context(FXRack0.FX.2...) -> spec is REJECTED", False,
               "validate() did not raise")
except ValidityError as e:
    assert_that("mutation(FXRack0) + shared_context(FXRack0.FX.2...) -> spec is REJECTED", True, str(e))

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL PROOF ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
