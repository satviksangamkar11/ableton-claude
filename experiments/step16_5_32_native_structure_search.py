"""16.5.32: Native Decoded Structure Search for kParamVolume.

Objective: Determine whether Oscillator0.Volume=0.05 survived the full
write -> Serum load -> Serum save -> decode round trip, by recursively
searching the ENTIRE decoded native structure for kParamVolume (and related
fields), without assuming which sub-engine holds it.

Method:
  1. Perform the exact round trip from 16.5.31 (write 0.05, load, save, decode)
  2. Recursively walk the decoded structure, collecting every path where a
     key contains "volume" (case-insensitive) or exactly "kParamVolume"
  3. Report PATH / TYPE / VALUE for every match
  4. Determine what "Oscillator0.plainParams == 'default'" indicates
     (search for related "type"/"engine"/"mode" style fields)
  5. Compare found values against the written 0.05
  6. Classify: PERSISTED / NOT_PERSISTED / UNRESOLVED

No codec/persistence-checker/producer/compiler changes. Pure inspection.
"""
import sys, pickle, copy, tempfile, os
sys.path.insert(0, r"D:\ableton claude")

from serum2 import bridge, codec, vst3_state, pathmerge
from serum2.evidence import epoch as epoch_mod
import dawdreamer as daw

VST3 = epoch_mod.SERUM_VST3
SR = 44100
BLOCK = 512

print("=" * 80)
print("16.5.32: Native Decoded Structure Search")
print("=" * 80)
print()

TARGET_PATH = "Oscillator0.plainParams.kParamVolume"
TEST_VALUE = 0.05

# ---- Reproduce the exact round trip from 16.5.31 ----
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]

meta = {}
body = copy.deepcopy(body_base)
pathmerge.apply_path_value(body, TARGET_PATH, TEST_VALUE)

print("SECTION 1: Round Trip (write=0.05 -> load -> save -> decode)")
print("-" * 80)
print()

fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
bridge.write_state_file(tmp, meta, body)

engine = daw.RenderEngine(SR, BLOCK)
synth = engine.make_plugin_processor("serum", VST3)
synth.load_state(tmp)
os.remove(tmp)

fd, out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(out)
raw = open(out, "rb").read()
os.remove(out)

decoded_meta, decoded_body = codec.decode(vst3_state.unwrap_vc2(raw))
print("[OK] Round trip complete. decoded_body has %d top-level keys." % len(decoded_body))
print()

# ---- SECTION 2: Recursive search for volume-related fields ----
print("SECTION 2: Recursive Search for 'volume' / 'kParamVolume'")
print("-" * 80)
print()

matches = []

def recursive_search(obj, path_parts, target_substrings):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = path_parts + [str(k)]
            if any(sub.lower() in str(k).lower() for sub in target_substrings):
                matches.append((".".join(new_path), type(v).__name__, v))
            recursive_search(v, new_path, target_substrings)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            new_path = path_parts + ["[%d]" % i]
            recursive_search(item, new_path, target_substrings)
    # scalars: nothing more to recurse into

recursive_search(decoded_body, [], ["kParamVolume", "volume"])

print("Total matches found: %d" % len(matches))
print()

if matches:
    print("All matches (PATH | TYPE | VALUE):")
    for path, typ, val in matches:
        val_repr = str(val)
        if len(val_repr) > 60:
            val_repr = val_repr[:60] + "..."
        print("  %-70s | %-8s | %s" % (path, typ, val_repr))
else:
    print("NO MATCHES for 'volume'/'kParamVolume' anywhere in decoded_body.")

print()

# ---- SECTION 3: What does Oscillator0.plainParams == 'default' mean? ----
print("SECTION 3: Investigating 'plainParams' == 'default'")
print("-" * 80)
print()

osc0 = decoded_body.get("Oscillator0", {})
print("Oscillator0 full key listing and types:")
for k, v in osc0.items():
    print("  %-20s type=%-8s value_preview=%s" % (k, type(v).__name__, str(v)[:80]))
print()

# Search for anything indicating "active engine" / "type" / "mode" near Oscillator0
print("Searching Oscillator0 subtree for engine-selector-like fields (type/mode/engine/select):")
engine_matches = []
recursive_search(osc0, ["Oscillator0"], ["type", "mode", "engine", "select", "active", "kind"])
if engine_matches:
    for path, typ, val in engine_matches:
        print("  %s | %s | %s" % (path, typ, val))
else:
    print("  (reusing recursive_search results would append to 'matches' list --")
    print("   running a separate pass below)")

