"""16.4.3b-5: C ([6,0] route on top of confirmed-neutral B) and D ([25,0]
route on top of the same B) -- direct raw-trace diffs against B, since B's
absolute kernel readings are now known to carry a render-intrinsic artifact."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
REAL_LFO0_PLAINPARAMS = {'kParamDefaultMode': 0.0, 'kParamMode': 'Free',
                         'kParamRate': 4.919910075711187}
AMOUNT = 29.682552814483643

def route(source):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': AMOUNT},
           'source': source}

meta, skel_body = bridge.capture_v8_skeleton(VST3)

def build(add_route_source=None):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    pathmerge.apply_path_value(b, "LFO0.plainParams", copy.deepcopy(REAL_LFO0_PLAINPARAMS))
    if add_route_source is not None:
        pathmerge.apply_path_value(b, "ModSlot30", route(add_route_source))
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
    print("=== %s === overall RMS: %.6f" % (label, float(np.sqrt(np.mean(x**2)))))
    return x

meta_b, body_b = build(add_route_source=None)
meta_c, body_c = build(add_route_source=[6, 0])
meta_d, body_d = build(add_route_source=[25, 0])

x_b = render("B (explicit LFO0, no route)", meta_b, body_b)
x_c = render("C (explicit LFO0 + route source=[6,0])", meta_c, body_c)
x_d = render("D (explicit LFO0 + route source=[25,0])", meta_d, body_d)

print()
print("B == C bit-identical:", np.array_equal(x_b, x_c), " max abs diff:", float(np.max(np.abs(x_b - x_c))))
print("B == D bit-identical:", np.array_equal(x_b, x_d), " max abs diff:", float(np.max(np.abs(x_b - x_d))))
print("C == D bit-identical:", np.array_equal(x_c, x_d), " max abs diff:", float(np.max(np.abs(x_c - x_d))))

def windowed_rms(x, n_windows=80):
    win = len(x) // n_windows
    return np.array([float(np.sqrt(np.mean(x[i*win:(i+1)*win]**2))) for i in range(n_windows)])

trace_b, trace_c, trace_d = windowed_rms(x_b), windowed_rms(x_c), windowed_rms(x_d)
diff_cb = trace_c - trace_b
diff_db = trace_d - trace_b
print()
print("windowed-RMS diff trace C-B (first 30):", np.round(diff_cb[:30], 6))
print("windowed-RMS diff trace D-B (first 30):", np.round(diff_db[:30], 6))
print("std(C-B):", float(np.std(diff_cb)), " std(D-B):", float(np.std(diff_db)))
print("max|C-B|:", float(np.max(np.abs(diff_cb))), " max|D-B|:", float(np.max(np.abs(diff_db))))

pickle.dump({"x_b": x_b, "x_c": x_c, "x_d": x_d, "trace_b": trace_b, "trace_c": trace_c, "trace_d": trace_d},
           open(r"D:/ableton claude/experiments/_raw_check_bcd.pkl", "wb"))
