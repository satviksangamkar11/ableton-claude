"""16.4.3b-7: real-preset-backed ablation. Base = the ENTIRE real corpus
body (body_idx=630) used directly, no reconstruction. Only ModSlot0 is
varied; ModSlot1/ModSlot2 (other real routes), LFO0's real curve/mode,
Macro1/Macro2's real values, and everything else stay exactly as saved."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
real_body = d["bodies"][630]
meta, skel_body = bridge.capture_v8_skeleton(VST3)

def build(modslot0_override):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    b.update(copy.deepcopy(real_body))  # entire real body as base, verbatim
    if modslot0_override == "remove":
        b["ModSlot0"] = skel_body.get("ModSlot0", "default")
    else:
        pathmerge.apply_path_value(b, "ModSlot0.source", modslot0_override)
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

m_a, b_a = build([6, 27])   # A: original
m_b, b_b = build([6, 0])    # B: secondary zeroed
m_c, b_c = build("remove")  # C: route removed entirely

x_a = render(m_a, b_a)
x_b = render(m_b, b_b)
x_c = render(m_c, b_c)

def windowed_rms(x, n_windows=160):
    win = len(x) // n_windows
    return np.array([float(np.sqrt(np.mean(x[i*win:(i+1)*win]**2))) for i in range(n_windows)])

print("overall RMS: A(orig,[6,27])=%.6f  B([6,0])=%.6f  C(no route)=%.6f" % (
    float(np.sqrt(np.mean(x_a**2))), float(np.sqrt(np.mean(x_b**2))), float(np.sqrt(np.mean(x_c**2)))))
print()
print("A vs B: bit_identical=%s max|diff|=%.6f" % (np.array_equal(x_a, x_b), float(np.max(np.abs(x_a-x_b)))))
print("A vs C: bit_identical=%s max|diff|=%.6f" % (np.array_equal(x_a, x_c), float(np.max(np.abs(x_a-x_c)))))
print("B vs C: bit_identical=%s max|diff|=%.6f" % (np.array_equal(x_b, x_c), float(np.max(np.abs(x_b-x_c)))))

trace_a, trace_b, trace_c = windowed_rms(x_a), windowed_rms(x_b), windowed_rms(x_c)
print()
print("trace std: A=%.6f B=%.6f C=%.6f" % (float(np.std(trace_a)), float(np.std(trace_b)), float(np.std(trace_c))))
print("std(A-B) [effect of secondary index 27 vs 0]:", float(np.std(trace_a - trace_b)))
print("std(B-C) [effect of the route itself with secondary=0]:", float(np.std(trace_b - trace_c)))
print("std(A-C) [effect of the full original route]:", float(np.std(trace_a - trace_c)))

pickle.dump({"x_a": x_a, "x_b": x_b, "x_c": x_c}, open(r"D:/ableton claude/experiments/_real_preset_ablation.pkl", "wb"))
