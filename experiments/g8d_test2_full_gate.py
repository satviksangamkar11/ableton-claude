import sys, copy, hashlib
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
AARDVARK = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
TARGET_SLOT = "ModSlot30"
MACRO_HOST_NAME = "Macro 8"
MACRO_VALUE = 1.0

skeleton = bridge.capture_v8_skeleton(VST3)
_, aardvark_body = codec.load_preset_file(AARDVARK)
route1 = aardvark_body["ModSlot1"]
fxrack0 = aardvark_body["FXRack0"]

print("=== 1. Verify source ModSlot1 data ===")
print(route1)

def build_state(include_route):
    meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
    body8["FXRack0"] = copy.deepcopy(fxrack0)
    if include_route:
        body8[TARGET_SLOT] = copy.deepcopy(route1)
    return meta8, body8

meta_r, body_r = build_state(True)
meta_b, body_b = build_state(False)

print()
print("=== 2/3. Verify content + divergence ===")
print("route slot contains exactly intended route:", body_r[TARGET_SLOT] == route1)
print("route state differs from baseline state (only at ModSlot30):",
      body_r != body_b, "| diff keys:", [k for k in body_r if body_r[k] != body_b.get(k)])
skel_hash = hashlib.sha256(codec.encode(*skeleton)).hexdigest()[:16]
route_hash = hashlib.sha256(codec.encode(meta_r, body_r)).hexdigest()[:16]
print("skeleton hash:", skel_hash, "| route-state hash:", route_hash, "| differ:", skel_hash != route_hash)

def load_and_prepare(meta8, body8):
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    idx = next(p["index"] for p in synth.get_parameters_description() if p["name"] == MACRO_HOST_NAME)
    synth.set_parameter(idx, MACRO_VALUE)
    return engine, synth

def render_tail(engine, synth, note=60, vel=100, note_len=0.15, total_seconds=2.0, tail_start=0.6):
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(total_seconds)
    audio = np.asarray(engine.get_audio())
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    tail = x[int(tail_start*SR):]
    return 20*np.log10(float(np.sqrt(np.mean(tail**2)) + 1e-12))

print()
print("=== 4. Load Serum 2.0.21 ===")
load_ok = True
try:
    engine_b, synth_b = load_and_prepare(meta_b, body_b)
    engine_r, synth_r = load_and_prepare(meta_r, body_r)
    print("LOAD: OK (both arms)")
except Exception as e:
    load_ok = False
    print("LOAD: CRASH ->", type(e).__name__, e)

print()
print("=== 5. Causal test: tail energy, Macro 8 held identical both arms ===")
if load_ok:
    tail_b = render_tail(engine_b, synth_b)
    tail_r = render_tail(engine_r, synth_r)
    delta = tail_r - tail_b
    print(f"baseline (no route) tail: {tail_b:.2f} dB")
    print(f"route (ModSlot1)    tail: {tail_r:.2f} dB")
    print(f"delta: {delta:+.2f} dB")
    print("measurable route-specific response (>3dB):", abs(delta) > 3.0)

print()
print("=== 6/7. Persistence: Serum re-save, semantic survival ===")
if load_ok:
    fd, tmp_out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    synth_r.save_state(tmp_out)
    _, resaved_body = codec.decode(vst3_state.unwrap_vc2(open(tmp_out,"rb").read()))
    survived = resaved_body[TARGET_SLOT] == route1
    print("resaved ModSlot30:", resaved_body[TARGET_SLOT])
    print("EXACT match with intended route:", survived)
    os.remove(tmp_out)
