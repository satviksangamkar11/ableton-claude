"""Test B: same process, replay the exact original g4i_bisect.py 6-step
family sequence in order, recording diagnostics per step."""
import sys, hashlib, os
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import tempfile

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
preset_path = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"

print("PID:", os.getpid())
skeleton = bridge.capture_v8_skeleton(VST3)

test_sets = [
    ("Global0 only", ["Global0"]),
    ("Env only", ["Env0","Env1","Env2","Env3"]),
    ("Oscillator only", ["Oscillator0","Oscillator1","Oscillator2","Oscillator3","Oscillator4"]),
    ("Filter only", ["Filter"]),
    ("ModSlot0-9 only", [f"ModSlot{i}" for i in range(10)]),
    ("ModSlot all 64", [f"ModSlot{i}" for i in range(64)]),
]

for iteration, (label, keys) in enumerate(test_sets):
    meta8, body8, transplanted = bridge.build_v8_state(preset_path, skeleton, module_prefixes=keys)
    icomp = codec.encode(meta8, body8)
    blob = vst3_state.wrap_vc2(icomp)
    h = hashlib.sha256(blob).hexdigest()[:16]

    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    open(tmp, "wb").write(blob)

    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    try:
        synth.load_state(tmp)
        synth.add_midi_note(60, 100, 0.0, 1.0)
        engine.load_graph([(synth, [])])
        engine.render(1.0)
        result = "OK"
    except Exception as e:
        result = f"CRASH: {type(e).__name__}: {e}"
    finally:
        os.remove(tmp)

    print(f"iter={iteration} label={label!r:22} transplanted={len(transplanted):3d} "
          f"state_len={len(blob):5d} sha256={h} result={result}")
