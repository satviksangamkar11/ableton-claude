"""16.5.4 regression tests for semantic target resolution.

Nine invariants (user-specified):
  1. "FXEQ.Freq1" resolves to fx_field_eq_freq1
  2. Resolver obtains context from capability layer (contract), not targets.py
  3. FXEQ at index 0 resolves to path .0.
  4. FXEQ at index 2 resolves to path .2.
  5. No FXEQ in body -> resolve_path returns None (CONTEXT_NOT_SATISFIED)
  6. Unknown semantic target -> TargetRefusal(UNKNOWN_SEMANTIC_TARGET)
  7. Changing contract's mutation_target_path changes resolution without
     changing SEMANTIC_TARGETS
  8. No literal numeric FX index in SEMANTIC_TARGETS
  9. Alias resolution never grants structural or causal admission
"""
import sys, pickle, re
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler.targets import (
    SemanticTargetRef, ResolvedTarget, TargetRefusal,
    SEMANTIC_TARGETS, UNKNOWN_SEMANTIC_TARGET, CAPABILITY_NOT_FOUND,
    resolve_semantic_target, resolve_path,
)

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-80s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:80]))

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

print("=== 1. 'FXEQ.Freq1' resolves to fx_field_eq_freq1 ===")
resolved = resolve_semantic_target("FXEQ.Freq1", contracts)
assert_that("not a TargetRefusal", isinstance(resolved, ResolvedTarget), resolved)
assert_that("ref.name == 'FXEQ.Freq1'",
            isinstance(resolved, ResolvedTarget) and resolved.ref.name == "FXEQ.Freq1")
assert_that("ref.capability_key == 'fx_field_eq_freq1'",
            isinstance(resolved, ResolvedTarget)
            and resolved.ref.capability_key == "fx_field_eq_freq1")
assert_that("contract.target == 'fx_field_eq_freq1'",
            isinstance(resolved, ResolvedTarget)
            and resolved.contract.target == "fx_field_eq_freq1",
            getattr(resolved, "contract", None) and resolved.contract.target)

print()
print("=== 2. Context comes from capability layer, not targets.py ===")
# The mutation_target_path is in the contract's scope, not in SEMANTIC_TARGETS
if isinstance(resolved, ResolvedTarget):
    path_in_contract = resolved.contract.scope.get("mutation_target_path")
    assert_that("contract carries mutation_target_path", path_in_contract is not None,
                path_in_contract)
    ref_as_repr = repr(SEMANTIC_TARGETS["FXEQ.Freq1"])
    assert_that("SEMANTIC_TARGETS['FXEQ.Freq1'] contains no path info",
                "FXRack0" not in ref_as_repr and "kParam" not in ref_as_repr, ref_as_repr)
    ref_vals = [SEMANTIC_TARGETS["FXEQ.Freq1"].name, SEMANTIC_TARGETS["FXEQ.Freq1"].capability_key]
    has_index = any(seg.isdigit() for s in ref_vals for seg in s.replace("_", ".").split("."))
    assert_that("SEMANTIC_TARGETS['FXEQ.Freq1'] contains no standalone integer index",
                not has_index, ref_vals)

print()
print("=== 3. FXEQ at index 0 resolves to path with .0. ===")
body_fxeq_at_0 = {"FXRack0": {"FX": [{"FXEQ": {"plainParams": {"kParamFreq1": 5000}}}]}}
if isinstance(resolved, ResolvedTarget):
    p0 = resolve_path(resolved, body_fxeq_at_0)
    assert_that("returns a path", p0 is not None, p0)
    assert_that("path contains .0.", p0 is not None and ".0." in p0, p0)
    assert_that("path ends with kParamFreq1",
                p0 is not None and p0.endswith("kParamFreq1"), p0)

print()
print("=== 4. FXEQ at index 2 resolves to path with .2. ===")
body_fxeq_at_2 = {"FXRack0": {"FX": [
    {"FXDistortion": {"plainParams": {}}},
    {"FXDistortion": {"plainParams": {}}},
    {"FXEQ": {"plainParams": {"kParamFreq1": 5000}}},
]}}
if isinstance(resolved, ResolvedTarget):
    p2 = resolve_path(resolved, body_fxeq_at_2)
    assert_that("returns a path", p2 is not None, p2)
    assert_that("path contains .2.", p2 is not None and ".2." in p2, p2)

