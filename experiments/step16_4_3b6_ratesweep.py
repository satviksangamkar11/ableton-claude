"""16.4.3b-6a/6b/6c: independent FFT + autocorrelation on the isolated C-B
diff trace, then a controlled rate sweep for [6,0] (does the detected
modulation frequency track the configured LFO0 rate?), with [25,0] run at
one alternate rate as a negative control. All rates are real corpus values,
not invented. No claims/capabilities/findings modified."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
AMOUNT = 29.682552814483643
RATES = {"R1": 2.000405, "R2": 4.919910075711187, "R3": 7.932354}

def route(source):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': AMOUNT},
           'source': source}

meta, skel_body = bridge.capture_v8_skeleton(VST3)

def build(rate, add_route_source=None):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    pathmerge.apply_path_value(b, "LFO0.plainParams",
                               {'kParamDefaultMode': 0.0, 'kParamMode': 'Free', 'kParamRate': rate})
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
    return np.array([float(np.sqrt(np.mean(x[i*win:(i+1)*win]**2))) for i in range(n_windows)]), win

def analyze_diff(diff_trace, win_samples, sr=SR, label=""):
    n = len(diff_trace)
    trace_dt = win_samples / sr
    detr = diff_trace - np.polyval(np.polyfit(np.arange(n), diff_trace, 2), np.arange(n))
    windowed = detr * np.hanning(n)
    spec = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(n, d=trace_dt)
    search = spec[2:]
    peak_idx = int(np.argmax(search)) + 2 if len(search) else 0
    peak_freq = freqs[peak_idx] if peak_idx < len(freqs) else 0.0
    peak_power = spec[peak_idx] if peak_idx < len(spec) else 0.0
    background = np.median(np.delete(spec, [0, 1, peak_idx])) + 1e-12
    prominence = peak_power / background
    ac = np.correlate(detr, detr, mode="full")[n-1:]
    ac = ac / (ac[0] + 1e-12)
    ac_peak_lag = int(np.argmax(ac[3:n//2])) + 3 if n > 8 else 0
    ac_peak_freq = 1.0 / (ac_peak_lag * trace_dt) if ac_peak_lag > 0 else 0.0
    print(" [%s] FFT peak=%.3fHz prominence=%.2f | autocorr peak lag=%d samples -> %.3fHz | trace std=%.5f" % (
        label, peak_freq, prominence, ac_peak_lag, ac_peak_freq, float(np.std(diff_trace))))
    return peak_freq, prominence, ac_peak_freq

results = {}
print("=== 16.4.3b-6b: rate sweep for source=[6,0] ===")
for rname, rate in RATES.items():
    m_b, b_b = build(rate, add_route_source=None)
    m_c, b_c = build(rate, add_route_source=[6, 0])
    x_b = render(m_b, b_b)
    x_c = render(m_c, b_c)
    diff = x_c - x_b
    trace, win = windowed_rms(diff if False else x_c, 160)  # placeholder overwritten below
    trace_b, win_b = windowed_rms(x_b, 160)
    trace_c, win_c = windowed_rms(x_c, 160)
    diff_trace = trace_c - trace_b
    print("rate=%s (%.4f): max|C-B| audio=%.5f" % (rname, rate, float(np.max(np.abs(diff)))))
    peak_freq, prom, ac_freq = analyze_diff(diff_trace, win_b, label="source=6 rate=%.3f" % rate)
    results[("6", rname)] = {"rate": rate, "peak_freq": peak_freq, "prominence": prom, "ac_freq": ac_freq}

print()
print("=== 16.4.3b-6c: [25,0] at one alternate rate (negative control) ===")
for rname in ("R1", "R3"):
    rate = RATES[rname]
    m_b, b_b = build(rate, add_route_source=None)
    m_d, b_d = build(rate, add_route_source=[25, 0])
    x_b = render(m_b, b_b)
    x_d = render(m_d, b_d)
    diff = x_d - x_b
    print("rate=%s (%.4f) source=[25,0]: max|D-B| audio=%.8f  bit-identical=%s" % (
        rname, rate, float(np.max(np.abs(diff))), np.array_equal(x_b, x_d)))
    results[("25", rname)] = {"rate": rate, "max_diff": float(np.max(np.abs(diff)))}

print()
print("=== summary: does detected frequency track configured rate? ===")
for rname, rate in RATES.items():
    r = results[("6", rname)]
    print(" configured=%.3fHz -> FFT_peak=%.3fHz autocorr=%.3fHz prominence=%.2f" % (
        rate, r["peak_freq"], r["ac_freq"], r["prominence"]))

pickle.dump(results, open(r"D:/ableton claude/experiments/_rate_sweep_results.pkl", "wb"))
