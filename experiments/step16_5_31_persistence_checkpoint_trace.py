"""16.5.31: Persistence Checkpoint Trace.

Objective: Locate the EXACT point where Oscillator0.Volume=0.05 diverges
through write -> load -> save -> decode, by calling resave_state() directly
and inspecting each intermediate value.

Checkpoints:
  A. original body value (post-mutation, pre-write)
  B. temp file exists / write succeeded (structural only, can't read binary directly)
  C. runtime Serum state (not directly observable via current API -- mark UNKNOWN)
  D. Serum's own save_state() raw output, after decode
  E. read_path_value(decoded_body, target_path) -- the actual "stored" value

Do NOT fix anything. Pure trace. No new causal claims.
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
print("16.5.31: Persistence Checkpoint Trace")
print("=" * 80)
print()

TARGET_PATH = "Oscillator0.plainParams.kParamVolume"
TEST_VALUE = 0.05

# ---- Load corpus ----
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]

# We need a skeleton (meta, body) pair like the harness uses
try:
    skeleton = ({}, copy.deepcopy(body_base))
    meta, body = skeleton
except Exception as e:
    print("[ERROR] Could not construct skeleton: %s" % e)
    sys.exit(1)

# ---- CHECKPOINT A: original body value ----
print("CHECKPOINT A: Original body value (before mutation)")
print("-" * 80)

original_value = pathmerge.read_path_value(body, TARGET_PATH)
print("OBSERVED - %s = %s" % (TARGET_PATH, original_value))
print()

# Apply mutation
pathmerge.apply_path_value(body, TARGET_PATH, TEST_VALUE)
mutated_value = pathmerge.read_path_value(body, TARGET_PATH)
print("OBSERVED - After mutation: %s = %s" % (TARGET_PATH, mutated_value))
print("Checkpoint A status: %s" % ("PASS" if mutated_value == TEST_VALUE else "FAIL"))
print()

# ---- CHECKPOINT B: write_state_file ----
print("CHECKPOINT B: bridge.write_state_file()")
print("-" * 80)

fd, tmp = tempfile.mkstemp(suffix=".bin")
os.close(fd)

try:
    bridge.write_state_file(tmp, meta, body)
    write_size = os.path.getsize(tmp)
    print("OBSERVED - write_state_file succeeded")
    print("  File size: %d bytes" % write_size)
    write_ok = True
except Exception as e:
    print("[ERROR] write_state_file failed: %s" % e)
    write_ok = False

print()

# ---- CHECKPOINT C: Serum load_state ----
print("CHECKPOINT C: synth.load_state() - Runtime Application")
print("-" * 80)

if write_ok:
    try:
        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)
        synth.load_state(tmp)
        print("OBSERVED - load_state() succeeded (no exception)")
        load_ok = True
    except Exception as e:
        print("[ERROR] load_state failed: %s" % e)
        load_ok = False
else:
    load_ok = False

os.remove(tmp)
print()
print("UNKNOWN - Direct runtime parameter readback:")
print("  DawDreamer's synth object may expose get_parameter() for HOST params,")
print("  but Oscillator0.plainParams.kParamVolume is a BODY-level (chunk state)")
print("  parameter, not necessarily a host-automatable parameter.")
print("  Attempting readback via get_parameters_description()...")
print()

if load_ok:
    try:
        params = synth.get_parameters_description()
        print("OBSERVED - Total host-exposed parameters: %d" % len(params))
        # Search for anything volume/oscillator related
        matches = [p for p in params if "vol" in p.get("name", "").lower() or "osc" in p.get("name", "").lower()]
        print("Parameters matching 'vol' or 'osc' (first 10):")
        for p in matches[:10]:
            print("  index=%s name=%s" % (p.get("index"), p.get("name")))
        print()
        if not matches:
            print("  No directly matching host parameter found.")
            print("  CONCLUSION: kParamVolume is body/chunk-state, not a host-automatable")
            print("  parameter exposed via get_parameters_description(). Runtime readback")
            print("  via this API is UNKNOWN/NOT APPLICABLE for this parameter.")
    except Exception as e:
        print("[ERROR] Could not enumerate parameters: %s" % e)

print()

# ---- CHECKPOINT D & E: save_state and decode ----
print("CHECKPOINT D+E: synth.save_state() -> codec.decode()")
print("-" * 80)

if load_ok:
    try:
        fd, out = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        synth.save_state(out)
        raw = open(out, "rb").read()
        os.remove(out)
        print("OBSERVED - save_state() succeeded, raw size: %d bytes" % len(raw))

        unwrapped = vst3_state.unwrap_vc2(raw)
        print("OBSERVED - unwrap_vc2() succeeded, size: %d bytes" % len(unwrapped))

        decode_result = codec.decode(unwrapped)
        print("OBSERVED - codec.decode() succeeded, returned type: %s" % type(decode_result).__name__)
        if isinstance(decode_result, tuple):
            print("  It's a tuple of length %d (matches harness: '_, resaved_body = resave_state(...)')" % len(decode_result))
            decoded_meta, decoded_body = decode_result
            print("  decoded_meta type: %s" % type(decoded_meta).__name__)
            print("  decoded_body type: %s" % type(decoded_body).__name__)
        else:
            decoded_body = decode_result
        print("  Decoded body top-level keys: %d" % len(decoded_body))
        print()

        # Check if Oscillator0 exists at all in decoded body
        print("Checking decoded body structure:")
        if "Oscillator0" in decoded_body:
            print("  Oscillator0: PRESENT in decoded body")
            osc_decoded = decoded_body["Oscillator0"]
            print("  Oscillator0 keys: %s" % list(osc_decoded.keys())[:10])

            if "plainParams" in osc_decoded:
                pp = osc_decoded["plainParams"]
                print("  Oscillator0.plainParams: PRESENT, type=%s" % type(pp).__name__)
                print("  plainParams raw value (truncated): %s" % str(pp)[:200])

                if isinstance(pp, dict):
                    pp_keys = list(pp.keys())
                    print("  plainParams keys (first 10): %s" % pp_keys[:10])
                    if "kParamVolume" in pp:
                        stored_value = pp["kParamVolume"]
                        print()
                        print("OBSERVED - Direct dict access:")
                        print("  decoded_body['Oscillator0']['plainParams']['kParamVolume'] = %s" % stored_value)
                    else:
                        print("  kParamVolume: NOT FOUND in plainParams keys")
                        stored_value = None
                else:
                    print("  plainParams is NOT a dict -- likely still base64/encoded chunk data")
                    print("  This suggests kParamVolume lives in a DIFFERENT decoded structure")
                    print("  than the corpus body's schema (schema mismatch between codec.decode()")
                    print("  output and the corpus _corpus_cache.pkl body format).")
                    stored_value = None
            else:
                print("  plainParams: NOT FOUND in Oscillator0")
                print("  Available keys instead: %s" % list(osc_decoded.keys()))
                stored_value = None
        else:
            print("  Oscillator0: NOT FOUND in decoded body")
            print("  Available top-level keys (first 20): %s" % list(decoded_body.keys())[:20])
            stored_value = None

        print()

        # Now use the SAME path resolution the harness uses
        print("Using pathmerge.read_path_value() (same as harness):")
        stored_via_pathmerge = pathmerge.read_path_value(decoded_body, TARGET_PATH)
        print("  pathmerge.read_path_value(decoded_body, '%s') = %s" % (TARGET_PATH, stored_via_pathmerge))
        print()

        # Compare
        print("CHECKPOINT E RESULT:")
        print("  Expected (mutated) value: %s" % TEST_VALUE)
        print("  Direct dict access value: %s" % stored_value)
        print("  pathmerge value:          %s" % stored_via_pathmerge)
        print()

        if stored_via_pathmerge is None and stored_value is not None:
            print("CRITICAL FINDING: pathmerge.read_path_value() returns None")
            print("  but direct dict access finds the value!")
            print("  => This indicates a PATH RESOLUTION BUG in pathmerge,")
            print("     not a Serum state-application failure.")
            verdict = "PATHMERGE_BUG"
        elif stored_via_pathmerge is None and stored_value is None:
            print("CRITICAL FINDING: Value genuinely absent from decoded structure")
            print("  even via direct dict access.")
            print("  => Either Serum did not preserve this parameter, or the")
            print("     decoded schema differs from the written schema.")
            verdict = "VALUE_ABSENT_FROM_DECODE"
        elif stored_via_pathmerge is not None:
            try:
                is_close = abs(float(stored_via_pathmerge) - TEST_VALUE) < 1e-4
            except (TypeError, ValueError):
                is_close = False
            if is_close:
                print("RESULT: Value MATCHES after full round-trip!")
                print("  => Persistence actually PASSES at this checkpoint.")
                print("  => The FAIL seen in 16.5.29/16.5.30 may be a comparison")
                print("     or tolerant_equal() issue, not a state-loss issue.")
                verdict = "MATCHES_DIRECT_TRACE"
            else:
                print("RESULT: Value present but DIFFERS from expected.")
                print("  Expected: %s, Got: %s" % (TEST_VALUE, stored_via_pathmerge))
                print("  => Genuine value divergence (clamp, default override, or")
                print("     Serum-side rejection).")
                verdict = "GENUINE_VALUE_DIVERGENCE"

    except Exception as e:
        print("[ERROR] save_state/decode chain failed: %s" % e)
        import traceback
        traceback.print_exc()
        verdict = "EXECUTION_ERROR"
else:
    print("[SKIPPED] load_state failed, cannot proceed to save/decode")
    verdict = "SKIPPED_LOAD_FAILED"

print()

# ---- Also check tolerant_equal directly ----
print("SUPPLEMENTARY CHECK: pathmerge.tolerant_equal() behavior")
print("-" * 80)
try:
    if 'stored_via_pathmerge' in dir():
        te_result = pathmerge.tolerant_equal(stored_via_pathmerge, TEST_VALUE)
        print("pathmerge.tolerant_equal(%s, %s) = %s" % (stored_via_pathmerge, TEST_VALUE, te_result))
except Exception as e:
    print("[ERROR] tolerant_equal check failed: %s" % e)

print()

# ---- VERDICT ----
print("=" * 80)
print("16.5.31 VERDICT")
print("=" * 80)
print()
print("Checkpoint chain result: %s" % verdict)
print()

print("Checkpoint summary:")
print("  A (body value pre-write):        %s" % mutated_value)
print("  B (write_state_file):            %s" % ("OK" if write_ok else "FAILED"))
print("  C (load_state / runtime):        %s" % ("OK (no exception)" if load_ok else "FAILED"))
print("  D (save_state + decode):         see above")
print("  E (pathmerge readback):          see above")
print()

print("=" * 80)
print("16.5.31 COMPLETE")
print("=" * 80)
