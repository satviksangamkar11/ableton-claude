"""16.4.3c: replacement discriminator. Long sustained note (4.5s render),
per-window spectral centroid trace (filter-sensitive, not RMS-envelope),
zero-crossing rate of the detrended trace as the periodicity signature --
NOT an FFT peak search, which was just shown to manufacture frequencies
from analysis geometry alone. First establishes the observable responds to
known static cutoff movement (16.4.3c-1), then the rate experiment
(16.4.3c-2/3) with negative controls (16.4.3c-4)."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
RATES = {"R1": 2.000405, "R2": 4.919910075711187, "R3": 7.932354}
N_WINDOWS = 200
RENDER_SECONDS = 4.5
NOTE_LEN = 4.0

meta, skel_body = bridge.capture_v8_skeleton(VST3)

def route(source, amount=29.682552814483643):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': amount}, 'source': source}

def build(rate, add_route_source, filter_freq_override=None):
    m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
    if rate is not None:
        pathmerge.apply_path_value(b, "LFO0.plainParams",
                                   {"kParamDefaultMode": 0.0, "kParamMode": "Free", "kParamRate": rate})
    if add_route_source is not None:
        pathmerge.apply_path_value(b, "ModSlot30", route(add_route_source))
    if filter_freq_override is not None:
        pathmerge.apply_path_value(b, "VoiceFilter0.plainParams.kParamFreq", filter_freq_override)
    return m, b

def render(m, b, seconds=RENDER_SECONDS, note=48, vel=110, note_len=NOTE_LEN):
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

def per_window_centroid(x, n_windows=N_WINDOWS, sr=SR):
    win = len(x) // n_windows
    centroids = []
    for i in range(n_windows):
        seg = x[i*win:(i+1)*win]
        if len(seg) < 64:
            centroids.append(centroids[-1] if centroids else 0.0)
            continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0/sr)
        c = float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))
        centroids.append(c)
    return np.array(centroids), win

def signature(trace):
    n = len(trace)
    detr = trace - np.polyval(np.polyfit(np.arange(n), trace, 2), np.arange(n))
    amp_std = float(np.std(detr))
    mean_val = np.mean(detr)
    signs = np.sign(detr - mean_val)
    signs[signs == 0] = 1
    zero_crossings = int(np.sum(np.abs(np.diff(signs)) > 0))
    return amp_std, zero_crossings

print("=== 16.4.3c-1: does the centroid observable respond to KNOWN static cutoff movement? ===")
m_base, b_base = build(None, None)
m_shift, b_shift = build(None, None, filter_freq_override=2000.0)
x_base = render(m_base, b_base)
x_shift = render(m_shift, b_shift)
c_base, win = per_window_centroid(x_base)
c_shift, _ = per_window_centroid(x_shift)
print(" mean centroid base=%.2fHz  shifted(freq=2000)=%.2fHz  delta=%.2fHz" % (
    np.mean(c_base), np.mean(c_shift), np.mean(c_shift)-np.mean(c_base)))
print(" observable responds:", abs(np.mean(c_shift)-np.mean(c_base)) > 50)

print()
print("=== 16.4.3c-2/3: rate experiment for [6,0] -- amp_std and zero-crossing-rate vs configured rate ===")
results = {}
for rname, rate in RATES.items():
    m, b = build(rate, [6, 0])
    x = render(m, b)
    trace, win = per_window_centroid(x)
    amp_std, zc = signature(trace)
    zc_rate_hz = zc / (2 * NOTE_LEN)  # each full cycle crosses the mean twice
    print(" [6,0] rate=%s (%.4f): amp_std=%.3f zero_crossings=%d -> zc_rate=%.3fHz" % (
        rname, rate, amp_std, zc, zc_rate_hz))
    results[("6,0", rname)] = {"rate": rate, "amp_std": amp_std, "zc": zc, "zc_rate_hz": zc_rate_hz}

print()
print("=== 16.4.3c-4: negative controls at the SAME rates ===")
for rname, rate in RATES.items():
    for label, source in (("[25,0]", [25, 0]), ("no-route", None)):
        m, b = build(rate, source)
        x = render(m, b)
        trace, win = per_window_centroid(x)
        amp_std, zc = signature(trace)
        print(" %-10s rate=%s: amp_std=%.3f zero_crossings=%d" % (label, rname, amp_std, zc))
        results[(label, rname)] = {"rate": rate, "amp_std": amp_std, "zc": zc}

pickle.dump(results, open(r"D:/ableton claude/experiments/_replacement_discriminator_results.pkl", "wb"))
