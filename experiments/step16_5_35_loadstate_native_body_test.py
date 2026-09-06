"""16.5.35: Unconfounded load_state Test Using Serum's Own Body.

Every prior test of load_state() was confounded:
  16.5.32 arm C  loaded corpus body[4] -- unknown validity for Serum 2.0.21
  16.5.34 arms C/D  vacuous, save_state returned a default state (f1 == f0)

This test removes the confound by mutating a body that Serum ITSELF produced
seconds earlier, and by comparing two arms that traverse the IDENTICAL path
(write_state_file -> load_state -> render), differing only by the mutation.

Arms:
  A   fresh, no load_state                       reference
  R   fresh + set_parameter(Main Vol, 0.0)       known-good: audio CAN change
  C   load_state(captured body, UNMUTATED)
  D   load_state(captured body, MUTATED)

Key comparison: D vs C
  D != C  -> load_state applies mutations. Defect lies in the corpus bodies.
  D == C  -> load_state is inert even for Serum's own freshly-minted body.

Also reports a structural diff of captured body vs corpus body[4].

Diagnostic only.
"""
import sys, os, pickle, copy, tempfile, hashlib
sys.path.insert(0, r"D:\ableton claude")

import numpy as np
import dawdreamer as daw
from serum2 import bridge, pathmerge
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
SR, BLOCK = 44100, 512
NOTE, VEL, LEN, DUR = 48, 110, 1.8, 2.0

print("=" * 80)
print("16.5.35: Unconfounded load_state Test (Serum's own body)")
print("=" * 80)
print()

meta, body_native = bridge.capture_v8_skeleton(VST3)
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_corpus = corpus["bodies"][4]

# ---- Structural inspection ----
print("SECTION 1: Captured native body -- what is actually populated?")
print("-" * 80)
g0 = body_native.get("Global0", {})
print("Global0 keys: %s" % list(g0.keys()))
pp = g0.get("plainParams")
print("Global0.plainParams type: %s" % type(pp).__name__)
if isinstance(pp, dict):
    print("  entries: %d" % len(pp))
    for k in list(pp.keys())[:12]:
        print("    %-32s %s" % (k, pp[k]))
else:
    print("  value: %r" % pp)
print()

print("SECTION 2: Structural diff -- native vs corpus body[4]")
print("-" * 80)
print("top-level keys  native=%d  corpus=%d" % (len(body_native), len(body_corpus)))
only_native = sorted(set(body_native) - set(body_corpus))
only_corpus = sorted(set(body_corpus) - set(body_native))
print("keys only in native: %s" % (only_native[:10] if only_native else "none"))
print("keys only in corpus: %s" % (only_corpus[:10] if only_corpus else "none"))

type_mismatch = []
for k in set(body_native) & set(body_corpus):
    tn, tc = type(body_native[k]).__name__, type(body_corpus[k]).__name__
    if tn != tc:
        type_mismatch.append((k, tn, tc))
print("shared keys with differing TYPE: %d" % len(type_mismatch))
for k, tn, tc in type_mismatch[:10]:
    print("    %-24s native=%-8s corpus=%s" % (k, tn, tc))
print()


# ---- Choose a mutation target that EXISTS in the native body ----
def find_numeric_leaf(obj, path=(), depth=0):
    """First numeric leaf under a dict, preferring volume/level-ish names."""
    if depth > 6:
        return None
    if isinstance(obj, dict):
        pref = [k for k in obj if any(s in str(k).lower() for s in ("mastervol", "volume", "level", "gain"))]
        for k in pref + [k for k in obj if k not in pref]:
            v = obj[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return path + (k,), v
            r = find_numeric_leaf(v, path + (k,), depth + 1)
            if r:
                return r
    return None

target_path = None
if isinstance(pp, dict) and "kParamMasterVolume" in pp:
    target_path = "Global0.plainParams.kParamMasterVolume"
    orig_val = pp["kParamMasterVolume"]
else:
    found = find_numeric_leaf({"Global0": g0})
    if found is None:
        found = find_numeric_leaf(body_native)
    if found:
        parts, orig_val = found
        target_path = ".".join(parts)

print("SECTION 3: Mutation target selected from the NATIVE body")
print("-" * 80)
if target_path is None:
    print("[STOP] No numeric leaf found in the captured native body.")
    print("       Serum's init state contains no mutable numeric fields at the")
    print("       paths we can address -- that is itself the finding.")
    sys.exit(0)
new_val = 0.0 if isinstance(orig_val, float) else 0
print("  path:     %s" % target_path)
print("  original: %r  ->  mutated: %r" % (orig_val, new_val))
print()


# ---- Render helpers ----
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
    def _setup(syn):
        fd, p = tempfile.mkstemp(suffix=".bin"); os.close(fd)
        bridge.write_state_file(p, meta, b)
        syn.load_state(p)
        os.remove(p)
    return _setup


body_mut = copy.deepcopy(body_native)
pathmerge.apply_path_value(body_mut, target_path, new_val)
readback = pathmerge.read_path_value(body_mut, target_path)
print("  mutation applied to body dict: readback = %r  (%s)" %
      (readback, "OK" if readback == new_val else "FAILED"))
print()

print("SECTION 4: Renders")
print("-" * 80)
A = render(lambda s: None)
R = render(lambda s: s.set_parameter(0, 0.0))
C = render(loader(body_native))
D = render(loader(body_mut))
for lbl, r in (("A", A), ("R", R), ("C", C), ("D", D)):
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


r_vs_a = cmp(R, A, "R", "A")
c_vs_a = cmp(C, A, "C", "A")
d_vs_c = cmp(D, C, "D", "C")
d_vs_a = cmp(D, A, "D", "A")
print()

print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()

if r_vs_a:
    print("[R == A] Even set_parameter produced no audio change in this run.")
    print("   Environment is not behaving as it did in 16.5.34. Stop and re-check.")
    verdict = "REFERENCE_ARM_FAILED"
elif not d_vs_c:
    print("[D != C] Mutating Serum's OWN captured body DOES change the rendered")
    print("   audio through write_state_file -> load_state.")
    print("   => load_state() WORKS. It is not inert.")
    print("   => The defect is specific to the CORPUS bodies, which do not apply.")
    print("   => Fix direction: regenerate/repair the corpus against this Serum")
    print("      build. No actuator rewrite and no env forensics required.")
    verdict = "LOAD_STATE_WORKS_CORPUS_IS_DEFECTIVE"
else:
    print("[D == C] Mutating Serum's own freshly-captured body produced")
    print("   byte-identical audio. load_state() is inert even against a body")
    print("   Serum itself generated seconds earlier.")
    print("   => Corpus staleness is EXCLUDED as the explanation.")
    print("   => The serialized-state path itself does not reach the DSP,")
    print("      while set_parameter/set_patch demonstrably do (R != A).")
    print("   => Fix direction: environment forensics on the load_state path,")
    print("      or migrate the actuator to the host-parameter vector.")
    verdict = "LOAD_STATE_INERT_ON_NATIVE_BODY"

print()
print("=" * 80)
print("16.5.35 COMPLETE   Verdict: %s" % verdict)
print("=" * 80)
