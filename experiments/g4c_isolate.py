"""Isolate: does load_state() work for ANY state on this DawDreamer build,
independent of serum2-preset-loader entirely?"""
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def render(engine, synth, seconds=2.0, note=48, vel=110, note_len=1.5):
    synth.clear_midi()
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    return np.asarray(engine.get_audio())

def centroid(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    return float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))

engineA = daw.RenderEngine(SR, 512)
synthA = engineA.make_plugin_processor("serum", VST3)
paramsA = synthA.get_parameters_description()
def idxA(name): return next(p["index"] for p in paramsA if p["name"] == name)
synthA.set_parameter(idxA("Filter 1 On"), 1.0)
synthA.set_parameter(idxA("Filter 1 Freq"), 0.1)
a_audio = render(engineA, synthA)
a_centroid = centroid(a_audio)
print("A (mutated, direct render): centroid =", a_centroid)

fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synthA.save_state(tmp)
print("saved state size:", os.path.getsize(tmp))

engineB = daw.RenderEngine(SR, 512)
synthB = engineB.make_plugin_processor("serum", VST3)
b_before = centroid(render(engineB, synthB))
print("B (fresh, before load): centroid =", b_before)

synthB.load_state(tmp)
b_after_audio = render(engineB, synthB)
b_after = centroid(b_after_audio)
print("B (after load_state(A's saved file)): centroid =", b_after)
os.remove(tmp)

print("\n=== VERDICT ===")
print("B after-load matches A:", abs(b_after - a_centroid) < 1.0, f"(delta={abs(b_after-a_centroid):.2f} Hz)")
print("B changed from its own default:", abs(b_after - b_before) > 1.0, f"(delta={abs(b_after-b_before):.2f} Hz)")
