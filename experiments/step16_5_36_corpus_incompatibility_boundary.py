"""16.5.36: Localize the Corpus Incompatibility Boundary.

Established in 16.5.35:
  load_state() WORKS -- mutating Serum's own captured body changes the audio
  (D != C, max_abs_diff 1.195e-01). The serialized-state actuator is sound.

  Corpus bodies do NOT apply. Structural diff:
    native=162 top-level keys, corpus=175
    native-only: ['component']
    corpus-only: 13 keys (ClipPlayer, Filter, GranularOsc, MultiSampleOsc,
                 Osc, SerumGUI, SpectralOsc, WTOsc, arpBankDisplayName, ...)

Finding under test:
  CORPUS-SERIALIZATION-COMPATIBILITY-1
  Corpus bodies are structurally incompatible with the current Serum 2.0.21
  native processor-state schema; the causal boundary is not yet localized.

This is a DIAGNOSTIC, not a repair rule. Stripping keys is a probe to locate
the incompatibility boundary, not a proposed corpus fix.

Arms (all through the identical write_state_file -> load_state -> render path,
using the captured NATIVE meta):
  A  fresh, no load                                    reference
  C  corpus body[4] unmodified                         (expect == A per 16.5.32)
  D  corpus INTERSECT native keys        (161 keys)    extras removed
  E  D + 'component' from native         (162 keys)    exact native key set

Hard gate (per design): a variant only counts as "applying" if it differs
from A. D != C alone is insufficient -- that could be a different flavor of
not-applying.
"""
import sys, os, pickle, copy, tempfile, hashlib
sys.path.insert(0, r"D:\ableton claude")

import numpy as np
import dawdreamer as daw
from serum2 import bridge
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
SR, BLOCK = 44100, 512
NOTE, VEL, LEN, DUR = 48, 110, 1.8, 2.0

print("=" * 80)
print("16.5.36: Localize the Corpus Incompatibility Boundary")
print("=" * 80)
print()

meta, body_native = bridge.capture_v8_skeleton(VST3)
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_corpus = corpus["bodies"][4]

nk, ck = set(body_native), set(body_corpus)
print("SECTION 1: Key sets")
print("-" * 80)
print("  native=%d  corpus=%d  shared=%d" % (len(nk), len(ck), len(nk & ck)))
print("  native-only (%d): %s" % (len(nk - ck), sorted(nk - ck)))
print("  corpus-only (%d): %s" % (len(ck - nk), sorted(ck - nk)))
print()

# ---- Build variants ----
body_D = {k: copy.deepcopy(v) for k, v in body_corpus.items() if k in nk}
body_E = copy.deepcopy(body_D)
for k in (nk - ck):
    body_E[k] = copy.deepcopy(body_native[k])

print("SECTION 2: Variants constructed")
print("-" * 80)
print("  C (corpus original)          : %d keys" % len(body_corpus))
print("  D (corpus INTERSECT native)  : %d keys" % len(body_D))
print("  E (D + native-only keys)     : %d keys   (native has %d)" % (len(body_E), len(body_native)))
print("  E key set == native key set  : %s" % (set(body_E) == nk))
print()


def render(setup):
    eng = daw.RenderEngine(SR, BLOCK)
    syn = eng.make_plugin_processor("serum", VST3)
    setup(syn)
    syn.clear_midi()
    syn.add_midi_note(NOTE, VEL, 0.0, LEN)
    eng.load_graph([(syn, [])])
    eng.render(DUR)
    a = np.asarray(eng.get_audio())
    sha = hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
    mono = a.mean(axis=0) if a.ndim == 2 else a
    rms = 20 * np.log10(float(np.sqrt(np.mean(mono ** 2))) + 1e-12)
    return {"audio": a, "sha": sha, "rms": rms}


def loader(b):
    def _s(syn):
        fd, p = tempfile.mkstemp(suffix=".bin"); os.close(fd)
        bridge.write_state_file(p, meta, b)
        syn.load_state(p)
        os.remove(p)
    return _s


print("SECTION 3: Renders")
print("-" * 80)
A = render(lambda s: None)
C = render(loader(body_corpus))
D = render(loader(body_D))
E = render(loader(body_E))
for lbl, r in (("A", A), ("C", C), ("D", D), ("E", E)):
    print("  %-3s sha=%s  rms=%9.2f dB" % (lbl, r["sha"][:16], r["rms"]))
print()

print("=" * 80)
print("COMPARISONS")
print("=" * 80)


def cmp(x, y, xl, yl):
    same = x["sha"] == y["sha"]
    mad = float(np.max(np.abs(x["audio"] - y["audio"]))) if x["audio"].shape == y["audio"].shape else float("nan")
    print("  %-3s vs %-3s  identical=%-5s  max_abs_diff=%.6e" % (xl, yl, same, mad))
    return same


print("Against the fresh reference (the hard gate -- 'does it apply at all?'):")
c_applies = not cmp(C, A, "C", "A")
d_applies = not cmp(D, A, "D", "A")
e_applies = not cmp(E, A, "E", "A")
print()
print("Incremental:")
cmp(D, C, "D", "C")
cmp(E, D, "E", "D")
print()

print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()
print("  applies (differs from fresh A):  C=%s  D=%s  E=%s" % (c_applies, d_applies, e_applies))
print()

if c_applies:
    print("[C applies] The unmodified corpus body DID change the audio here,")
    print("   contradicting 16.5.32. Environment inconsistency -- re-check before")
    print("   drawing any conclusion.")
    verdict = "UNEXPECTED_C_APPLIES"
elif e_applies and not d_applies:
    print("[E applies, D does not] Restoring the native-only key(s) is what makes")
    print("   the corpus state load. Removing the 13 extras alone was insufficient.")
    print("   => Boundary localized to the MISSING native key(s): %s" % sorted(nk - ck))
    verdict = "BOUNDARY_IS_MISSING_NATIVE_KEYS"
elif d_applies:
    print("[D applies] Removing the 13 non-native top-level keys is sufficient to")
    print("   make the corpus state load.")
    print("   => Boundary localized to the EXTRA top-level keys.")
    print("   NOTE: this is a localization, NOT a validated repair rule. It does")
    print("   not establish that the stripped body faithfully represents the")
    print("   corpus patch -- only that Serum now accepts it.")
    verdict = "BOUNDARY_IS_EXTRA_TOPLEVEL_KEYS"
else:
    print("[neither D nor E applies] Top-level key-set alignment is NOT sufficient.")
    print("   E has exactly the native key set and still does not reach the DSP.")
    print("   => The incompatibility is NESTED, below the top level.")
    print("   Next: localize within-key structure/value representation.")
    verdict = "BOUNDARY_IS_NESTED_NOT_TOPLEVEL"

    print()
    print("  Nested probe -- type mismatches at depth 2 on shared keys:")
    n_shown = 0
    for k in sorted(nk & ck):
        vn, vc = body_native[k], body_corpus[k]
        if isinstance(vn, dict) and isinstance(vc, dict):
            for sub in sorted(set(vn) & set(vc)):
                tn, tc = type(vn[sub]).__name__, type(vc[sub]).__name__
                if tn != tc and n_shown < 15:
                    print("    %-22s .%-18s native=%-8s corpus=%s" % (k, sub, tn, tc))
                    n_shown += 1
    if n_shown == 0:
        print("    (no depth-2 type mismatches on shared keys)")

print()
print("=" * 80)
print("16.5.36 COMPLETE   Verdict: %s" % verdict)
print("=" * 80)
