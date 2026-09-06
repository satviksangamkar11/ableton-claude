import sys; sys.path.insert(0, r"D:\ableton claude")
from serum2 import codec, vst3_state, bridge
import dawdreamer as daw
import tempfile, os, json

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

# Ground truth: Serum itself, told (via host param) to actually create a mod route
engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)
params = synth.get_parameters_description()
idx = lambda n: next(p["index"] for p in params if p["name"] == n)
synth.set_parameter(idx("Mod 1 Amount"), 0.7)
fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(tmp)
raw = open(tmp, "rb").read(); os.remove(tmp)
_, populated_v8_body = codec.decode(vst3_state.unwrap_vc2(raw))

print("=== NATIVE v8, ModSlot0, Mod 1 Amount=0.7 (Serum's own truth) ===")
print(json.dumps(populated_v8_body["ModSlot0"], indent=1, default=str))

# skeleton (default, untouched)
skeleton = bridge.capture_v8_skeleton(VST3)
print("\n=== SKELETON v8, ModSlot0 (default/empty) ===")
print(json.dumps(skeleton[1]["ModSlot0"], indent=1, default=str))

# v5 preset's ModSlot0
_, preset_body = codec.load_preset_file(r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset")
print("\n=== v5 PRESET, ModSlot0 (populated, from .SerumPreset) ===")
print(json.dumps(preset_body["ModSlot0"], indent=1, default=str))

print("\n=== key-set comparison ===")
def keyset(d):
    return set(d.keys()) if isinstance(d, dict) else set()
print("native-populated keys:", keyset(populated_v8_body["ModSlot0"]))
print("skeleton-empty keys:  ", keyset(skeleton[1]["ModSlot0"]))
print("v5-preset keys:       ", keyset(preset_body["ModSlot0"]))
