"""16.5.34: Codec vs load_state Isolation.

Established:
  16.5.32  ALL render arms byte-identical, including one with NO load_state()
  16.5.33  load_state() returns None and does not land (save_state readback
           shows FXRack0.FX=0 where corpus body[4] has 5). Not an ordering bug.

This experiment uses an input path INDEPENDENT of our codec (the direct host
parameter API) to create a known-distinctive state, then tests whether that
state survives save -> load, and whether our codec round trip preserves it.

Arms:
  A  fresh                                       -> reference
  B  fresh + set_parameter(Main Vol, 0.0)        -> proves live actuator
  C  fresh + load_state(Serum-native f1)         -> load_state on known-good bytes
  D  fresh + load_state(reencode(decode(f1)))    -> our codec path
  E  fresh + set_patch(get_patch of a modified)  -> alternate state API

Gates (in order):
  G1  set_parameter readback confirms the value stuck
  G2  B != A            -> live actuator affects DSP
  G3  f1 != f0 (bytes)  -> save_state captures the change (else C/D vacuous)
  G4  C == B            -> load_state works on Serum's own bytes
  G5  D == C            -> codec.encode preserves what Serum needs

Primary discriminator is RAW AUDIO SHA, not any metric.
Diagnostic only. No producer/compiler/frontier changes.
"""
import sys, os, tempfile, hashlib, traceback
sys.path.insert(0, r"D:\ableton claude")

import numpy as np
import dawdreamer as daw
from serum2 import bridge, codec, vst3_state
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
SR, BLOCK = 44100, 512
NOTE, VEL, LEN, DUR = 48, 110, 1.8, 2.0
MAIN_VOL_IDX = 0
TEST_VAL = 0.0

print("=" * 80)
print("16.5.34: Codec vs load_state Isolation")
print("=" * 80)
print()


def new_synth():
    eng = daw.RenderEngine(SR, BLOCK)
    syn = eng.make_plugin_processor("serum", VST3)
    return eng, syn


def render_with(eng, syn):
    syn.clear_midi()
    syn.add_midi_note(NOTE, VEL, 0.0, LEN)
    eng.load_graph([(syn, [])])
    eng.render(DUR)
    a = np.asarray(eng.get_audio())
    sha = hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    mono = a.mean(axis=0) if a.ndim == 2 else a
    rms = 20 * np.log10(float(np.sqrt(np.mean(mono ** 2))) + 1e-12)
    return {"audio": a, "sha": sha, "rms": rms}


def show(label, r, note=""):
    print("  %-3s sha=%s  rms=%9.2f dB  %s" % (label, r["sha"][:16], r["rms"], note))


def save_bytes(syn):
    fd, p = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    syn.save_state(p)
    b = open(p, "rb").read()
    os.remove(p)
    return b


def write_tmp(b):
    fd, p = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    open(p, "wb").write(b)
    return p


# ---- G1: does set_parameter stick? ----
print("GATE 1: set_parameter readback")
print("-" * 80)
eng, syn = new_synth()
pname = syn.get_parameter_name(MAIN_VOL_IDX)
before = syn.get_parameter(MAIN_VOL_IDX)
syn.set_parameter(MAIN_VOL_IDX, TEST_VAL)
after = syn.get_parameter(MAIN_VOL_IDX)
print("  param[%d] name=%r" % (MAIN_VOL_IDX, pname))
print("  before=%r  set->%r  after=%r" % (before, TEST_VAL, after))
g1 = (after != before)
print("  G1 (value changed): %s" % ("PASS" if g1 else "FAIL"))
print()

# ---- A / B ----
print("ARMS A and B")
print("-" * 80)
engA, synA = new_synth()
f0 = save_bytes(synA)
A = render_with(engA, synA)
show("A", A, "(fresh, untouched)")

engB, synB = new_synth()
synB.set_parameter(MAIN_VOL_IDX, TEST_VAL)
f1 = save_bytes(synB)
B = render_with(engB, synB)
show("B", B, "(set_parameter Main Vol=0.0)")
print()

g2 = A["sha"] != B["sha"]
print("  GATE 2 (B != A, live actuator affects DSP): %s" % ("PASS" if g2 else "FAIL"))

g3 = f0 != f1
print("  GATE 3 (f1 != f0, save_state captured the change): %s" % ("PASS" if g3 else "FAIL"))
print("     f0 len=%d sha=%s" % (len(f0), hashlib.sha256(f0).hexdigest()[:16]))
print("     f1 len=%d sha=%s" % (len(f1), hashlib.sha256(f1).hexdigest()[:16]))
print()

