"""Kernel: RMS energy in dB within [0.3s, 0.35s) of the render.
Used to measure envelope decay-stage behaviour, well past attack."""
import numpy as np

SR = 44100


def kernel(audio, sample_rate=SR):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    a, b = int(0.3 * sample_rate), int(0.35 * sample_rate)
    seg = x[a:min(b, len(x))]
    if len(seg) == 0:
        return -240.0
    return 20 * np.log10(float(np.sqrt(np.mean(seg ** 2)) + 1e-12))
