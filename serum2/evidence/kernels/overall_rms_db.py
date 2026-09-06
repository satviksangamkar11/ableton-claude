"""Kernel: RMS energy in dB across the full render.
Used for whole-note level tests (oscillator enable, level/volume)."""
import numpy as np

SR = 44100


def kernel(audio, sample_rate=SR):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    return 20 * np.log10(float(np.sqrt(np.mean(x ** 2)) + 1e-12))
