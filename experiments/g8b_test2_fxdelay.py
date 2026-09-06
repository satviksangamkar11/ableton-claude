import sys, copy
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
route1 = aardvark_body["ModSlot1"]

print("=== 1. Verify source ModSlot1 data ===")
print(route1)
assert route1["destModuleTypeString"] == "FXDelay" and route1["destModuleParamName"] == "kParamWet"

def build_state(include_route):
    meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
    body8["FXRack0"] = copy.deepcopy(aardvark_body["FXRack0"])  # make FXDelay exist, identical both arms
    if include_route:
        body8[TARGET_SLOT] = copy.deepcopy(route1)
    return meta8, body8

meta_r, body_r = build_state(True)
meta_b, body_b = build_state(False)

print()
print("=== 2/3. Verify content + divergence ===")
print("route slot contains exactly intended route:", body_r[TARGET_SLOT] == route1)
print("route state differs from baseline state:", body_r != body_b)

def render_tail_energy(meta8, body8, note=60, vel=100, note_len=0.15, total_seconds=2.0, tail_start=0.6):
    """Short plucked note -- dry signal decays fast, delay repeats persist into the tail window."""
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    try:
        synth.load_state(tmp)
        load_ok = True
    except Exception as e:
        os.remove(tmp)
        return None, f"CRASH: {type(e).__name__}: {e}"
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(total_seconds)
    audio = np.asarray(engine.get_audio())
    os.remove(tmp)
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    tail_idx = int(tail_start * SR)
    tail = x[tail_idx:]
    tail_rms = float(np.sqrt(np.mean(tail**2)) + 1e-12)
    tail_rms_db = 20*np.log10(tail_rms)
    return tail_rms_db, "OK"

print()
print("=== 4. Load Serum 2.0.21 (baseline + route) ===")
tail_baseline, res_b = render_tail_energy(meta_b, body_b)
print("baseline load/render:", res_b, "  tail_rms_db:", tail_baseline)
tail_route, res_r = render_tail_energy(meta_r, body_r)
print("route    load/render:", res_r, "  tail_rms_db:", tail_route)

print()
print("=== 5. Causal test: tail energy (delay repeats persisting after dry decay) ===")
if tail_baseline is not None and tail_route is not None:
    delta = tail_route - tail_baseline
    print(f"baseline tail energy: {tail_baseline:.2f} dB")
    print(f"route    tail energy: {tail_route:.2f} dB")
    print(f"delta: {delta:+.2f} dB")
    print("measurable difference (>3dB):", abs(delta) > 3.0)
    print("NOTE: not assuming sign direction -- amount=-22.16, measured delta reported as-is.")

print()
print("=== 6. Persistence: Serum re-save ===")
fd, tmp2 = tempfile.mkstemp(suffix=".bin"); os.close(fd)
bridge.write_state_file(tmp2, meta_r, body_r)
engine2 = daw.RenderEngine(SR, 512)
synth2 = engine2.make_plugin_processor("serum", VST3)
synth2.load_state(tmp2)
fd, tmp3 = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth2.save_state(tmp3)
_, resaved_body = codec.decode(vst3_state.unwrap_vc2(open(tmp3,"rb").read()))
survived = resaved_body[TARGET_SLOT] == route1
print("resaved ModSlot30:", resaved_body[TARGET_SLOT])
print("EXACT match:", survived)
os.remove(tmp2); os.remove(tmp3)