# ---- C: load Serum-native bytes ----
print("ARM C: load_state(Serum-native f1)")
print("-" * 80)
engC, synC = new_synth()
p = write_tmp(f1)
synC.load_state(p)
os.remove(p)
fC = save_bytes(synC)
print("  save_state readback after load: %s f1" %
      ("MATCHES" if fC == f1 else "DIFFERS from"))
C = render_with(engC, synC)
show("C", C)
g4 = C["sha"] == B["sha"]
print("  GATE 4 (C == B, load_state works on native bytes): %s" % ("PASS" if g4 else "FAIL"))
print()

# ---- D: our codec round trip ----
print("ARM D: load_state(codec reencode of f1)")
print("-" * 80)
D = None
g5 = None
try:
    meta_d, body_d = codec.decode(vst3_state.unwrap_vc2(f1))
    f1_re = vst3_state.wrap_vc2(codec.encode(meta_d, body_d))
    print("  reencoded: original len=%d  reencoded len=%d  bytes_equal=%s" %
          (len(f1), len(f1_re), f1 == f1_re))
    engD, synD = new_synth()
    p = write_tmp(f1_re)
    synD.load_state(p)
    os.remove(p)
    D = render_with(engD, synD)
    show("D", D)
    g5 = (D["sha"] == C["sha"])
    print("  GATE 5 (D == C, codec preserves what Serum needs): %s" % ("PASS" if g5 else "FAIL"))
except Exception as e:
    print("  [ERROR] %s" % e)
    traceback.print_exc()
print()

# ---- E: get_patch / set_patch ----
print("ARM E: get_patch / set_patch (alternate state API)")
print("-" * 80)
E = None
try:
    engE0, synE0 = new_synth()
    patch_default = synE0.get_patch()
    synE0.set_parameter(MAIN_VOL_IDX, TEST_VAL)
    patch_modified = synE0.get_patch()
    print("  get_patch type=%s  default_len=%s  modified_len=%s  differ=%s" %
          (type(patch_default).__name__, len(patch_default), len(patch_modified),
           patch_default != patch_modified))

    engE, synE = new_synth()
    synE.set_patch(patch_modified)
    E = render_with(engE, synE)
    show("E", E)
    print("  E == B (set_patch reproduces the modified state): %s" % (E["sha"] == B["sha"]))
    print("  E == A (set_patch had no effect):                 %s" % (E["sha"] == A["sha"]))
except Exception as e:
    print("  [ERROR] get_patch/set_patch unusable: %s" % e)
print()

# ---- Interpretation ----
print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

if not g1:
    print("set_parameter did not change the parameter value.")
    print("=> The host-parameter actuator itself is not functioning. Stop here;")
    print("   this is not a codec or load_state problem.")
    verdict = "SET_PARAMETER_INEFFECTIVE"
elif not g2:
    print("[B == A] Changing Main Vol to 0.0 produced byte-identical audio.")
    print("=> The live parameter actuator does not affect the DSP either.")
    print("   NOTHING we do reaches the rendered audio. This points at the")
    print("   render/graph layer itself, not at state serialization.")
    verdict = "NO_ACTUATOR_REACHES_DSP"
elif not g3:
    print("[f1 == f0] save_state() did not capture the parameter change.")
    print("=> save_state does not reflect live state, so arms C and D are")
    print("   round-tripping a default state and cannot discriminate.")
    print("   save_state itself is the unreliable component.")
    verdict = "SAVE_STATE_DOES_NOT_CAPTURE"
elif not g4:
    print("[C != B] load_state() failed to restore Serum's OWN untouched bytes.")
    print("=> The defect is in the DawDreamer/Serum load path, not our codec.")
    print("   Our encoder is exonerated; load_state is unusable as a state path.")
    verdict = "LOAD_STATE_BROKEN_ON_NATIVE_BYTES"
elif g5 is False:
    print("[C == B but D != C] load_state works on native bytes, but our")
    print("   codec round trip breaks it.")
    print("=> codec.encode/decode loses something Serum requires.")
    verdict = "CODEC_ROUNDTRIP_CORRUPTS_STATE"
elif g5 is True:
    print("[C == B and D == C] Both native and codec-reencoded bytes restore")
    print("   correctly.")
    print("=> The state path is sound for Serum-originated bodies. The failure")
    print("   is then specific to the CORPUS bodies, not to load_state or the")
    print("   codec generally.")
    verdict = "STATE_PATH_SOUND_CORPUS_BODIES_SUSPECT"
else:
    verdict = "INCONCLUSIVE"

print()
print("=" * 80)
print("16.5.34 COMPLETE   Verdict: %s" % verdict)
print("=" * 80)
