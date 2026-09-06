"""Kernel: RMS energy in dB within the first 30ms after note-on.
Used to measure envelope attack-stage behaviour."""
import numpy as np

SR = 44100


def kernel(audio, sample_rate=SR):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    seg = x[:int(0.03 * sample_rate)]
    if len(seg) == 0:
        return -240.0
    return 20 * np.log10(float(np.sqrt(np.mean(seg ** 2)) + 1e-12))
