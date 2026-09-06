"""16.4.3b-7: secondary-reference causal test. Preset 32 exact body, only
ModSlot0.source and Macro4.plainParams.kParamValue vary. Explicit 0/50/100,
never 'default'."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
real_body = d["bodies"][32]
meta, skel_body = bridge.capture_v8_skeleton(VST3)
print("Macro4 as-saved:", real_body.get("Macro4"))

def build(source, macro4_value):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    b.update(copy.deepcopy(real_body))
    if source == "remove":
        b["ModSlot0"] = skel_body.get("ModSlot0", "default")
    else:
        pathmerge.apply_path_value(b, "ModSlot0.source", source)
    pathmerge.apply_path_value(b, "Macro4.plainParams.kParamValue", macro4_value)
    return m, b

def render(m, b, seconds=2.0, note=48, vel=110, note_len=1.8):
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
    return audio.mean(axis=0) if audio.ndim == 2 else audio

def windowed_rms(x, n_windows=160):
    win = len(x) // n_windows
    return np.array([float(np.sqrt(np.mean(x[i*win:(i+1)*win]**2))) for i in range(n_windows)])

cases = {
    "A [6,29] Macro4=0":   ([6, 29], 0.0),
    "B [6,29] Macro4=50":  ([6, 29], 50.0),
    "C [6,29] Macro4=100": ([6, 29], 100.0),
    "D [6,0]  Macro4=100": ([6, 0], 100.0),
    "E no-route Macro4=100": ("remove", 100.0),
}

audio = {}
for label, (source, macro4_val) in cases.items():
    m, b = build(source, macro4_val)
    audio[label] = render(m, b)

x_e = audio["E no-route Macro4=100"]
print()
print("=== results vs E (no-route reference) ===")
for label in cases:
    x = audio[label]
    diff = x - x_e
    trace_diff = windowed_rms(x) - windowed_rms(x_e)
    print("%-24s max|diff vs E|=%.6f  overall_rms=%.6f  trace_std_diff=%.6f  bit_identical_to_E=%s" % (
        label, float(np.max(np.abs(diff))), float(np.sqrt(np.mean(x**2))),
        float(np.std(trace_diff)), np.array_equal(x, x_e)))

pickle.dump(audio, open(r"D:/ableton claude/experiments/_gating_dose_response.pkl", "wb"))
