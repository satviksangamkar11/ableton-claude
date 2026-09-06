import sys, time
sys.path.insert(0, r"D:\ableton claude")
from serum2 import codec, vst3_state
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
OUT = r"D:\ableton claude\experiments\gui_loaded_state.bin"

engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)
print("Opening Serum GUI...", flush=True)
synth.open_editor()
print("Window should be open. Load 'simple_wavetable.SerumPreset' via Serum's own browser now.", flush=True)
print("Waiting 60 seconds...", flush=True)
time.sleep(60)
synth.save_state(OUT)
print("Captured state ->", OUT, flush=True)
