import sys; sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def try_load(state_path):
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(state_path)
    synth.add_midi_note(60, 100, 0.0, 1.0)
    engine.load_graph([(synth, [])])
    engine.render(1.0)
    return "OK"

skeleton = bridge.capture_v8_skeleton(VST3)
preset_path = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"

test_sets = [
    ("Global0 only", ["Global0"]),
    ("Env only", ["Env0","Env1","Env2","Env3"]),
    ("Oscillator only", ["Oscillator0","Oscillator1","Oscillator2","Oscillator3","Oscillator4"]),
    ("Filter only", ["Filter"]),
    ("ModSlot0-9 only", [f"ModSlot{i}" for i in range(10)]),
    ("ModSlot all 64", [f"ModSlot{i}" for i in range(64)]),
]

for label, keys in test_sets:
    meta8, body8, transplanted = bridge.build_v8_state(preset_path, skeleton, module_prefixes=keys)
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    try:
        result = try_load(tmp)
        print(f"{label:<20} transplanted={len(transplanted):3d}  -> {result}")
    except Exception as e:
        print(f"{label:<20} transplanted={len(transplanted):3d}  -> CRASH: {type(e).__name__}: {e}")
    finally:
        os.remove(tmp)

print("\n--- narrowing within ModSlot ---")
for i in range(10):
    keys = [f"ModSlot{i}"]
    meta8, body8, transplanted = bridge.build_v8_state(preset_path, skeleton, module_prefixes=keys)
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    try:
        try_load(tmp)
        print(f"ModSlot{i:<3} transplanted={len(transplanted)} -> OK")
    except Exception as e:
        print(f"ModSlot{i:<3} transplanted={len(transplanted)} -> CRASH: {e}")
        # inspect what's actually in this slot vs skeleton's version
        _, preset_body = codec.load_preset_file(preset_path)
        print("   preset ModSlot%d:" % i, preset_body.get(f"ModSlot{i}"))
        print("   skeleton ModSlot%d:" % i, skeleton[1].get(f"ModSlot{i}"))
    finally:
        os.remove(tmp)
