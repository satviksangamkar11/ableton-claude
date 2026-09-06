"""Kernel: 8-window mean spectral centroid.

Reconstructed from g7a_causality.render_windows and g8a_test1_slot30.render_windows.
Both computed a list of per-window centroids; the mean was taken at the call site
(np.mean(...)). This artifact composes both halves into one audio -> scalar kernel.
"""
import numpy as np

SR = 44100
N_WINDOWS = 8


def kernel(audio, sample_rate=SR, n_windows=N_WINDOWS):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    win = len(x) // n_windows
    out = []
    for i in range(n_windows):
        seg = x[i * win:(i + 1) * win]
        if len(seg) < 64:
            continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
        out.append(float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12)))
    return float(np.mean(out))
