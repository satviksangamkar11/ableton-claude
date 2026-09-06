"""16.3.5: proof for the RequiredContext derivation + satisfaction primitives,
plus the explicit substitutability guard (context is membership/type, never
position)."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler import context as ctx
from serum2 import bridge

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-72s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:120]))

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
_, skel_body = bridge.capture_v8_skeleton(VST3)
d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
aardvark_fxrack0 = None
DRIVE_PATH = "FXRack0.FX.2.FXDistortion.plainParams.kParamDrive"

# reconstruct Aardvark's real FXRack0 the same way the original Drive experiment did
import serum2.codec as codec
AARD = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
_, aard_body = codec.load_preset_file(AARD)
aardvark_fxrack0 = aard_body["FXRack0"]

print("=== derivation guard: BOTH witnesses required ===")
rc_no_positive = ctx.derive_required_context(DRIVE_PATH, "NEGATIVE_EVIDENCE", skel_body)
assert_that("no RequiredContext promoted without a positive witness (status=NEGATIVE_EVIDENCE)",
           rc_no_positive is None)

aard_body_with_context = dict(skel_body)
aard_body_with_context["FXRack0"] = aardvark_fxrack0
rc_no_negative = ctx.derive_required_context(DRIVE_PATH, "CAUSAL_VERIFIED", aard_body_with_context)
assert_that("no RequiredContext promoted when the path already resolves (no negative witness)",
           rc_no_negative is None)

rc = ctx.derive_required_context(DRIVE_PATH, "CAUSAL_VERIFIED", skel_body)
assert_that("RequiredContext IS promoted with both a positive witness and a failing bare-skeleton probe",
           rc is not None, rc)
if rc:
    assert_that("container_path == FXRack0.FX (index-agnostic, no '.2' in it)",
               rc.container_path == "FXRack0.FX", rc.container_path)
    assert_that("element_key == FXDistortion", rc.element_key == "FXDistortion", rc.element_key)
    assert_that("leaf_suffix == plainParams.kParamDrive", rc.leaf_suffix == "plainParams.kParamDrive", rc.leaf_suffix)

print()
print("=== 16.3.5: the two named cases ===")
assert_that("FXDistortion.Drive + empty FX rack (bare skeleton) -> NOT satisfied",
           rc.satisfied_by(skel_body) is False)
assert_that("FXDistortion.Drive + Aardvark's real FX context -> satisfied",
           rc.satisfied_by(aard_body_with_context) is True)

print()
print("=== substitutability: a DIFFERENT layout with FXDistortion at a DIFFERENT index ===")
# find a corpus body where FXDistortion sits at an index OTHER than 2
alt_fxrack0 = None
alt_index = None
for b in d["bodies"]:
    fxr = b.get("FXRack0")
    if not isinstance(fxr, dict):
        continue
    fx_list = fxr.get("FX", [])
    has_at_2 = len(fx_list) > 2 and isinstance(fx_list[2], dict) and "FXDistortion" in fx_list[2]
    if has_at_2:
        continue  # must NOT also have it at index 2, or resolve_index's first-match masks the test
    for i, fx in enumerate(fx_list):
        if isinstance(fx, dict) and "FXDistortion" in fx:
            alt_fxrack0, alt_index = fxr, i
            break
    if alt_fxrack0:
        break
assert_that("found an alternate real corpus layout with FXDistortion at a DIFFERENT index",
           alt_fxrack0 is not None, "index=%s" % alt_index)

if alt_fxrack0:
    alt_body = dict(skel_body)
    alt_body["FXRack0"] = alt_fxrack0
    assert_that("same RequiredContext (derived from the index-2 witness) is satisfied by the "
               "index-%d layout too -- membership/type, not position" % alt_index,
               rc.satisfied_by(alt_body) is True)
    resolved_idx = rc.resolve_index(alt_body)
    assert_that("resolve_index finds the ACTUAL index (%d) in this different layout" % alt_index,
               resolved_idx == alt_index, resolved_idx)
    resolved_path = rc.resolve_path(DRIVE_PATH, alt_body)
    expected_path = "FXRack0.FX.%d.FXDistortion.plainParams.kParamDrive" % alt_index
    assert_that("resolve_path rewrites the index segment to match this body, not the witness's index 2",
               resolved_path == expected_path, resolved_path)

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL REQUIRED CONTEXT ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
