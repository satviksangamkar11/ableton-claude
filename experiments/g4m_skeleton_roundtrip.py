import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def render(engine, synth, seconds=2.0, note=60, vel=100, note_len=1.0):
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

print("Capturing genuine v8 skeleton...")
meta, body = bridge.capture_v8_skeleton(VST3)
print("meta:", meta)

print("\nRe-encoding through our own codec (zero modification)...")
reencoded_icomp = codec.encode(meta, body)
reencoded_blob = vst3_state.wrap_vc2(reencoded_icomp)

fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
open(tmp, "wb").write(reencoded_blob)

print("Attempting load into a FRESH Serum instance...")
engine = daw.RenderEngine(SR, 512)
synth = engine.make_plugin_processor("serum", VST3)
try:
    synth.load_state(tmp)
    print("LOAD: OK, no crash")
    audio_reencoded = render(engine, synth)
    c_reencoded = centroid(audio_reencoded)
    print("centroid (re-encoded skeleton):", c_reencoded)

    # compare against a truly untouched fresh default instance
    engine2 = daw.RenderEngine(SR, 512)
    synth2 = engine2.make_plugin_processor("serum", VST3)
    c_native = centroid(render(engine2, synth2))
    print("centroid (native untouched default):", c_native)
    print("MATCH:", abs(c_reencoded - c_native) < 5.0)

    # also verify decode(reencoded) == original body
    _, body_check = codec.decode(reencoded_icomp)
    print("decode(our re-encode) == original decoded body:", body_check == body)
except Exception as e:
    print("LOAD: CRASH ->", type(e).__name__, e)
finally:
    os.remove(tmp)
