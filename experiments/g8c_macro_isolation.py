import sys, copy
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec
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
fxrack0 = aardvark_body["FXRack0"]

def build_state(include_route):
    meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
    body8["FXRack0"] = copy.deepcopy(fxrack0)
    if include_route:
        body8[TARGET_SLOT] = copy.deepcopy(route1)
    return meta8, body8

def render_tail(meta8, body8, macro_host_name, macro_value, note=60, vel=100, note_len=0.15, total_seconds=2.0, tail_start=0.6):
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    idx = next(p["index"] for p in synth.get_parameters_description() if p["name"] == macro_host_name)
    synth.set_parameter(idx, macro_value)
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(total_seconds)
    audio = np.asarray(engine.get_audio())
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    tail = x[int(tail_start*SR):]
    return 20*np.log10(float(np.sqrt(np.mean(tail**2)) + 1e-12))

meta_r, body_r = build_state(True)
meta_b, body_b = build_state(False)

print(f"{'host param':<12} {'internal key':<10} {'baseline tail dB':>18} {'route tail dB':>16} {'delta':>8}")
for i in range(8):
    host_name = f"Macro {i+1}"
    internal_key = f"Macro{i}"
    tb = render_tail(meta_b, body_b, host_name, 1.0)
    tr = render_tail(meta_r, body_r, host_name, 1.0)
    delta = tr - tb
    flag = "  <-- CANDIDATE" if abs(delta) > 3.0 else ""
    print(f"{host_name:<12} {internal_key:<10} {tb:18.2f} {tr:16.2f} {delta:+8.2f}{flag}")
