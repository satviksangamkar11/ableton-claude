"""Pitch measurement kernel for behavioral experiments.

Provides harmonic-summation F0 estimation that correctly handles signals
where the first overtone is stronger than the fundamental — the common case
for Serum oscillators at default level.

Design: for each candidate frequency, score = sum of spectral power at
f0, 2*f0, 3*f0, …  The true fundamental captures ALL harmonic energy;
an overtone candidate misses energy at its own sub-harmonics and therefore
scores lower.  No post-hoc octave correction is applied; the score itself
selects the correct fundamental.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np


# ── public types ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HarmonicCandidate:
    f0_hz: float
    score: float
    harmonic_powers: tuple[float, ...]  # power at 1*f0, 2*f0, …


# ── core kernel ───────────────────────────────────────────────────────────────

def harmonic_sum_f0(
    audio: np.ndarray,
    sample_rate: int,
    candidates_hz: np.ndarray,
    *,
    max_harmonics: int = 12,
) -> HarmonicCandidate:
    """Score each candidate F0 by summed spectral power at f0, 2*f0, 3*f0, …

    Returns the highest-scoring candidate without octave correction.

    Parameters
    ----------
    audio        : float array, shape (channels, samples) or (samples,)
    sample_rate  : sample rate in Hz
    candidates_hz: 1-D array of candidate fundamental frequencies to evaluate
    max_harmonics: number of harmonic positions to sum per candidate

    Notes
    -----
    Uses a single-bin lookup at each harmonic position (argmin |freqs - target|).
    For a window of N samples this gives frequency resolution sr/N ≈ 1 Hz for
    a 0.9-second window at 44100 Hz.  Sufficient precision for octave-shift
    detection (12 semitones = 2× frequency ratio).
    """
    mono = audio.mean(axis=0) if audio.ndim == 2 else audio.flatten()
    # Mid-section window: avoid attack/release artefacts
    lo = int(0.3 * sample_rate)
    hi = int(1.2 * sample_rate)
    segment = mono[lo:hi].astype(np.float64)
    segment -= segment.mean()          # remove DC

    win = np.hanning(len(segment))
    spectrum = np.abs(np.fft.rfft(segment * win)) ** 2   # power spectrum
    freqs = np.fft.rfftfreq(len(segment), 1.0 / sample_rate)
    nyquist = sample_rate / 2.0

    best: Optional[HarmonicCandidate] = None

    for f0 in candidates_hz:
        powers: list[float] = []
        for h in range(1, max_harmonics + 1):
            target = h * float(f0)
            if target >= nyquist:
                break
            idx = int(np.argmin(np.abs(freqs - target)))
            powers.append(float(spectrum[idx]))

        score = float(sum(powers))
        candidate = HarmonicCandidate(
            f0_hz=float(f0),
            score=score,
            harmonic_powers=tuple(powers),
        )
        if best is None or score > best.score:
            best = candidate

    if best is None:
        raise ValueError("candidates_hz is empty or all harmonics above Nyquist")
    return best


# ── scalar wrapper for METRICS registry ──────────────────────────────────────

# Candidate grid for standard pitched-instrument F0 estimation.
# C2 (65.4 Hz) to C6 (1046.5 Hz) in 0.5-Hz steps gives sub-cent resolution
# at every octave within the Serum oscillator range.
_DEFAULT_CANDIDATES = np.arange(65.0, 1050.0, 0.5)


def fundamental_frequency_hz(audio: np.ndarray, stimulus=None) -> float:
    """METRICS-compatible scalar wrapper: returns F0 in Hz.

    Uses harmonic summation with the default candidate grid and 12 harmonics.
    SR is taken from measure.py's module-level constant (44100).
    """
    from serum2.evidence.measure import SR
    result = harmonic_sum_f0(audio, SR, _DEFAULT_CANDIDATES, max_harmonics=12)
    return result.f0_hz


# ── pitch-shift helper ────────────────────────────────────────────────────────

def semitone_shift(baseline_hz: float, treatment_hz: float) -> float:
    """12 * log2(treatment / baseline). Raises ValueError if either ≤ 0."""
    if baseline_hz <= 0 or treatment_hz <= 0:
        raise ValueError(
            f"Both frequencies must be positive: baseline={baseline_hz}, treatment={treatment_hz}"
        )
    return 12.0 * math.log2(treatment_hz / baseline_hz)
