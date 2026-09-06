import sys, time
sys.path.insert(0, r"D:\ableton claude")
from serum2 import codec, vst3_state, bridge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
OUT = r"D:\ableton claude\experiments\gui_loaded_state2.bin"

# baseline: fresh default instance's A Octave value
be = daw.RenderEngine(44100, 512)
bs = be.make_plugin_processor("serum", VST3)
bp = bs.get_parameters_description()
oct_idx = next(p["index"] for p in bp if p["name"] == "A Octave")
default_octave = bs.get_parameter(oct_idx)
print("DEFAULT A Octave (normalized):", default_octave, flush=True)

engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)
print("Opening Serum GUI -- please load 'simple_wavetable.SerumPreset' via Serum's OWN browser, then close the window.", flush=True)
synth.open_editor()  # blocks until window closed
print("Editor closed. Reading host parameter...", flush=True)

after_octave = synth.get_parameter(oct_idx)
print("AFTER-CLOSE A Octave (normalized):", after_octave, flush=True)
print("Host parameter changed from default:", abs(after_octave - default_octave) > 1e-4, flush=True)

synth.save_state(OUT)
print("state saved ->", OUT, flush=True)

_, skel_body = bridge.capture_v8_skeleton(VST3)
raw = open(OUT, "rb").read()
_, gui_body = codec.decode(vst3_state.unwrap_vc2(raw))
print("full internal state identical to default:", gui_body == skel_body, flush=True)
print("Oscillator0 wavetable path:", gui_body.get("Oscillator0",{}).get("WTOsc0",{}).get("relativePathToWT"), flush=True)
