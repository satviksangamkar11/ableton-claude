"""16.5.32: Container Validity and State-Load Verification.

Established in 16.5.32a:
  capture_v8_skeleton(VST3) WORKS and returns real v8 metadata:
    {component: "processor", version: 8.0, product: "Serum2", ...}
  Every experiment since 16.5.17 has passed meta={} instead.

This script separates CONTAINER VALIDITY from MUTATION CAUSALITY.

Render arms:
  A  fresh instance, NO load_state()          <- the reference never taken
  B  captured meta + captured body            <- round-trip of ~default state
  C  captured meta + corpus body[4]           <- distinctive non-default patch
  C0 EMPTY meta {} + corpus body[4]           <- the broken path used since 16.5.17
  D  captured meta + corpus body[4] + MasterVolume=0.1 mutation

Decisive comparisons:
  C  vs A   -> does loading a distinctive state change audio? (CONTAINER VALIDITY)
  C0 vs A   -> does the broken path collapse to the default patch? (REGRESSION)
  C  vs C0  -> direct demonstration of the meta bug
  D  vs C   -> does a mutation take effect with a VALID container? (CAUSALITY)

Primary discriminator is RAW AUDIO IDENTITY, not any metric.

No claim about Serum behavior is made here. This tests the
serialization/load path only.
"""
import sys, os, pickle, copy, tempfile, hashlib
sys.path.insert(0, r"D:\ableton claude")

import numpy as np
import dawdreamer as daw
from serum2 import bridge, pathmerge
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
SR = 44100
BLOCK = 512

print("=" * 80)
print("16.5.32: Container Validity and State-Load Verification")
print("=" * 80)
print()

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_corpus = corpus["bodies"][4]

meta_real, body_captured = bridge.capture_v8_skeleton(VST3)
print("Captured v8 meta: %s" % {k: meta_real[k] for k in ("component", "version", "product")})
print()


def render(meta, body, load=True, label=""):
    """Replicates render_arm()'s sequence exactly, with optional state load."""
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    if load:
        fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
        bridge.write_state_file(tmp, meta, body)
        state_sha = hashlib.sha256(open(tmp, "rb").read()).hexdigest()
        synth.load_state(tmp)
        os.remove(tmp)
    else:
        state_sha = None
    synth.clear_midi()
    synth.add_midi_note(48, 110, 0.0, 1.8)
    engine.load_graph([(synth, [])])
    engine.render(2.0)
    audio = np.asarray(engine.get_audio())
    audio_sha = hashlib.sha256(np.ascontiguousarray(audio).tobytes()).hexdigest()
    rms = 20 * np.log10(float(np.sqrt(np.mean((audio.mean(axis=0) if audio.ndim == 2 else audio) ** 2))) + 1e-12)
    print("  %-4s shape=%-14s audio_sha=%s  rms=%.2f dB" % (label, str(audio.shape), audio_sha[:16], rms))
    return {"audio": audio, "sha": audio_sha, "rms": rms, "state_sha": state_sha}


print("Rendering arms (note 48, vel 110, 1.8 beats, 2.0s -- identical stimulus):")
print()

A = render(None, None, load=False, label="A")
B = render(meta_real, body_captured, load=True, label="B")
C = render(meta_real, body_corpus, load=True, label="C")
C0 = render({}, body_corpus, load=True, label="C0")

body_mut = copy.deepcopy(body_corpus)
pathmerge.apply_path_value(body_mut, "Global0.plainParams.kParamMasterVolume", 0.1)
D = render(meta_real, body_mut, load=True, label="D")

print()


def compare(x, y, xl, yl):
    same = x["sha"] == y["sha"]
    if x["audio"].shape == y["audio"].shape:
        mad = float(np.max(np.abs(x["audio"] - y["audio"])))
    else:
        mad = float("nan")
    print("  %-9s vs %-9s  identical=%-5s  max_abs_diff=%.6e  rms %.2f vs %.2f" %
          (xl, yl, same, mad, x["rms"], y["rms"]))
    return same


print("=" * 80)
print("COMPARISONS")
print("=" * 80)
print()

print("CONTAINER VALIDITY:")
c_vs_a = compare(C, A, "C", "A")
print()

print("REGRESSION (broken meta={} path used since 16.5.17):")
c0_vs_a = compare(C0, A, "C0", "A")
c_vs_c0 = compare(C, C0, "C", "C0")
print()

print("ROUND-TRIP OF CAPTURED STATE:")
b_vs_a = compare(B, A, "B", "A")
print()

print("MUTATION CAUSALITY (valid container):")
d_vs_c = compare(D, C, "D", "C")
print()

print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

if not c_vs_a:
    print("[C != A] Loading the corpus body WITH valid meta DOES change the audio.")
    print("         => The state-file path works when the container is valid.")
    container_ok = True
else:
    print("[C == A] Loading the corpus body with valid meta produced audio identical")
    print("         to a fresh instance with no state loaded at all.")
    print("         => load_state() is not applying state even with valid meta.")
    container_ok = False

print()

if c0_vs_a:
    print("[C0 == A] The meta={} path renders IDENTICALLY to a fresh unloaded instance.")
    print("          => CONFIRMED: every experiment since 16.5.17 rendered the")
    print("             default patch, regardless of body content or mutation.")
elif not c_vs_c0:
    print("[C != C0] Valid-meta and empty-meta paths produce DIFFERENT audio.")
    print("          => The empty meta materially changed what Serum rendered.")
else:
    print("[C0 != A and C == C0] Empty meta did not collapse to default;")
    print("          the regression hypothesis is NOT supported by this result.")

print()

if container_ok:
    if not d_vs_c:
        print("[D != C] MasterVolume mutation DOES change audio with a valid container.")
        print("         => MUTATION CAUSALITY RESTORED.")
        print("         => The 5/5 zero-effect results were an artifact of meta={}.")
        verdict = "REGRESSION_CONFIRMED_AND_FIXED"
    else:
        print("[D == C] Container is valid and state loads, but the MasterVolume")
        print("         mutation still produces identical audio.")
        print("         => Container was necessary but not sufficient; a separate")
        print("            mutation-path problem remains.")
        verdict = "CONTAINER_FIXED_MUTATION_STILL_FAILING"
else:
    print("State loading does not work even with valid meta.")
    print("=> The problem is deeper than the meta regression.")
    verdict = "STATE_LOAD_FAILS_WITH_VALID_META"

print()
print("=" * 80)
print("16.5.32 COMPLETE   Verdict: %s" % verdict)
print("=" * 80)
