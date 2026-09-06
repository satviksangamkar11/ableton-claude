"""Kernel: zero-crossing rate of a detrended per-window spectral-centroid
trace, over a LONG sustained render.

Built for 16.4.3c after the previous FFT-peak-picking discriminator
(modulation_frequency_hz) was directly shown to manufacture a "detected
frequency" from analysis geometry alone (constant window count -> constant
reported peak, REGARDLESS of the underlying audio -- see 16.4.3b-11/12: the
peak always landed on the algorithm's own lowest searchable FFT bin whenever
the residual spectrum was low-frequency-dominated, which any note-envelope
residual is, real modulation or not).

This kernel avoids FFT peak-search entirely. It counts how many times a
long-run centroid trace crosses its own (detrended) mean -- a monotonic,
model-free timescale signature that does not require picking a spectral bin.
Validated (16.4.3c-1) to respond strongly to a KNOWN static filter-cutoff
change (delta ~3000Hz on a ~300Hz baseline), and (16.4.3c-2/3/4) to increase
monotonically with configured LFO0 rate while two independent negative
controls (no route, source=[25,0]) stay EXACTLY invariant across the same
rate changes.

Does NOT claim quantitative Hz correspondence with any source's configured
rate -- only a monotonic, reproducible, control-tested causal dependence.
"""
import numpy as np

SR = 44100
N_WINDOWS = 200


def kernel(audio, sample_rate=SR, n_windows=N_WINDOWS):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    win = n // n_windows
    if win < 64:
        return 0.0

    centroids = []
    for i in range(n_windows):
        seg = x[i * win:(i + 1) * win]
        if len(seg) < 64:
            centroids.append(centroids[-1] if centroids else 0.0)
            continue
        m = len(seg)
        spec = np.abs(np.fft.rfft(seg * np.hanning(m)))
        freqs = np.fft.rfftfreq(m, 1.0 / sample_rate)
        centroids.append(float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12)))
    trace = np.array(centroids)

    t = np.arange(len(trace), dtype=float)
    coeffs = np.polyfit(t, trace, 2)
    detrended = trace - np.polyval(coeffs, t)

    signs = np.sign(detrended - np.mean(detrended))
    signs[signs == 0] = 1
    return float(np.sum(np.abs(np.diff(signs)) > 0))
