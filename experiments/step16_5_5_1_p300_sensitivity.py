"""16.5.5.1: P300 sensitivity check via narrow-band energy kernel.

wholesignal_centroid reported delta=-44.98 at threshold=50 for P300 (300 Hz
treatment vs 639.84 Hz baseline). That is 'below detection threshold', not
'no causal effect.' Before classifying 300 Hz as a causal non-effect witness,
we apply an independent, more sensitive, filter-specific observable.

Observable: RMS in the narrow band [150, 800] Hz.
Rationale: A parametric EQ band acting near 300-640 Hz should redistribute
energy within this window even if the whole-signal spectral centroid shift
is small. This kernel has no configurable threshold -- we report the raw
delta and compare its magnitude to P8000's delta under the same observable,
which is a confirmed EFFECT_OBSERVED at the lower (wholesignal) level.

Both points are re-rendered fresh. No harness wrapping -- standalone analysis
to keep this independent of the capability evidence system.

Possible outcomes:
  (i)  P300 narrow-band delta >> P8000 narrow-band delta (relative):
       wholesignal_centroid was a poor kernel for this regime; P300 produced
       a real filter response that the prior kernel missed. -> causal UNRESOLVED.
  (ii) P300 narrow-band delta << P8000 narrow-band delta AND consistent in
       direction with what the EQ should do (or near-zero):
       Two independent observables agree. P300 is a genuine non-detect;
       can be classified as causal non-effect witness with stated caveat.

No outcome here upgrades or downgrades existing EvidenceRecords.
"""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, pathmerge
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
BLOCK = 512
NOTE, VEL, NOTE_LEN, SECS = 48, 110, 1.8, 2.0

d = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
fxrack0 = d["bodies"][4]["FXRack0"]
assert fxrack0["FX"][1]["FXEQ"]["plainParams"]["kParamFreq1"] == 639.8384480408016

meta_skel, body_skel = bridge.capture_v8_skeleton(VST3)

def render_freq1(freq_val):
    m, b = copy.deepcopy(meta_skel), copy.deepcopy(body_skel)
    pathmerge.apply_path_value(b, "FXRack0", copy.deepcopy(fxrack0))
    pathmerge.apply_path_value(b, "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1", freq_val)
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, m, b)
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    synth.add_midi_note(NOTE, VEL, 0.0, NOTE_LEN)
    engine.load_graph([(synth, [])])
    engine.render(SECS)
    audio = np.asarray(engine.get_audio())
    os.remove(tmp)
    return audio.mean(axis=0) if audio.ndim == 2 else audio

BASELINE_FREQ = 639.8384480408016  # corpus value -- this IS the control arm

def band_rms(x, lo=150.0, hi=800.0, sr=SR):
    """RMS energy in the [lo, hi] Hz band."""
    n = len(x)
    spec = np.abs(np.fft.rfft(x)) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    mask = (freqs >= lo) & (freqs <= hi)
    return float(np.sqrt(np.mean(spec[mask])))

def wholesignal_centroid(x, sr=SR):
    """Replication of the original kernel's scalar output for cross-check."""
    spec = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    return float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12))

print("=== rendering arms ===")
print("control (baseline 639.84 Hz)...")
x_ctrl = render_freq1(BASELINE_FREQ)

print("P300  treatment (300.0 Hz)...")
x_p300 = render_freq1(300.0)

print("P8000 treatment (8000.0 Hz)...")
x_p8000 = render_freq1(8000.0)

print()
print("=== wholesignal_centroid (independent replication) ===")
c_ctrl  = wholesignal_centroid(x_ctrl)
c_p300  = wholesignal_centroid(x_p300)
c_p8000 = wholesignal_centroid(x_p8000)
print("  ctrl : %.2f" % c_ctrl)
print("  P300 : %.2f  delta=%+.2f" % (c_p300,  c_p300  - c_ctrl))
print("  P8000: %.2f  delta=%+.2f" % (c_p8000, c_p8000 - c_ctrl))

print()
print("=== narrow-band RMS [150, 800] Hz ===")
b_ctrl  = band_rms(x_ctrl)
b_p300  = band_rms(x_p300)
b_p8000 = band_rms(x_p8000)
print("  ctrl : %.6f" % b_ctrl)
print("  P300 : %.6f  delta=%+.6f  rel=%+.2f%%" % (b_p300,  b_p300  - b_ctrl, 100*(b_p300  - b_ctrl)/b_ctrl))
print("  P8000: %.6f  delta=%+.6f  rel=%+.2f%%" % (b_p8000, b_p8000 - b_ctrl, 100*(b_p8000 - b_ctrl)/b_ctrl))

# Sensitivity ratio: how much does P300 move the narrow-band RMS relative to P8000?
ratio = abs(b_p300 - b_ctrl) / (abs(b_p8000 - b_ctrl) + 1e-30)
print()
print("P300/P8000 sensitivity ratio (narrow-band): %.4f" % ratio)
print("  (>0.5 -> P300 is comparable to P8000 -> prior kernel was insensitive)")
print("  (<0.1 -> P300 is a genuine non-detect across both observables)")

print()
print("=== verdict ===")
if ratio > 0.25:
    print("UNRESOLVED: narrow-band shows comparable response at P300.")
    print("  wholesignal_centroid was too coarse for this regime.")
    print("  P300 CANNOT be classified as a causal non-effect witness.")
elif abs(b_p300 - b_ctrl) / b_ctrl < 0.005:
    print("CONFIRMED NON-DETECT: P300 delta < 0.5% in narrow-band.")
    print("  Two independent observables agree. P300 is a genuine non-detect.")
    print("  Can classify as causal non-effect witness (stated: 'below two-kernel detection floor').")
else:
    print("BORDERLINE: P300 shows %.2f%% narrow-band delta." % (100*abs(b_p300-b_ctrl)/b_ctrl))
    print("  Inconclusive. Do not classify until a third observable is applied.")

results = {"ctrl_freq": BASELINE_FREQ, "p300": 300.0, "p8000": 8000.0,
           "centroid": {"ctrl": c_ctrl, "p300": c_p300, "p8000": c_p8000},
           "band_rms": {"ctrl": b_ctrl, "p300": b_p300, "p8000": b_p8000},
           "ratio": ratio}
pickle.dump(results, open(r"D:\ableton claude\experiments\_p300_sensitivity.pkl", "wb"))
