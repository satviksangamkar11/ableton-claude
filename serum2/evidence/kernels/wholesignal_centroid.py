"""Kernel: whole-signal spectral centroid (single FFT over the entire render).

Reconstructed from g8e_test3_coexistence.render_centroid. This is a DIFFERENT
algorithm from windowed_mean_centroid despite both being called
"spectral_centroid_hz" historically.
"""
import numpy as np

SR = 44100


def kernel(audio, sample_rate=SR):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
    return float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12))
