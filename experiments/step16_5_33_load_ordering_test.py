"""16.5.33: load_state() / load_graph() Ordering Test.

Established in 16.5.32:
  ALL render arms produce byte-identical audio (sha 8a212cca..., -19.25 dB),
  including one with NO load_state() call at all.
  => synth.load_state() is a complete no-op in the current render path.

This script tests ONE question:
  Does load_state() land, and does load_graph() discard it?

Probes:
  1. What methods does the plugin processor expose? (is there a prepare/open
     step, or an alternate state API we are not using?)
  2. Does load_state() return a status we have been discarding?
  3. Does save_state() IMMEDIATELY after load_state() reflect the loaded body?
     - corpus body[4] has 5 FX in FXRack0.FX
     - if readback shows FX: [] -> load never landed
     - if readback shows 5 FX -> load landed, something later discards it
  4. Audio across orderings:
       A  no load_state at all                     (reference)
       E  load_state BEFORE load_graph             (current render_arm order)
       F  load_state AFTER  load_graph             (the ordering hypothesis)

Discriminates: "load never applied" vs "load applied then wiped by load_graph".

No producer/compiler changes. Diagnostic only.
"""
import sys, os, pickle, tempfile, hashlib
sys.path.insert(0, r"D:\ableton claude")

import numpy as np
import dawdreamer as daw
from serum2 import bridge, codec, vst3_state
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
SR = 44100
BLOCK = 512

print("=" * 80)
print("16.5.33: load_state() / load_graph() Ordering Test")
print("=" * 80)
print()

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_corpus = corpus["bodies"][4]
meta_real, _ = bridge.capture_v8_skeleton(VST3)

n_fx_expected = len(body_corpus.get("FXRack0", {}).get("FX", []))
print("Corpus body[4] FXRack0.FX device count: %d" % n_fx_expected)
print()


def write_state(meta, body):
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    return tmp


# ---- PROBE 1: available processor methods ----
print("PROBE 1: Plugin processor API surface")
print("-" * 80)
engine = daw.RenderEngine(SR, BLOCK)
synth = engine.make_plugin_processor("serum", VST3)
methods = [m for m in dir(synth) if not m.startswith("_")]
print("Methods/attrs (%d):" % len(methods))
for i in range(0, len(methods), 4):
    print("  " + "  ".join("%-22s" % m for m in methods[i:i + 4]))
print()

# ---- PROBE 2: load_state return value + immediate readback ----
print("PROBE 2: load_state() return value and immediate save_state readback")
print("-" * 80)
tmp = write_state(meta_real, body_corpus)
ret = synth.load_state(tmp)
print("load_state() returned: %r  (type=%s)" % (ret, type(ret).__name__))
os.remove(tmp)

fd, out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(out)
raw = open(out, "rb").read()
os.remove(out)
_, body_back = codec.decode(vst3_state.unwrap_vc2(raw))
n_fx_back = len(body_back.get("FXRack0", {}).get("FX", []))
print("save_state readback IMMEDIATELY after load_state (no graph yet):")
print("  FXRack0.FX device count: %d  (expected %d if load landed)" % (n_fx_back, n_fx_expected))
if n_fx_back == n_fx_expected and n_fx_expected > 0:
    print("  => LOAD LANDED at the plugin level.")
    load_landed = True
else:
    print("  => LOAD DID NOT LAND (or is not reflected in save_state).")
    load_landed = False
print()


# ---- PROBE 3: audio across orderings ----
def render(order, label):
    """order: 'none' | 'before' | 'after'  (relative to load_graph)"""
    eng = daw.RenderEngine(SR, BLOCK)
    syn = eng.make_plugin_processor("serum", VST3)
    tmpf = None
    if order in ("before", "after"):
        tmpf = write_state(meta_real, body_corpus)
    if order == "before":
        syn.load_state(tmpf)
    syn.clear_midi()
    syn.add_midi_note(48, 110, 0.0, 1.8)
    eng.load_graph([(syn, [])])
    if order == "after":
        syn.load_state(tmpf)
    if tmpf:
        os.remove(tmpf)
    eng.render(2.0)
    a = np.asarray(eng.get_audio())
    sha = hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    mono = a.mean(axis=0) if a.ndim == 2 else a
    rms = 20 * np.log10(float(np.sqrt(np.mean(mono ** 2))) + 1e-12)
    print("  %-3s order=%-7s sha=%s  rms=%.2f dB" % (label, order, sha[:16], rms))
    return {"audio": a, "sha": sha, "rms": rms}


print("PROBE 3: Audio across load orderings")
print("-" * 80)
A = render("none", "A")
E = render("before", "E")
F = render("after", "F")
print()

print("=" * 80)
print("COMPARISONS")
print("=" * 80)


def cmp(x, y, xl, yl):
    same = x["sha"] == y["sha"]
    mad = float(np.max(np.abs(x["audio"] - y["audio"]))) if x["audio"].shape == y["audio"].shape else float("nan")
    print("  %-3s vs %-3s  identical=%-5s  max_abs_diff=%.6e" % (xl, yl, same, mad))
    return same


e_vs_a = cmp(E, A, "E", "A")
f_vs_a = cmp(F, A, "F", "A")
f_vs_e = cmp(F, E, "F", "E")
print()

print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

if not f_vs_a:
    print("[F != A] Loading state AFTER load_graph() DOES change the audio.")
    print("         => ORDERING BUG CONFIRMED. load_graph() was discarding the")
    print("            state loaded before it. render_arm() must load after.")
    verdict = "ORDERING_BUG_CONFIRMED"
elif load_landed:
    print("[F == A] but load_state DID land at the plugin level (save_state readback")
    print("         showed the loaded FX chain).")
    print("         => State reaches the plugin but never reaches the rendered")
    print("            audio, under either ordering. The break is between plugin")
    print("            state and the render/DSP path, not in ordering.")
    verdict = "STATE_LANDS_BUT_AUDIO_UNAFFECTED"
else:
    print("[F == A] and load_state did NOT land in save_state readback.")
    print("         => load_state() is not applying state at all, under either")
    print("            ordering. The break is at the load/deserialize boundary.")
    verdict = "LOAD_STATE_INEFFECTIVE"

print()
print("=" * 80)
print("16.5.33 COMPLETE   Verdict: %s" % verdict)
print("=" * 80)
