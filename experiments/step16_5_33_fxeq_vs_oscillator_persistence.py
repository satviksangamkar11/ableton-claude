"""16.5.33: FXEQ vs Oscillator Persistence Comparison.

Objective: Determine whether the "default"-collapse round-trip failure found
in 16.5.32 is specific to Oscillator0, or a general codec/Serum issue that
would also affect FXEQ.Freq1 -- the parameter the entire earlier investigation
(16.5.17-16.5.28) depends on.

Confirmed in 16.5.32/16.5.33-prep:
  - codec.encode()/decode() is schema-agnostic CBOR+zstd (not the source)
  - The "default" collapse happens inside Serum's own load_state/save_state
  - Oscillator0.plainParams.kParamVolume does NOT survive the round trip

Method:
  1. Run the exact same resave_state() round trip for FXEQ.Freq1
     (the parameter with historical CAUSAL_VERIFIED evidence)
  2. Search the decoded structure for kParamFreq1 the same way 16.5.32 did
  3. Compare: does FXEQ round-trip cleanly while Oscillator0 does not?
  4. Report PERSISTED / NOT_PERSISTED / UNRESOLVED for FXEQ specifically

No codec/persistence-checker/producer/compiler changes. Pure comparison.
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
print("16.5.33: FXEQ vs Oscillator Persistence Comparison")
print("=" * 80)
print()

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]


def recursive_search(obj, path_parts, target_substrings, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = path_parts + [str(k)]
            if any(sub.lower() in str(k).lower() for sub in target_substrings):
                out.append((".".join(new_path), type(v).__name__, v))
            recursive_search(v, new_path, target_substrings, out)
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            recursive_search(item, path_parts + ["[%d]" % i], target_substrings, out)


def round_trip_and_search(target_path, test_value, search_terms, label):
    print("=" * 80)
    print("TEST: %s" % label)
    print("=" * 80)
    print()
    print("Target path: %s" % target_path)
    print("Test value:  %s" % test_value)
    print()

    body = copy.deepcopy(body_base)

    orig_val = pathmerge.read_path_value(body, target_path)
    print("OBSERVED - Original value at path: %s" % orig_val)

    pathmerge.apply_path_value(body, target_path, test_value)
    mutated_val = pathmerge.read_path_value(body, target_path)
    print("OBSERVED - After mutation: %s" % mutated_val)
    print()

    meta = {}
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta, body)

    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    try:
        synth.load_state(tmp)
    except Exception as e:
        os.remove(tmp)
        print("[ERROR] load_state failed: %s" % e)
        return None
    os.remove(tmp)

    fd, out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    synth.save_state(out)
    raw = open(out, "rb").read()
    os.remove(out)

    decoded_meta, decoded_body = codec.decode(vst3_state.unwrap_vc2(raw))
    print("[OK] Round trip complete.")
    print()

    # Direct path check (same schema as written)
    direct_readback = pathmerge.read_path_value(decoded_body, target_path)
    print("Direct pathmerge readback at SAME path '%s':" % target_path)
    print("  Value: %s" % direct_readback)
    print()

    # Recursive search for the parameter anywhere in the structure
    matches = []
    recursive_search(decoded_body, [], search_terms, matches)
    print("Recursive search for %s anywhere in decoded structure:" % search_terms)
    print("  Total matches: %d" % len(matches))
    for path, typ, val in matches[:20]:
        val_repr = str(val)
        if len(val_repr) > 60:
            val_repr = val_repr[:60] + "..."
        print("    %-70s | %-8s | %s" % (path, typ, val_repr))
    print()

    # Verdict for this parameter
    exact_matches = [m for m in matches if m[0].endswith(target_path.split(".")[-1])]
    close_matches = [m for m in exact_matches
                      if isinstance(m[2], (int, float)) and abs(float(m[2]) - test_value) < 1e-3]

    if direct_readback is not None and isinstance(direct_readback, (int, float)) and abs(float(direct_readback) - test_value) < 1e-3:
        verdict = "PERSISTED_DIRECT_PATH"
        print("VERDICT: PERSISTED (direct path readback matches)")
    elif close_matches:
        verdict = "PERSISTED_DIFFERENT_PATH"
        print("VERDICT: PERSISTED (found elsewhere in structure, not at original path)")
    elif exact_matches:
        verdict = "NOT_PERSISTED_VALUE_DIFFERS"
        print("VERDICT: NOT_PERSISTED (field exists but value differs)")
    else:
        verdict = "UNRESOLVED_FIELD_NOT_FOUND"
        print("VERDICT: UNRESOLVED (field not found anywhere in decoded structure)")

    print()
    return verdict


# ---- TEST 1: FXEQ.Freq1 (the historically causal-verified parameter) ----
fxeq_verdict = round_trip_and_search(
    "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1",
    15000.0,
    ["kParamFreq1", "Freq1", "freq1"],
    "FXEQ.Freq1 (historical CAUSAL_VERIFIED parameter)"
)

# ---- TEST 2: Oscillator0.Volume (re-run for direct side-by-side) ----
osc_verdict = round_trip_and_search(
    "Oscillator0.plainParams.kParamVolume",
    0.05,
    ["kParamVolume", "volume", "Volume"],
    "Oscillator0.Volume (16.5.32 comparison baseline)"
)

# ---- SECTION: Side-by-side comparison ----
print("=" * 80)
print("SIDE-BY-SIDE COMPARISON")
print("=" * 80)
print()

print("FXEQ.Freq1 persistence verdict:        %s" % fxeq_verdict)
print("Oscillator0.Volume persistence verdict: %s" % osc_verdict)
print()

if fxeq_verdict in ("PERSISTED_DIRECT_PATH", "PERSISTED_DIFFERENT_PATH") and \
   osc_verdict in ("UNRESOLVED_FIELD_NOT_FOUND", "NOT_PERSISTED_VALUE_DIFFERS"):
    print("CONCLUSION: The persistence failure is SPECIFIC to Oscillator0,")
    print("            not a general codec/Serum round-trip defect.")
    print("            FXEQ round-trips correctly through the same mechanism.")
    print()
    print("Implication for the FXEQ investigation (16.5.17-16.5.28):")
    print("  The state-application pipeline for FXEQ is NOT implicated by")
    print("  this Oscillator-specific finding. The FXEQ.Freq1 -> centroid")
    print("  mystery (6925 Hz vs 3863 Hz baseline) remains open on its own")
    print("  terms, independent of the Oscillator persistence issue.")
    overall = "OSCILLATOR_SPECIFIC"

elif fxeq_verdict in ("UNRESOLVED_FIELD_NOT_FOUND", "NOT_PERSISTED_VALUE_DIFFERS") and \
     osc_verdict in ("UNRESOLVED_FIELD_NOT_FOUND", "NOT_PERSISTED_VALUE_DIFFERS"):
    print("CONCLUSION: BOTH FXEQ.Freq1 and Oscillator0.Volume fail to persist")
    print("            through the same round trip mechanism.")
    print()
    print("Implication:")
    print("  This is a GENERAL corpus-schema-vs-Serum-native-schema mismatch,")
    print("  not module-specific. This DOES implicate the earlier FXEQ")
    print("  investigation -- the persistence check used throughout may have")
    print("  been unreliable for ALL parameters, not just Oscillator.")
    print("  HOWEVER: 16.5.17 showed the FXEQ mutation DID apply correctly at")
    print("  the body-dict level (state_diff.matches_intent=True), and the")
    print("  historical FXEQ evidence predates this specific check -- so this")
    print("  finding is about the VERIFICATION mechanism, not necessarily")
    print("  about whether FXEQ audio itself responds to Freq1.")
    overall = "GENERAL_SCHEMA_MISMATCH"

else:
    print("CONCLUSION: Mixed result -- one persisted via a different path than")
    print("            expected, or results are otherwise inconclusive.")
    overall = "MIXED_INCONCLUSIVE"

print()
print("=" * 80)
print("16.5.33 COMPLETE")
print("=" * 80)
print()
print("Overall: %s" % overall)
