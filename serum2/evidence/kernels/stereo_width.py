"""Kernel: stereo width via bounded mid/side energy ratio.

width = RMS(L-R) / (RMS(L-R) + RMS(L+R)), bounded in [0, 1].
Mono/identical L,R -> 0. Fully decorrelated equal-power L,R -> 0.5.
Fully anti-phase L,R (mid cancels) -> approaches 1 cleanly (bounded, unlike a
raw side/mid ratio which diverges as mid_rms -> 0 -- caught during validation).
Used to detect unison-voice pan randomization, which a mono-sensitive metric
(RMS, centroid) cannot see at all.
"""
import numpy as np

SR = 44100


def kernel(audio, sample_rate=SR):
    if audio.ndim != 2 or audio.shape[0] < 2:
        return 0.0  # genuinely mono input -- zero width, not an error
    L, R = audio[0], audio[1]
    side_rms = float(np.sqrt(np.mean((L - R) ** 2)))
    mid_rms = float(np.sqrt(np.mean((L + R) ** 2)))
    return side_rms / (side_rms + mid_rms + 1e-12)
