"""Audio measurements. Each returns a scalar for a named metric."""
import numpy as np

SR = 44100


def _mono(audio):
    return audio.mean(axis=0) if audio.ndim == 2 else audio


def spectral_centroid_hz(audio, stimulus=None):
    x = _mono(audio)
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    return float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12))


def tail_rms_db(audio, stimulus=None):
    """Energy remaining after the dry signal has decayed -- isolates delay
    repeats / reverb tails from the note itself."""
    x = _mono(audio)
    tail_start = 0.6 if stimulus is None or stimulus.get("tail_start") is None else stimulus["tail_start"]
    tail = x[int(tail_start * SR):]
    return 20 * np.log10(float(np.sqrt(np.mean(tail ** 2)) + 1e-12))


def rms_db(audio, stimulus=None):
    x = _mono(audio)
    return 20 * np.log10(float(np.sqrt(np.mean(x ** 2)) + 1e-12))


METRICS = {
    "spectral_centroid_hz": spectral_centroid_hz,
    "tail_rms_db": tail_rms_db,
    "rms_db": rms_db,
}


def direction_of(delta, threshold):
    if abs(delta) < threshold:
        return "none"
    return "increase" if delta > 0 else "decrease"
