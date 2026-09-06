"""Step 1: self-touch mechanical test. Reassign each ModSlot0-9 its own
already-present value via the exact deepcopy+reassignment mechanism used
in build_v8_state -- zero external object, zero value change."""
import sys, copy
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

meta, skeleton_body = bridge.capture_v8_skeleton(VST3)
body8 = copy.deepcopy(skeleton_body)

touched = []
for i in range(10):
    key = f"ModSlot{i}"
    body8[key] = copy.deepcopy(body8[key])  # self-touch: reassign own value
    touched.append(key)

print("self-touched keys:", touched)
print("body8 == original skeleton_body (value equality):", body8 == skeleton_body)

icomp = codec.encode(meta, body8)
blob = vst3_state.wrap_vc2(icomp)
fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
open(tmp, "wb").write(blob)

engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)
try:
    synth.load_state(tmp)
    print("LOAD: OK, no crash")
    synth.add_midi_note(60, 100, 0.0, 1.0)
    engine.load_graph([(synth, [])])
    engine.render(1.0)
    print("RENDER: OK")
except Exception as e:
    print("LOAD/RENDER: CRASH ->", type(e).__name__, e)
finally:
    os.remove(tmp)
