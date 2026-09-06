"""G5 (pulled forward as a cheap sanity check) -- does the zero-noise result
from a simple direct-parameter state hold for a complex, unison/granular-heavy
patch? Uses raw set_parameter on unison/voice-count params (no loader needed
for this check) to approximate 'complex' engagement, since G4 loader isn't
proven yet."""
import dawdreamer as daw
import numpy as np

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def new_synth():
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    return engine, synth

def render(engine, synth, seconds=2.0, note=48, vel=110, note_len=1.5):
    synth.clear_midi()
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    return np.asarray(engine.get_audio())

def rms_db(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    return 20*np.log10(float(np.sqrt(np.mean(x**2)) + 1e-12))

engine0, synth0 = new_synth()
params = synth0.get_parameters_description()
unison_params = [p for p in params if "Unison" in p["name"] or "Uni" in p["name"]]
print("Unison-related params found:")
for p in unison_params[:20]:
    print(" ", p["index"], p["name"])
