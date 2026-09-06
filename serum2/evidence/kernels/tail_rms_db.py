"""Kernel: RMS energy in dB of the render tail (after the dry signal decays).

Reconstructed from g8b_test2_fxdelay.render_tail_energy and
g8d_test2_full_gate.render_tail / g8e_test3_coexistence.render_tail.
"""
import numpy as np

SR = 44100
TAIL_START = 0.6


def kernel(audio, sample_rate=SR, tail_start=TAIL_START):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    tail = x[int(tail_start * sample_rate):]
    return 20 * np.log10(float(np.sqrt(np.mean(tail ** 2)) + 1e-12))
