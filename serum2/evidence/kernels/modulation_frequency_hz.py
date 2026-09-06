"""Kernel: dominant periodic-modulation frequency (Hz) of a rendered note.

Built for 15.2.5 LFO-source discovery. Prior aggregate metrics (mean RMS,
mean centroid) cannot distinguish "no effect" from "a periodic effect that
averages out" -- this kernel extracts a time-domain envelope trace and looks
for genuine oscillation in it, separated from the note's own attack/decay/
release shape.

Method:
  1. Windowed RMS trace (n_windows non-overlapping segments across the render).
  2. Detrend in LOG domain via a low-order polynomial fit. This is the key
     design choice: an exponential decay of ANY rate is exactly LINEAR in log
     amplitude, so even a degree-1 fit removes it perfectly -- far more robust
     than fitting the linear-amplitude trace directly, which cannot represent
     a steep decay with a low-order polynomial and leaves spurious low-
     frequency residual energy that (validated empirically) a naive linear-
     domain detrend misreads as a ~1 Hz "detected" modulation.
  3. FFT the detrended log-residual (Hanning-windowed). The dominant AC bin
     (excluding the two lowest bins, which carry residual very-low-frequency
     drift from imperfect detrending) is the candidate modulation frequency.
  4. Two gates before a frequency is reported at all, both required:
       - depth (RMS of the log-residual) must clear MIN_DEPTH -- filters out
         numerical noise floor and mild envelope-detrend residue.
       - prominence (peak bin power / median of the rest of the spectrum)
         must clear MIN_PROMINENCE -- filters out broadband, non-periodic
         residue (e.g. sharp envelope-segment kinks) from being mistaken for
         a genuine spectral line.
     Either failing means "no confidently detected periodicity" -> 0.0 Hz.

Validated against synthetic ground truth (see step 2 of 15.2.5): flat/static
signal, 2 Hz and 7 Hz genuine AM (with and without a decaying carrier
envelope), pure exponential decay at multiple rates, and a hard-cornered
ADSR-shaped envelope (a harsher test than the task required) -- all correctly
classified with the parameters below. See modulation_depth.py for the paired
depth/strength kernel (identical trace/detrend logic, duplicated per the
one-file-one-function convention).
"""
import numpy as np

SR = 44100
N_WINDOWS = 80
POLY_DEGREE = 3
MIN_PROMINENCE = 4.0
MIN_DEPTH = 0.28


def kernel(audio, sample_rate=SR, n_windows=N_WINDOWS, poly_degree=POLY_DEGREE,
          min_prominence=MIN_PROMINENCE, min_depth=MIN_DEPTH):
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

    depth = float(np.sqrt(np.mean(resid ** 2)))
    if depth < min_depth:
        return 0.0

    windowed = resid * np.hanning(len(resid))
    spec = np.abs(np.fft.rfft(windowed))
    if len(spec) < 4:
        return 0.0
    trace_dt = win / sample_rate
    freqs = np.fft.rfftfreq(len(windowed), d=trace_dt)

    search = spec[2:]
    if len(search) == 0 or np.all(search == 0):
        return 0.0
    peak_idx = int(np.argmax(search)) + 2
    peak_power = spec[peak_idx]
    rest = np.delete(spec, [0, 1, peak_idx])
    background = np.median(rest) + 1e-12
    prominence = peak_power / background
    if prominence < min_prominence:
        return 0.0

    return float(freqs[peak_idx])
