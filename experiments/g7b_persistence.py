import sys, copy
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
AARDVARK = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"

skeleton = bridge.capture_v8_skeleton(VST3)
_, aardvark_body = codec.load_preset_file(AARDVARK)
real_route = aardvark_body["ModSlot0"]

meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
body8["ModSlot0"] = copy.deepcopy(real_route)

fd, tmp_in = tempfile.mkstemp(suffix=".bin"); os.close(fd)
bridge.write_state_file(tmp_in, meta8, body8)

# load our generated state, then ask Serum ITSELF to re-save it
engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)
synth.load_state(tmp_in)

fd, tmp_out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(tmp_out)

resaved = open(tmp_out, "rb").read()
resaved_icomp = vst3_state.unwrap_vc2(resaved)
resaved_meta, resaved_body = codec.decode(resaved_icomp)

print("Serum's own re-save -- ModSlot0:")
print(" ", resaved_body["ModSlot0"])
print()
print("What we loaded (Aardvark's real route):")
print(" ", real_route)
print()

survived = resaved_body["ModSlot0"] == real_route
print("EXACT match:", survived)

if not survived:
    a, b = real_route, resaved_body["ModSlot0"]
    for k in set(a) | set(b):
        if a.get(k) != b.get(k):
            print(f"  DIFFERS at '{k}': loaded={a.get(k)!r}  resaved={b.get(k)!r}")

os.remove(tmp_in); os.remove(tmp_out)
