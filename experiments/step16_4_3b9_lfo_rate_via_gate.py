"""16.4.3b-9/10: revisit [6,0]'s identity using the now-understood gate
mechanism. Preset 630 exact body, Macro2 gate=100 (confirmed == ungated
[6,0]), LFO0 EXPLICITLY set to different real rates. Isolate the diff trace
(route present minus route absent) at each rate and check whether its
frequency content tracks the configured rate -- not final-audio FFT, which
already failed once."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
RATES = {"R1": 2.000405, "R2": 4.919910075711187, "R3": 7.932354}

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
real_body = d["bodies"][630]
meta, skel_body = bridge.capture_v8_skeleton(VST3)

def build(rate, add_route):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    b.update(copy.deepcopy(real_body))
    pathmerge.apply_path_value(b, "Macro2.plainParams.kParamValue", 100.0)  # gate fully open
    pathmerge.apply_path_value(b, "LFO0.plainParams",
                               {"kParamDefaultMode": 0.0, "kParamMode": "Free", "kParamRate": rate})
    if not add_route:
        b["ModSlot0"] = skel_body.get("ModSlot0", "default")
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

def analyze(diff_trace, win_samples, sr=SR, label=""):
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
    print(" [%s] FFT_peak=%.3fHz prominence=%.2f | autocorr=%.3fHz | std=%.5f" % (
        label, peak_freq, prominence, ac_peak_freq, float(np.std(diff_trace))))
    return peak_freq, ac_peak_freq

print("=== LFO0 rate sweep, via the confirmed gated route [6,27]/Macro2=100 ===")
for rname, rate in RATES.items():
    m_route, b_route = build(rate, add_route=True)
    m_noroute, b_noroute = build(rate, add_route=False)
    x_route = render(m_route, b_route)
    x_noroute = render(m_noroute, b_noroute)
    max_diff = float(np.max(np.abs(x_route - x_noroute)))
    trace_route, win = windowed_rms(x_route)
    trace_noroute, _ = windowed_rms(x_noroute)
    diff_trace = trace_route - trace_noroute
    print("rate=%s (%.4f): max|route-noroute|=%.5f" % (rname, rate, max_diff))
    analyze(diff_trace, win, label="rate=%.3f" % rate)
