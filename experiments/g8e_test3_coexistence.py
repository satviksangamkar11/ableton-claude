import sys, copy, hashlib
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
AARDVARK = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
SLOT_A, SLOT_B = "ModSlot30", "ModSlot31"
MACRO_HOST_NAME = "Macro 8"
MACRO_VALUE = 1.0

skeleton = bridge.capture_v8_skeleton(VST3)
_, aardvark_body = codec.load_preset_file(AARDVARK)
route_filter = aardvark_body["ModSlot0"]   # VoiceFilter/kParamFreq, source [6,0], +29.68
route_delay  = aardvark_body["ModSlot1"]   # FXDelay/kParamWet, source [32,0], -22.16
fxrack0 = aardvark_body["FXRack0"]

print("=== 1. Verify both source routes ===")
print("route_filter (ModSlot0):", route_filter)
print("route_delay  (ModSlot1):", route_delay)

def build_state(include_routes):
    meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
    body8["FXRack0"] = copy.deepcopy(fxrack0)
    if include_routes:
        body8[SLOT_A] = copy.deepcopy(route_filter)
        body8[SLOT_B] = copy.deepcopy(route_delay)
    return meta8, body8

meta_r, body_r = build_state(True)
meta_b, body_b = build_state(False)

print()
print("=== 2/3. Verify isolation: diff contains exactly ModSlot30 + ModSlot31 ===")
diff_keys = sorted([k for k in body_r if body_r[k] != body_b.get(k)])
print("diff keys:", diff_keys)
print("exactly {ModSlot30, ModSlot31}:", diff_keys == sorted([SLOT_A, SLOT_B]))
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
    on_idx = next(p["index"] for p in synth.get_parameters_description() if p["name"] == "Filter 1 On")
    synth.set_parameter(on_idx, 1.0)
    macro_idx = next(p["index"] for p in synth.get_parameters_description() if p["name"] == MACRO_HOST_NAME)
    synth.set_parameter(macro_idx, MACRO_VALUE)
    return engine, synth

def render_centroid(meta8, body8, note=48, vel=110, note_len=1.8, seconds=2.0):
    engine, synth = load_and_prepare(meta8, body8)
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    audio = np.asarray(engine.get_audio())
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    spec = np.abs(np.fft.rfft(x*np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    return float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))

def render_tail(meta8, body8, note=60, vel=100, note_len=0.15, total_seconds=2.0, tail_start=0.6):
    engine, synth = load_and_prepare(meta8, body8)
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(total_seconds)
    audio = np.asarray(engine.get_audio())
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    tail = x[int(tail_start*SR):]
    return 20*np.log10(float(np.sqrt(np.mean(tail**2)) + 1e-12))

print()
print("=== 4. Load Serum 2.0.21 (both arms, both metrics) ===")
load_ok = True
try:
    c_b = render_centroid(meta_b, body_b)
    c_r = render_centroid(meta_r, body_r)
    t_b = render_tail(meta_b, body_b)
    t_r = render_tail(meta_r, body_r)
    print("LOAD: OK (all 4 renders)")
except Exception as e:
    load_ok = False
    print("LOAD: CRASH ->", type(e).__name__, e)

print()
print("=== 5a. Route 1 causal signature: VoiceFilter cutoff (centroid) ===")
if load_ok:
    print(f"baseline centroid: {c_b:.1f} Hz | route centroid: {c_r:.1f} Hz | delta: {c_r-c_b:+.1f} Hz")
    print("matches expected VoiceFilter signature (route > baseline, ~600Hz rise):", c_r > c_b + 100)

print()
print("=== 5b. Route 2 causal signature: FXDelay wet/tail ===")
if load_ok:
    print(f"baseline tail: {t_b:.2f} dB | route tail: {t_r:.2f} dB | delta: {t_r-t_b:+.2f} dB")
    print("matches expected FXDelay signature (measurable delta):", abs(t_r-t_b) > 3.0)

print()
print("=== 6/7. Persistence: both routes survive Serum re-save ===")
if load_ok:
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta_r, body_r)
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    fd, tmp_out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    synth.save_state(tmp_out)
    _, resaved_body = codec.decode(vst3_state.unwrap_vc2(open(tmp_out,"rb").read()))
    survived_a = resaved_body[SLOT_A] == route_filter
    survived_b = resaved_body[SLOT_B] == route_delay
    print(f"{SLOT_A} survived exactly:", survived_a)
    print(f"{SLOT_B} survived exactly:", survived_b)
    print("BOTH routes survived:", survived_a and survived_b)
    os.remove(tmp_out)
