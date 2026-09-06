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

skeleton = bridge.capture_v8_skeleton(VST3)
_, aardvark_body = codec.load_preset_file(AARDVARK)
real_route = aardvark_body["ModSlot0"]
print("Route to transplant:", real_route)

print()
print("=== 1. Verify ModSlot30 was actually empty ===")
print("skeleton[ModSlot30]:", skeleton[1][TARGET_SLOT])
was_empty = skeleton[1][TARGET_SLOT] == {"plainParams": "default"}
print("was empty:", was_empty)

print()
print("=== 2/3. Build state, verify content + divergence ===")
meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
body8[TARGET_SLOT] = copy.deepcopy(real_route)
contains_intended = body8[TARGET_SLOT] == real_route
differs_from_skeleton = body8[TARGET_SLOT] != skeleton[1][TARGET_SLOT]
print("generated state contains exactly the intended route:", contains_intended)
print("generated state differs from skeleton at that slot:", differs_from_skeleton)

skel_hash = hashlib.sha256(codec.encode(*skeleton)).hexdigest()[:16]
mut_hash = hashlib.sha256(codec.encode(meta8, body8)).hexdigest()[:16]
print("skeleton hash:", skel_hash, "| mutated hash:", mut_hash, "| differ:", skel_hash != mut_hash)

fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
bridge.write_state_file(tmp, meta8, body8)

print()
print("=== 4. Load Serum 2.0.21 ===")
def render_windows(engine, synth, n_windows=8, seconds=2.0, note=48, vel=110, note_len=1.8):
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    audio = np.asarray(engine.get_audio())
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    win = len(x)//n_windows
    out = []
    for i in range(n_windows):
        seg = x[i*win:(i+1)*win]
        if len(seg) < 64: continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg*np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0/SR)
        out.append(float(np.sum(freqs*spec)/(np.sum(spec)+1e-12)))
    return out

load_ok = True
try:
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    print("LOAD: OK")
except Exception as e:
    load_ok = False
    print("LOAD: CRASH ->", type(e).__name__, e)

print()
print("=== 5. Causal audio test (VoiceFilter cutoff signature) ===")
if load_ok:
    params = synth.get_parameters_description()
    on_idx = next(p["index"] for p in params if p["name"] == "Filter 1 On")
    synth.set_parameter(on_idx, 1.0)
    c_route = render_windows(engine, synth)
    print("route-present centroids:", [round(c,1) for c in c_route])

    # baseline: default ModSlot30 (no route), same everything else
    meta_b, body_b = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
    fd2, tmp_b = tempfile.mkstemp(suffix=".bin"); os.close(fd2)
    bridge.write_state_file(tmp_b, meta_b, body_b)
    engine_b = daw.RenderEngine(SR, 512)
    synth_b = engine_b.make_plugin_processor("serum", VST3)
    synth_b.load_state(tmp_b)
    on_idx_b = next(p["index"] for p in synth_b.get_parameters_description() if p["name"] == "Filter 1 On")
    synth_b.set_parameter(on_idx_b, 1.0)
    c_baseline = render_windows(engine_b, synth_b)
    os.remove(tmp_b)
    print("baseline centroids:", [round(c,1) for c in c_baseline])

    mean_route, mean_baseline = np.mean(c_route), np.mean(c_baseline)
    print(f"mean route={mean_route:.1f}  mean baseline={mean_baseline:.1f}")
    print("matches expected signature (route > baseline, ~same magnitude as ModSlot0 test ~946 vs ~349):",
          mean_route > mean_baseline)

print()
print("=== 6/7. Persistence: Serum's own re-save ===")
if load_ok:
    fd3, tmp_out = tempfile.mkstemp(suffix=".bin"); os.close(fd3)
    synth.save_state(tmp_out)
    resaved_meta, resaved_body = codec.decode(vst3_state.unwrap_vc2(open(tmp_out,"rb").read()))
    survived = resaved_body[TARGET_SLOT] == real_route
    print("resaved ModSlot30:", resaved_body[TARGET_SLOT])
    print("EXACT match with intended route:", survived)
    os.remove(tmp_out)

os.remove(tmp)
