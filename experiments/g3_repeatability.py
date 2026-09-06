"""G3 -- renderer repeatability / noise floor, on the exact G2-passing state
(Filter 1 enabled, mid cutoff) -- a simple, non-default but non-complex patch."""
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
    peak = float(np.max(np.abs(x)))
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    centroid = float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))
    lo = float(np.sum(spec[(freqs>=20)&(freqs<250)]))
    mid = float(np.sum(spec[(freqs>=250)&(freqs<4000)]))
    hi = float(np.sum(spec[(freqs>=4000)&(freqs<20000)]))
    tot = lo+mid+hi+1e-12
    return dict(rms_db=20*np.log10(rms), peak=peak, centroid=centroid,
                lo_frac=lo/tot, mid_frac=mid/tot, hi_frac=hi/tot)

N = 20
rows = []
for i in range(N):
    engine, synth = new_synth()
    params = synth.get_parameters_description()
    on_idx = next(p["index"] for p in params if p["name"] == "Filter 1 On")
    cut_idx = next(p["index"] for p in params if p["name"] == "Filter 1 Freq")
    synth.set_parameter(on_idx, 1.0)
    synth.set_parameter(cut_idx, 0.5)
    rows.append(feats(render(engine, synth)))

keys = rows[0].keys()
print(f"N={N} renders, identical state (Filter1 On, cutoff=0.5)\n")
print(f"{'metric':<10} {'mean':>12} {'std':>12} {'min':>12} {'max':>12} {'range':>12}")
for k in keys:
    vals = np.array([r[k] for r in rows])
    print(f"{k:<10} {vals.mean():12.4f} {vals.std():12.6f} {vals.min():12.4f} {vals.max():12.4f} {vals.max()-vals.min():12.6f}")
