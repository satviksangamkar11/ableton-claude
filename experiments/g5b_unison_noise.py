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

def feats(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    rms = float(np.sqrt(np.mean(x**2)) + 1e-12)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    centroid = float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))
    return dict(rms_db=20*np.log10(rms), centroid=centroid)

N = 20
rows = []
for i in range(N):
    engine, synth = new_synth()
    params = synth.get_parameters_description()
    def idx(name): return next(p["index"] for p in params if p["name"] == name)
    synth.set_parameter(idx("A Unison"), 1.0)        # max voices
    synth.set_parameter(idx("A Uni Detune"), 0.5)
    synth.set_parameter(idx("A Uni Rand Start"), 1.0) # randomized phase start -- the suspect
    synth.set_parameter(idx("Filter 1 On"), 1.0)
    synth.set_parameter(idx("Filter 1 Freq"), 0.5)
    rows.append(feats(render(engine, synth)))

for k in rows[0]:
    vals = np.array([r[k] for r in rows])
    print(f"{k:<10} mean={vals.mean():10.4f}  std={vals.std():10.6f}  range={vals.max()-vals.min():10.6f}")
