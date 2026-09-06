import sys; sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def render_state_file(state_path, seconds=2.0, note=60, vel=100, note_len=1.0):
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(state_path)
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

print("Capturing v8 skeleton from live Serum 2.0.21...")
skeleton = bridge.capture_v8_skeleton(VST3)
print("skeleton meta:", skeleton[0])

presets = {
    "wavetable": r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset",
    "spectral":  r"D:\ableton claude\archive\golden_presets\spectral.SerumPreset",
}

results = {}
for name, path in presets.items():
    meta8, body8, transplanted = bridge.build_v8_state(path, skeleton)
    print(f"\n{name}: transplanted modules = {transplanted}")
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    audio = render_state_file(tmp)
    os.remove(tmp)
    f = feats(audio)
    results[name] = f
    print(f"  {name}: {f}")

print("\n=== VERDICT ===")
d = abs(results["wavetable"]["centroid"] - results["spectral"]["centroid"])
print("centroid delta:", d, "Hz")
print("distinct:", d > 5.0)
