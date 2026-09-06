"""G4B -- semantics. Single-step: convert_preset_file() output goes straight
into load_state(). No double-wrapping this time."""
import dawdreamer as daw
import numpy as np
import serum2_preset_loader as loader
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def render_preset(preset_path, seconds=2.0, note=60, vel=100, note_len=1.0):
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    blob = loader.convert_preset_file(preset_path)   # already the full VC2! container
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    open(tmp, "wb").write(blob)
    try:
        synth.load_state(tmp)
    finally:
        os.remove(tmp)
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
    lo = float(np.sum(spec[(freqs>=20)&(freqs<250)]))
    hi = float(np.sum(spec[(freqs>=4000)&(freqs<20000)]))
    tot = float(np.sum(spec))+1e-12
    return dict(rms_db=20*np.log10(rms), centroid=centroid, lo_frac=lo/tot, hi_frac=hi/tot)

presets = {
    "wavetable":   r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset",
    "spectral":    r"D:\ableton claude\archive\golden_presets\spectral.SerumPreset",
    "granular":    r"D:\ableton claude\archive\golden_presets\granular.SerumPreset",
    "arp":         r"D:\ableton claude\archive\golden_presets\arp.SerumPreset",
    "multisample": r"D:\ableton claude\archive\golden_presets\multisample.SerumPreset",
}

results = {}
for name, path in presets.items():
    f = feats(render_preset(path))
    results[name] = f
    print(f"{name:<14} {f}")

print("\n=== VERDICT ===")
names = list(results)
all_same = all(results[names[0]] == results[n] for n in names[1:])
print("all five identical:", all_same)
for i in range(len(names)):
    for j in range(i+1, len(names)):
        a, b = results[names[i]], results[names[j]]
        d = abs(a["centroid"] - b["centroid"])
        print(f"  {names[i]:<12} vs {names[j]:<12}  centroid delta = {d:8.1f} Hz")
