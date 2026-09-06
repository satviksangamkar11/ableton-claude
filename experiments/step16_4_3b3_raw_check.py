"""16.4.3b-3/4: reproduce the anomalous State B (explicit LFO0, NO route)
exactly, render it, and inspect the raw audio directly -- not just the
derived kernel number -- against true untouched State A."""
import sys, copy, tempfile, os
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
REAL_LFO0_PLAINPARAMS = {'kParamDefaultMode': 0.0, 'kParamMode': 'Free',
                         'kParamRate': 4.919910075711187}

meta, skel_body = bridge.capture_v8_skeleton(VST3)

def build(explicit_lfo0: bool):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    if explicit_lfo0:
        pathmerge.apply_path_value(b, "LFO0.plainParams", copy.deepcopy(REAL_LFO0_PLAINPARAMS))
    return m, b

def render(label, m, b, seconds=2.0, note=48, vel=110, note_len=1.8):
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, m, b)
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    params = synth.get_parameters_description()
    on_idx = next(p["index"] for p in params if p["name"] == "Filter 1 On")
    synth.set_parameter(on_idx, 1.0)
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    audio = np.asarray(engine.get_audio())
    os.remove(tmp)
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    print("=== %s ===" % label)
    print(" audio shape:", audio.shape, "nonzero samples:", np.count_nonzero(x), "/", len(x))
    print(" overall RMS:", float(np.sqrt(np.mean(x**2))))
    print(" max abs:", float(np.max(np.abs(x))))
    return x

meta_a, body_a = build(explicit_lfo0=False)
meta_b, body_b = build(explicit_lfo0=True)
print("State A LFO0:", body_a.get("LFO0"))
print("State B LFO0:", body_b.get("LFO0"))
print()

x_a = render("State A (untouched skeleton, no route)", meta_a, body_a)
x_b = render("State B (explicit LFO0 Free/rate=4.92, no route)", meta_b, body_b)

print()
print("=== raw windowed RMS trace (80 windows, matching kernel geometry) ===")
def windowed_rms(x, n_windows=80):
    win = len(x) // n_windows
    return np.array([float(np.sqrt(np.mean(x[i*win:(i+1)*win]**2))) for i in range(n_windows)])

trace_a = windowed_rms(x_a)
trace_b = windowed_rms(x_b)
print("State A trace (first 20):", np.round(trace_a[:20], 5))
print("State B trace (first 20):", np.round(trace_b[:20], 5))
print("State A trace std/mean ratio:", float(np.std(trace_a)/(np.mean(trace_a)+1e-12)))
print("State B trace std/mean ratio:", float(np.std(trace_b)/(np.mean(trace_b)+1e-12)))
print("A == B bit-identical:", np.array_equal(x_a, x_b))
print("max abs diff A vs B:", float(np.max(np.abs(x_a - x_b))))

import pickle
pickle.dump({"x_a": x_a, "x_b": x_b, "trace_a": trace_a, "trace_b": trace_b},
           open(r"D:/ableton claude/experiments/_raw_check_ab.pkl", "wb"))