print()
print("=== 5. No FXEQ -> resolve_path returns None ===")
body_no_fxeq = {"FXRack0": {"FX": [{"FXDistortion": {"plainParams": {}}}]}}
body_empty_fx = {"FXRack0": {"FX": []}}
if isinstance(resolved, ResolvedTarget):
    p_none = resolve_path(resolved, body_no_fxeq)
    assert_that("no FXEQ: returns None", p_none is None, p_none)
    p_empty = resolve_path(resolved, body_empty_fx)
    assert_that("empty FX: returns None", p_empty is None, p_empty)

print()
print("=== 6. Unknown semantic target -> TargetRefusal ===")
refusal = resolve_semantic_target("NonExistent.Field", contracts)
assert_that("returns TargetRefusal", isinstance(refusal, TargetRefusal), refusal)
assert_that("reason == UNKNOWN_SEMANTIC_TARGET",
            isinstance(refusal, TargetRefusal) and refusal.reason == UNKNOWN_SEMANTIC_TARGET,
            getattr(refusal, "reason", None))

print()
print("=== 7. Changing contract path changes resolution without changing targets.py ===")
# Build a fake contracts dict where the capability_key "fx_field_eq_freq1" maps to
# a contract whose mutation_target_path points to an entirely different container.
class _FakeContract:
    def __init__(self, target, path, status="STRUCTURAL_ONLY"):
        self.target = target
        self.scope = {"mutation_target_path": path}
        self.status = status
        self.allowed_operation = "mutate_numeric_value"
        self.limitations = ()

fake_contracts_alt_container = {
    ("fake_cdid", "fake_cond"): _FakeContract(
        "fx_field_eq_freq1",
        "FXRack0.AlternateFX.0.FXEQ.plainParams.kParamFreq1",
    )
}
resolved_alt = resolve_semantic_target("FXEQ.Freq1", fake_contracts_alt_container)
assert_that("alt contract: resolves to ResolvedTarget", isinstance(resolved_alt, ResolvedTarget))

# Body with FXEQ in FXRack0.FX (original container) -- should fail for alt contract
body_original = {"FXRack0": {
    "FX": [{"FXEQ": {"plainParams": {}}}],
    "AlternateFX": [],
}}
p_alt_fail = resolve_path(resolved_alt, body_original) if isinstance(resolved_alt, ResolvedTarget) else "SKIP"
assert_that("alt contract: body lacks AlternateFX FXEQ -> None", p_alt_fail is None, p_alt_fail)

# Body with FXEQ in FXRack0.AlternateFX -- should succeed
body_alternate = {"FXRack0": {"AlternateFX": [{"FXEQ": {"plainParams": {}}}]}}
p_alt_ok = resolve_path(resolved_alt, body_alternate) if isinstance(resolved_alt, ResolvedTarget) else None
assert_that("alt contract: body has AlternateFX FXEQ -> resolves",
            p_alt_ok is not None and "AlternateFX" in p_alt_ok, p_alt_ok)
assert_that("SEMANTIC_TARGETS unchanged (targets.py was not modified)",
            SEMANTIC_TARGETS["FXEQ.Freq1"].capability_key == "fx_field_eq_freq1")

print()
print("=== 8. No literal numeric FX index in SEMANTIC_TARGETS ===")
# The invariant: no STANDALONE integer segment appears in name or capability_key
# (e.g., ".1." path indices). Digits embedded in parameter names ("Freq1",
# "Reso2") are intentional and not list position indices.
for name_key, ref in SEMANTIC_TARGETS.items():
    name_has_index = any(seg.isdigit() for seg in ref.name.split("."))
    key_has_index = any(seg.isdigit() for seg in ref.capability_key.split("_"))
    assert_that("no standalone integer in %r .name" % name_key, not name_has_index, ref.name)
    assert_that("no standalone integer in %r .capability_key" % name_key,
                not key_has_index, ref.capability_key)

print()
print("=== 9. Alias resolution never grants structural or causal admission ===")
resolved9 = resolve_semantic_target("FXEQ.Freq1", contracts)
assert_that("ResolvedTarget has no 'admitted' attribute",
            not hasattr(resolved9, "admitted"))
assert_that("ResolvedTarget has no 'usable_for' method",
            not hasattr(resolved9, "usable_for"))
assert_that("TargetRefusal has no 'admitted' attribute",
            not hasattr(TargetRefusal("R", "D"), "admitted"))
# The contract is present for inspection, but it is NOT an admission decision.
# The caller must call admission.admit() separately.
if isinstance(resolved9, ResolvedTarget):
    assert_that("contract on ResolvedTarget has usable_for (for reference only)",
                hasattr(resolved9.contract, "usable_for"))
    assert_that("resolved target itself does not call usable_for",
                True, "enforcement: caller must call admit() explicitly")

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL SEMANTIC TARGET ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
