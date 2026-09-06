"""16.4.3b-6: source[1] semantics -- smallest controlled matrix around the
known-discriminating [6,0]: [6,0], [6,1], [25,0], [25,1]. Raw-audio diff
against no-route baseline as first discriminator (bit-identical / nonzero-
static / nonzero-time-varying). No claims/capabilities/findings touched."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
AMOUNT = 29.682552814483643
LFO0_CFG = {'kParamDefaultMode': 0.0, 'kParamMode': 'Free', 'kParamRate': 4.919910075711187}

def route(source):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': AMOUNT},
           'source': source}

meta, skel_body = bridge.capture_v8_skeleton(VST3)

def build(add_route_source=None):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    pathmerge.apply_path_value(b, "LFO0.plainParams", copy.deepcopy(LFO0_CFG))
    if add_route_source is not None:
        pathmerge.apply_path_value(b, "ModSlot30", route(add_route_source))
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

m_base, b_base = build(add_route_source=None)
x_base = render(m_base, b_base)

results = {}
for source in ([6, 0], [6, 1], [25, 0], [25, 1]):
    m, b = build(add_route_source=source)
    x = render(m, b)
    diff = x - x_base
    bit_identical = np.array_equal(x, x_base)
    max_diff = float(np.max(np.abs(diff)))
    trace_diff = windowed_rms(x) - windowed_rms(x_base)
    std_diff = float(np.std(trace_diff))
    # classify: bit-identical / nonzero-static (diff nearly constant across windows) / time-varying
    if bit_identical:
        cls = "BIT_IDENTICAL"
    elif std_diff < 1e-5:
        cls = "NONZERO_STATIC"
    else:
        cls = "NONZERO_TIME_VARYING"
    print("source=%s: bit_identical=%s max|diff|=%.6f trace_std=%.6f -> %s" % (
        source, bit_identical, max_diff, std_diff, cls))
    results[tuple(source)] = {"bit_identical": bit_identical, "max_diff": max_diff,
                              "trace_std": std_diff, "classification": cls}

pickle.dump(results, open(r"D:/ableton claude/experiments/_source1_matrix_results.pkl", "wb"))
