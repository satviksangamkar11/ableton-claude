"""Test A: fresh process, single RenderEngine, single Serum instance,
exact simple_wavetable ModSlot0-9 transplant, load, render."""
import sys, hashlib, os
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import tempfile

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
preset_path = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"

print("PID:", os.getpid())
skeleton = bridge.capture_v8_skeleton(VST3)
meta8, body8, transplanted = bridge.build_v8_state(preset_path, skeleton, module_prefixes=[f"ModSlot{i}" for i in range(10)])
icomp = codec.encode(meta8, body8)
blob = vst3_state.wrap_vc2(icomp)
h = hashlib.sha256(blob).hexdigest()
print(f"iteration=0 transplanted={len(transplanted)} state_len={len(blob)} state_sha256={h[:16]}")

fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
open(tmp, "wb").write(blob)

engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)
try:
    synth.load_state(tmp)
    load_result = "OK"
    synth.add_midi_note(60, 100, 0.0, 1.0)
    engine.load_graph([(synth, [])])
    engine.render(1.0)
    render_result = "OK"
except Exception as e:
    load_result = f"CRASH: {type(e).__name__}: {e}"
    render_result = "N/A"
finally:
    os.remove(tmp)

print("load_result:", load_result)
print("render_result:", render_result)