engine_selector_matches = []
def recursive_search2(obj, path_parts, target_substrings, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = path_parts + [str(k)]
            if any(sub.lower() in str(k).lower() for sub in target_substrings):
                out.append((".".join(new_path), type(v).__name__, v))
            recursive_search2(v, new_path, target_substrings, out)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            recursive_search2(item, path_parts + ["[%d]" % i], target_substrings, out)

recursive_search2(osc0, ["Oscillator0"], ["type", "mode", "engine", "select", "active", "kind"], engine_selector_matches)

print()
print("Engine-selector-like fields found under Oscillator0:")
if engine_selector_matches:
    for path, typ, val in engine_selector_matches:
        val_repr = str(val)
        if len(val_repr) > 60:
            val_repr = val_repr[:60] + "..."
        print("  %-70s | %-8s | %s" % (path, typ, val_repr))
else:
    print("  None found.")

print()

# Sub-engine top-level structure (Granular/MultiSample/Sample/Spectral/WT)
print("Sub-engine top-level structure under each Oscillator0 child:")
for sub_engine in ["GranularOsc0", "MultiSampleOsc0", "SampleOsc0", "SpectralOsc0", "WTOsc0"]:
    if sub_engine in osc0:
        sub = osc0[sub_engine]
        print("  %s: type=%s" % (sub_engine, type(sub).__name__))
        if isinstance(sub, dict):
            print("    keys: %s" % list(sub.keys())[:10])
    else:
        print("  %s: NOT PRESENT" % sub_engine)

print()

# ---- SECTION 4: Compare original corpus body Oscillator0 structure ----
print("SECTION 4: Original Corpus Body Oscillator0 Structure (for comparison)")
print("-" * 80)
print()

orig_osc0 = body_base.get("Oscillator0", {})
print("Original corpus Oscillator0 keys and types:")
for k, v in orig_osc0.items():
    print("  %-20s type=%-8s value_preview=%s" % (k, type(v).__name__, str(v)[:80]))

print()

# ---- SECTION 5: Verdict ----
print("=" * 80)
print("SECTION 5: Verdict")
print("=" * 80)
print()

exact_target_matches = [m for m in matches if m[0].endswith("kParamVolume")]
close_value_matches = [m for m in exact_target_matches
                        if isinstance(m[2], (int, float)) and abs(float(m[2]) - TEST_VALUE) < 1e-3]

print("Matches ending in 'kParamVolume': %d" % len(exact_target_matches))
print("Of those, matching value 0.05 (within tolerance): %d" % len(close_value_matches))
print()

if len(exact_target_matches) == 0:
    print("VERDICT: UNRESOLVED")
    print("  No 'kParamVolume' field found anywhere in the decoded native structure.")
    print("  The native representation encodes volume differently (different key name,")
    print("  different structure, or a format not yet identified).")
    verdict = "UNRESOLVED_NO_KPARAMVOLUME_FOUND"

elif len(exact_target_matches) == 1:
    path, typ, val = exact_target_matches[0]
    if isinstance(val, (int, float)) and abs(float(val) - TEST_VALUE) < 1e-3:
        print("VERDICT: PERSISTED")
        print("  Exactly one kParamVolume field found, matching 0.05:")
        print("    %s = %s" % (path, val))
        verdict = "PERSISTED"
    else:
        print("VERDICT: NOT_PERSISTED")
        print("  Exactly one kParamVolume field found, but value differs:")
        print("    %s = %s (expected 0.05)" % (path, val))
        verdict = "NOT_PERSISTED"

else:
    print("VERDICT: UNRESOLVED (multiple candidates)")
    print("  Multiple kParamVolume fields found -- need to determine which")
    print("  corresponds to the currently active oscillator engine.")
    for path, typ, val in exact_target_matches:
        matches_05 = isinstance(val, (int, float)) and abs(float(val) - TEST_VALUE) < 1e-3
        print("    %s = %s %s" % (path, val, "[MATCHES 0.05]" if matches_05 else ""))
    verdict = "UNRESOLVED_MULTIPLE_CANDIDATES"

print()
print("=" * 80)
print("16.5.32 COMPLETE")
print("=" * 80)
print()
print("Verdict: %s" % verdict)
print()
print("Explicit non-conclusion:")
print("  This does not yet determine whether the 16.5.29/16.5.30 zero-centroid")
print("  audio result reflects a real absence of causal effect. It only")
print("  determines whether the WRITTEN value structurally persisted.")
