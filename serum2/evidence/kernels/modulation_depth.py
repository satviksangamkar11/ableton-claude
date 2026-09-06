"""Kernel: periodic-modulation depth/strength of a rendered note.

Paired with modulation_frequency_hz.py (identical trace-extraction and
log-domain detrending -- duplicated here rather than shared, per the
one-file-one-function kernel-identity convention). Where that kernel answers
"is there a confidently periodic component, and at what frequency", this one
answers "how strong is it" as the RMS of the detrended log-residual --
independent of whether a clean spectral peak was found. This lets a caller
distinguish, e.g., a static route (near-zero depth, freq=0.0) from a
non-periodic-but-still-varying envelope artifact (small but nonzero depth,
freq=0.0) from genuine modulation (large depth, nonzero freq).

See modulation_frequency_hz.py's module docstring for full method rationale
and the synthetic validation this design was tuned against.
"""
import numpy as np

SR = 44100
N_WINDOWS = 80
POLY_DEGREE = 3


def kernel(audio, sample_rate=SR, n_windows=N_WINDOWS, poly_degree=POLY_DEGREE):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    win = n // n_windows
    if win < 4:
        return 0.0

    trace = np.array([
        float(np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2)))
        for i in range(n_windows)
    ])
    if len(trace) < 8:
        return 0.0

    eps = 1e-9
    log_trace = np.log(trace + eps)
    t = np.arange(len(trace), dtype=float)
    coeffs = np.polyfit(t, log_trace, poly_degree)
    trend_log = np.polyval(coeffs, t)
    resid = log_trace - trend_log
    resid = resid - np.mean(resid)

    return float(np.sqrt(np.mean(resid ** 2)))
