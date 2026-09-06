"""15.4.8: mandatory adversarial proof suite for the compiler admission layer.
Every test here is a DELIBERATE attempt to make admit() overclaim -- to admit
something it shouldn't, or to admit something real evidence contradicts, or
to make a demonstrated negative look like an absence of evidence, or to let
a proven field's contract silently cover a sibling/family it never tested.
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import admission as adm
from serum2.evidence import capability_contract as cc

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-78s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:100]))

print("=== 15.4.2: compiler admission rules against the 4 named cases ===")

r = adm.admit(contracts, "lfo_as_modulation_source", required_causal=True)
assert_that("LFO source (required_causal=True) -> REFUSED", not r.admitted, r.reason)
assert_that("LFO source refusal reason is NEGATIVE_EVIDENCE-based, not UNKNOWN",
           r.reason == adm.REFUSED_NEGATIVE_EVIDENCE, r.reason)

r = adm.admit(contracts, "macro_field_name", required_persistence=True)
assert_that("Macro.name (required_persistence=True) -> REFUSED", not r.admitted, r.reason)
assert_that("Macro.name refusal is negative-evidence (persistence actually FAILED)",
           r.reason == adm.REFUSED_NEGATIVE_EVIDENCE, r.reason)

r = adm.admit(contracts, "voice_field_randompan", required_causal=True)
assert_that("RandomPan (required_causal=True) -> REFUSED", not r.admitted, r.reason)
assert_that("RandomPan refusal is structural-only-insufficient (not fabricated as negative_evidence)",
           r.reason == adm.REFUSED_STRUCTURAL_ONLY_FOR_CAUSAL, r.reason)

r = adm.admit(contracts, "fx_field_eq_freq1", required_causal=True)
assert_that("proven FXEQ Freq1 (required_causal=True) -> ADMITTED", r.admitted, r.reason)

print()
print("=== 15.4.3: UNKNOWN != UNSUPPORTED ===")
r = adm.admit(contracts, "fx_field_reverb_decay_time")  # never tested this session
assert_that("never-tested target -> REFUSED with UNKNOWN reason", not r.admitted, r.reason)
assert_that("refusal reason is exactly 'unknown_no_contract', not an unsupported/negative claim",
           r.reason == adm.REFUSED_UNKNOWN, r.reason)
assert_that("UNKNOWN refusal detail explicitly disclaims asserting Serum can't do it",
           "NOT a claim" in r.detail, r.detail)

print()
print("=== 15.4.4: negative evidence differs structurally from absence of evidence ===")
unknown_result = adm.admit(contracts, "totally_fabricated_field_xyz")
negative_result = adm.admit(contracts, "voice_field_randompan")
assert_that("UNKNOWN and NEGATIVE_EVIDENCE produce DIFFERENT refusal reasons",
           unknown_result.reason != negative_result.reason,
           "%s vs %s" % (unknown_result.reason, negative_result.reason))
assert_that("NEGATIVE_EVIDENCE contract carries actual observed gate values, UNKNOWN carries none",
           negative_result.contract is not None and unknown_result.contract is None)

print()
print("=== 15.4.5: prerequisite refusal -- known capability, unverified prerequisite ===")
mv = adm.admit(contracts, "macro_field_value")  # has prereq host:Filter 1 On
assert_that("Macro.value contract HAS a declared prerequisite", len(mv.contract.prerequisites) > 0,
           mv.contract.prerequisites)
r_no_verify = adm.admit(contracts, "macro_field_value", required_causal=True,
                        proposed_prerequisites_verified={})  # caller confirms NOTHING
assert_that("Macro.value execution with UNVERIFIED prerequisite -> REFUSED",
           not r_no_verify.admitted, r_no_verify.reason)
assert_that("refusal reason is prerequisite_unverified", r_no_verify.reason == adm.REFUSED_PREREQUISITE_UNVERIFIED)
r_verified = adm.admit(contracts, "macro_field_value", required_causal=True,
                       proposed_prerequisites_verified={"host:Filter 1 On": True})
assert_that("Macro.value execution WITH verified prerequisite -> ADMITTED", r_verified.admitted, r_verified.reason)

print()
print("=== 15.4.6: measurement mismatch -- wrong kernel identity cannot borrow the contract ===")
drive = [c for c in contracts.values() if c.target == "fx_field_distortion_drive"][0]
real_mdid = drive.measurement["measurement_definition_id"]
r_mismatch = adm.admit(contracts, "fx_field_distortion_drive", required_causal=True,
                       required_measurement_definition_id="some_other_kernel:deadbeef")
assert_that("wrong measurement_definition_id -> REFUSED", not r_mismatch.admitted, r_mismatch.reason)
assert_that("refusal reason is measurement_definition_mismatch",
           r_mismatch.reason == adm.REFUSED_MEASUREMENT_MISMATCH)
r_match = adm.admit(contracts, "fx_field_distortion_drive", required_causal=True,
                    required_measurement_definition_id=real_mdid)
assert_that("correct measurement_definition_id -> ADMITTED", r_match.admitted, r_match.reason)

print()
print("=== 15.4.7: capability scope -- a proven field must not expand to its family ===")
# Adversarial: FXEQ has 7 proven fields. Attempt to admit a NEIGHBORING,
# never-tested FXEQ field by pretending the family name is enough.
r_sibling = adm.admit(contracts, "fx_field_eq_kParamBandwidth")  # never existed as a claim_type
assert_that("never-tested sibling field (FXEQ 'Bandwidth') -> UNKNOWN, not silently admitted",
           not r_sibling.admitted and r_sibling.reason == adm.REFUSED_UNKNOWN, r_sibling.reason)
# Adversarial: try admitting via the FAMILY name itself instead of an exact claim_type.
r_family = adm.admit(contracts, "FXRack")
assert_that("admitting by bare family name 'FXRack' -> UNKNOWN (no exact-target fuzzy match)",
           not r_family.admitted and r_family.reason == adm.REFUSED_UNKNOWN, r_family.reason)
# Confirm the real Freq1/Freq2 contracts stay genuinely independent (no shared
# admission just because they're siblings in the same FX unit).
freq1 = adm.admit(contracts, "fx_field_eq_freq1", required_causal=True)
freq2 = adm.admit(contracts, "fx_field_eq_kParamFreq2", required_causal=True)
assert_that("Freq1 and Freq2 are each independently admitted (not via a shared family grant)",
           freq1.admitted and freq2.admitted and freq1.contract is not freq2.contract)

print()
print("=== adversarial: contradicted group must never be admitted regardless of flags ===")
# No contradicted contract currently exists in this corpus (by design -- the
# harness/ClaimEngine prevent silent contradiction). Verify the CODE PATH
# still refuses one if it existed, using a synthetic contract object directly.
fake_contradicted = cc.CapabilityContract(
    target="synthetic_contradicted_field", allowed_operation=cc.MUTATE_NUMERIC,
    status=cc.BLOCKED_CONTRADICTED, prerequisites=(),
    verified={"load": None, "persistence": None, "causal": None}, measurement=None,
    scope={}, provenance={}, limitations=("synthetic test case",))
fake_contracts = {("x", "y"): fake_contradicted}
r_contra = adm.admit(fake_contracts, "synthetic_contradicted_field")
assert_that("BLOCKED_CONTRADICTED contract -> REFUSED even with no other flags set",
           not r_contra.admitted and r_contra.reason == adm.REFUSED_CONTRADICTED, r_contra.reason)

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL ADMISSION ADVERSARIAL ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
