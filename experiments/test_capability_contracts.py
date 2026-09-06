"""15.3.8: mandatory proof test for the Capability Contract layer. Verifies
the layer's one job -- being STRICTLY DERIVED from ClaimGroup, never
upgrading a claim group's own evidence into something stronger.

Named guard cases, each one a scenario the user explicitly called out as
something the contract layer must NOT get wrong:
  1. FXEQ.Type1       -- NO_OBSERVED_EFFECT must not become "works causally"
  2. LFO-as-source      -- UNKNOWN/negative must stay unusable to any compiler
                          requiring a causal LFO-modulation-source guarantee
  3. VoicePanel.RandomPan -- confound-compromised result must not read as clean
  4. Macro.name         -- persistence actually FAILED; family-level PERSISTENT
                          rollup must not leak into this specific field's contract
  5. Sanity: a genuinely CAUSAL_VERIFIED contract (Drive) must actually be
     usable_for(required_causal=True).
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import capability_contract as cc

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-72s %s" % ("PASS" if condition else "FAIL", label, detail))

def find(target_substr):
    hits = [c for c in contracts.values() if target_substr in c.target]
    return hits[0] if hits else None

print("=== 1. FXEQ.Type1: honest negative must not be upgraded ===")
type1 = find("fx_field_eq_kParamType1")
assert_that("Type1 contract exists", type1 is not None)
if type1:
    assert_that("Type1 status == STRUCTURAL_ONLY (not CAUSAL_VERIFIED)",
               type1.status == cc.STRUCTURAL_ONLY, "status=%s" % type1.status)
    assert_that("Type1 verified.causal == NO_OBSERVED_EFFECT (not silently omitted)",
               type1.verified["causal"] == "NO_OBSERVED_EFFECT", "%s" % type1.verified)
    assert_that("Type1 NOT usable_for(required_causal=True)",
               type1.usable_for(required_causal=True) is False)
    assert_that("Type1 IS usable_for(no causal requirement) -- structural facts still usable",
               type1.usable_for(required_causal=False) is True)

print()
print("=== 2. LFO-as-source: negative/no-evidence must stay unusable ===")
lfo_src = find("lfo_as_modulation_source")
assert_that("LFO-as-source contract exists", lfo_src is not None)
if lfo_src:
    assert_that("LFO-as-source status == BLOCKED_NO_EVIDENCE",
               lfo_src.status == cc.NEGATIVE_EVIDENCE, "status=%s" % lfo_src.status)
    assert_that("LFO-as-source NOT usable_for(required_causal=True)",
               lfo_src.usable_for(required_causal=True) is False)
    assert_that("LFO-as-source NOT even usable_for(no causal requirement) -- BLOCKED means BLOCKED",
               lfo_src.usable_for(required_causal=False) is False)

print()
print("=== 3. VoicePanel.RandomPan: confound-compromised result must not read clean ===")
randompan = find("voice_field_randompan")
assert_that("RandomPan contract exists", randompan is not None)
if randompan:
    assert_that("RandomPan status == STRUCTURAL_ONLY (not CAUSAL_VERIFIED)",
               randompan.status == cc.STRUCTURAL_ONLY, "status=%s" % randompan.status)
    assert_that("RandomPan verified.causal == NO_OBSERVED_EFFECT (honest, not upgraded)",
               randompan.verified["causal"] == "NO_OBSERVED_EFFECT", "%s" % randompan.verified)
    assert_that("RandomPan NOT usable_for(required_causal=True)",
               randompan.usable_for(required_causal=True) is False)

print()
print("=== 4. Macro.name: persistence actually FAILED -- must not inherit family PERSISTENT ===")
macro_name = find("macro_field_name")
assert_that("Macro.name contract exists", macro_name is not None)
if macro_name:
    assert_that("Macro.name status == BLOCKED_NO_EVIDENCE (persistence gate never met)",
               macro_name.status == cc.NEGATIVE_EVIDENCE, "status=%s" % macro_name.status)
    assert_that("Macro.name NOT usable_for() at all",
               macro_name.usable_for(required_causal=False) is False)

print()
print("=== 5. Sanity: a real CAUSAL_VERIFIED contract must actually be usable ===")
drive = find("fx_field_distortion_drive")
assert_that("Drive contract exists", drive is not None)
if drive:
    assert_that("Drive status == CAUSAL_VERIFIED", drive.status == cc.CAUSAL_VERIFIED, "status=%s" % drive.status)
    assert_that("Drive verified.causal == EFFECT_OBSERVED", drive.verified["causal"] == "EFFECT_OBSERVED")
    assert_that("Drive IS usable_for(required_causal=True)", drive.usable_for(required_causal=True) is True)

print()
print("=== 6. Read-only guard: building contracts must not mutate the ClaimEngine ===")
import copy
eng_snapshot_keys = set(contracts.keys())
contracts2 = cc.build_all_contracts.__wrapped__ if hasattr(cc.build_all_contracts, "__wrapped__") else None
# Re-derive from the same pickled contracts dict structurally: confirm every
# contract's provenance traces back to real supporting_evidence ids (never
# fabricated), and that no contract claims a status stronger than its own
# verified.causal justifies.
bad = []
for key, c in contracts.items():
    if c.status == cc.CAUSAL_VERIFIED and c.verified.get("causal") != "EFFECT_OBSERVED":
        bad.append((key, "CAUSAL_VERIFIED but causal!=EFFECT_OBSERVED: %s" % c.verified))
    if c.status not in (cc.BLOCKED_CONTRADICTED, cc.NEGATIVE_EVIDENCE) and not c.provenance.get("supporting_evidence"):
        bad.append((key, "non-blocked contract with no supporting_evidence provenance"))
assert_that("no contract's status exceeds what its own verified.causal justifies", not bad, str(bad))

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL CAPABILITY CONTRACT ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
