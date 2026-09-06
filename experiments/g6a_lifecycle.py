"""Step 5: does routing load/render through a separate function (matching
g4i_bisect.py's try_load() structure) reproduce anything, using the exact
same already-verified state bytes as g5d?"""
import sys, os
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import tempfile

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

def try_load(state_path):
    """Matches g4i_bisect.py's exact function structure -- engine/synth as
    local variables inside a function frame, cleared on return."""
    engine = daw.RenderEngine(44100, 512)
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

for i, (label, keys) in enumerate(test_sets):
    meta8, body8, transplanted = bridge.build_v8_state(preset_path, skeleton, module_prefixes=keys)
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    try:
        result = try_load(tmp)
    except Exception as e:
        result = f"CRASH: {type(e).__name__}: {e}"
    finally:
        os.remove(tmp)
    print(f"iter={i} label={label!r:22} transplanted={len(transplanted):3d} result={result}")
