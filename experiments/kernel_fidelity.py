"""Step 5a: extraction fidelity. Does each reconstructed kernel reproduce the
ORIGINAL script's behaviour on shared reference buffers?

The originals combined render+measure, so we replicate their measurement half
inline here exactly as written, and compare against the extracted artifact.
"""
import sys
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2.evidence.kernels import (windowed_mean_centroid, wholesignal_centroid,
                                     tail_rms_db)

SR = 44100
TOL_REL = 1e-12


# ---- originals, transcribed verbatim from the historical scripts ----
def orig_g7a_render_windows(x, n_windows=8):
    """g7a_causality.render_windows measurement half + call-site np.mean."""
    win = len(x) // n_windows
    centroids = []
    for i in range(n_windows):
        seg = x[i*win:(i+1)*win]
        if len(seg) < 64: continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0/SR)
        centroids.append(float(np.sum(freqs*spec)/(np.sum(spec)+1e-12)))
    return float(np.mean(centroids))


def orig_g8a_render_windows(x, n_windows=8):
    """g8a_test1_slot30.render_windows measurement half + call-site np.mean."""
    win = len(x)//n_windows
    out = []
    for i in range(n_windows):
        seg = x[i*win:(i+1)*win]
        if len(seg) < 64: continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg*np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0/SR)
        out.append(float(np.sum(freqs*spec)/(np.sum(spec)+1e-12)))
    return float(np.mean(out))


def orig_g8e_render_centroid(x):
    """g8e_test3_coexistence.render_centroid measurement half."""
    n = len(x)
    spec = np.abs(np.fft.rfft(x*np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    return float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))


def orig_g8b_render_tail_energy(x, tail_start=0.6):
    """g8b_test2_fxdelay.render_tail_energy measurement half."""
    tail_idx = int(tail_start * SR)
    tail = x[tail_idx:]
    tail_rms = float(np.sqrt(np.mean(tail**2)) + 1e-12)
    return 20*np.log10(tail_rms)


def orig_g8d_render_tail(x, tail_start=0.6):
    """g8d_test2_full_gate.render_tail measurement half."""
    tail = x[int(tail_start*SR):]
    return 20*np.log10(float(np.sqrt(np.mean(tail**2)) + 1e-12))


# ---- reference buffer set: spans magnitudes, spectra, and edge cases ----
rng = np.random.default_rng(20260903)
n = int(2.0 * SR)
t = np.arange(n) / SR
REFERENCE_BUFFERS = {
    "silence":        np.zeros(n),
    "dc":             np.ones(n) * 0.5,
    "sine_100hz":     0.8*np.sin(2*np.pi*100*t),
    "sine_5khz":      0.3*np.sin(2*np.pi*5000*t),
    "white_noise":    rng.normal(0, 0.2, n),
    "pink_ish":       np.cumsum(rng.normal(0, 0.01, n)),
    "decaying_pluck": 0.9*np.exp(-6*t)*np.sin(2*np.pi*220*t),
    "near_clipping":  np.clip(3.0*np.sin(2*np.pi*440*t), -0.999, 0.999),
    "stereo":         np.vstack([0.5*np.sin(2*np.pi*300*t), 0.5*np.sin(2*np.pi*900*t)]),
}


def compare(label, original_fn, kernel_fn):
    rows, ok = [], True
    for name, buf in REFERENCE_BUFFERS.items():
        x = buf.mean(axis=0) if buf.ndim == 2 else buf
        a = original_fn(x)
        b = kernel_fn(buf)
        if np.isnan(a) and np.isnan(b):
            match = True; rel = 0.0
        else:
            rel = abs(b - a) / max(1e-12, abs(a))
            match = rel <= TOL_REL
        ok &= match
        rows.append((name, a, b, rel, match))
    print("=== %s ===" % label)
    for name, a, b, rel, match in rows:
        print("  %-16s orig=%14.6f  kernel=%14.6f  rel=%.2e  %s"
              % (name, a, b, rel, "OK" if match else "MISMATCH"))
    print("  -> %s\n" % ("FIDELITY PASS" if ok else "FIDELITY FAIL"))
    return ok


results = {}
results["g7a -> windowed_mean_centroid"] = compare(
    "g7a.render_windows  vs  windowed_mean_centroid",
    orig_g7a_render_windows, windowed_mean_centroid.kernel)
results["g8a -> windowed_mean_centroid"] = compare(
    "g8a.render_windows  vs  windowed_mean_centroid",
    orig_g8a_render_windows, windowed_mean_centroid.kernel)
results["g8e -> wholesignal_centroid"] = compare(
    "g8e.render_centroid  vs  wholesignal_centroid",
    orig_g8e_render_centroid, wholesignal_centroid.kernel)
results["g8b -> tail_rms_db"] = compare(
    "g8b.render_tail_energy  vs  tail_rms_db",
    orig_g8b_render_tail_energy, tail_rms_db.kernel)
results["g8d -> tail_rms_db"] = compare(
    "g8d.render_tail  vs  tail_rms_db",
    orig_g8d_render_tail, tail_rms_db.kernel)

print("=== STEP 5a: EXTRACTION FIDELITY ===")
for k, v in results.items():
    print("  %-34s %s" % (k, "PASS" if v else "FAIL"))
print()
print("ALL EXTRACTION FIDELITY:", "PASS" if all(results.values()) else "FAIL")
sys.exit(0 if all(results.values()) else 1)
