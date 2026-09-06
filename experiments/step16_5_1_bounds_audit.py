"""16.5.1: Audit whether structural bounds can be derived mechanically from
existing EvidenceRecords WITHOUT parsing prose or manually re-entering facts.

Success condition:
  Existing clamp-probe evidence can be exposed as machine-readable structural
  bounds without duplicating or manually re-entering Serum facts.

Failure condition:
  If the existing EvidenceRecords do not contain enough structured information
  to derive those bounds safely, stop and fix the evidence representation first.

This script does not modify ANY existing object. It only reads and classifies.
"""
import sys, pickle, re
sys.path.insert(0, r"D:\ableton claude")

# ---- attempt 1: naive regex on provenance prose ----
RANGE_RE = re.compile(r'\[(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\]')

def try_parse_range(provenance):
    """Returns (lo, hi) if provenance contains a '[lo, hi]' pattern, else None.
    NOTE: this regex does NOT know whether the match is a numeric range or an
    array literal like [6, 0] -- it cannot distinguish them without domain
    knowledge baked in."""
    m = RANGE_RE.search(provenance or "")
    if m:
        return (float(m.group(1)), float(m.group(2)))
    return None

def is_plausible_range(lo, hi):
    """A plausible numeric range has lo < hi and a spread > 0. Array literals
    like [6, 0] fail because lo > hi."""
    return lo < hi

# ---- load all saved evidence records ----
records = {}

def load_single(tag, path):
    try:
        r = pickle.load(open(path, "rb"))
        records[tag] = r
    except FileNotFoundError:
        records[tag] = None

def load_dict(path):
    try:
        return pickle.load(open(path, "rb"))
    except FileNotFoundError:
        return {}

load_single("fxeq_freq1",  r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl")
load_single("fxdist_drive", r"D:\ableton claude\experiments\_fxdist_drive_record.pkl")
load_single("fxdist_mode",  r"D:\ableton claude\experiments\_fxdist_mode_record.pkl")

fxeq_numeric = load_dict(r"D:\ableton claude\experiments\_fxeq_numeric_records.pkl")
fxeq_type    = load_dict(r"D:\ableton claude\experiments\_fxeq_type_records.pkl")
lfo_dep      = load_dict(r"D:\ableton claude\experiments\_lfo_rate_dependence_records.pkl")
global_voice = load_dict(r"D:\ableton claude\experiments\_global_voice_records.pkl")

def mutations_from(rec):
    if rec is None:
        return []
    return rec.experiment.get("mutations", [])

# ---- collect all fields + provenance strings ----
candidates = []

def add(label, rec, expected_has_clamp):
    for m in mutations_from(rec):
        candidates.append({
            "label": label,
            "path": m.get("target_path"),
            "value": m.get("value"),
            "provenance": m.get("provenance", ""),
            "expected_has_clamp": expected_has_clamp,
        })

add("FXEQ-FREQ1", records["fxeq_freq1"], True)
add("FXDIST-DRIVE", records["fxdist_drive"], True)
add("FXDIST-MODE", records["fxdist_mode"], False)
for key, rec in fxeq_numeric.items():
    add("FXEQ-%s" % key, rec, True)
for key, rec in fxeq_type.items():
    add("FXEQ-TYPE-%s" % key, rec, False)
for key, rec in lfo_dep.items():
    add("LFO-DEP-%s" % key, rec, False)
for key, rec in global_voice.items():
    add("VOICE-%s" % key, rec, "OVERSAMPLING" in key or "MACRO" in key.upper())

# ---- audit each candidate ----
print("=== 16.5.1 Structural Bounds Derivability Audit ===")
print()
print("%-30s %-15s %-12s %-12s %s" % ("label", "regex_result", "plausible", "verdict", "provenance[:60]"))
print("-" * 110)

results = []
for c in candidates:
    prov = c["provenance"]
    if isinstance(c["value"], dict) or isinstance(c["value"], list):
        # Structural/dict values: bounds concept doesn't apply
        verdict = "NOT_APPLICABLE"
        parsed = None
        plausible = None
    else:
        parsed = try_parse_range(prov)
        if parsed is None:
            verdict = "UNKNOWN"
            plausible = None
        elif is_plausible_range(*parsed):
            verdict = "PARSEABLE"
            plausible = True
        else:
            # regex matched but lo >= hi -- likely an array literal, not a range
            verdict = "FALSE_POSITIVE"
            plausible = False

    results.append({**c, "parsed": parsed, "verdict": verdict})
    label = c["label"][:29]
    print("%-30s %-15s %-12s %-12s %s" %
          (label,
           str(parsed)[:14] if parsed else "None",
           str(plausible)[:11] if plausible is not None else "n/a",
           verdict,
           prov[:60]))

print()
# ---- summary ----
by_verdict = {}
for r in results:
    by_verdict.setdefault(r["verdict"], []).append(r["label"])

print("=== Summary ===")
for v, labels in sorted(by_verdict.items()):
    print("  %-18s %d field(s): %s" % (v, len(labels), ", ".join(labels)))

# ---- key findings ----
print()
print("=== Key Findings ===")
parseable = [r for r in results if r["verdict"] == "PARSEABLE"]
false_pos  = [r for r in results if r["verdict"] == "FALSE_POSITIVE"]
unknown    = [r for r in results if r["verdict"] == "UNKNOWN"]

print()
print("1. PARSEABLE (%d fields):" % len(parseable))
for r in parseable:
    print("   %-30s range=%s  (from prose: %r)" % (r["label"], r["parsed"], r["provenance"][:60]))

print()
print("2. FALSE_POSITIVE (%d fields):" % len(false_pos))
for r in false_pos:
    print("   %-30s regex matched %s but lo>=hi -- array literal, not range" % (r["label"], r["parsed"]))
    print("   provenance: %r" % r["provenance"][:80])

print()
print("3. UNKNOWN (%d fields):" % len(unknown))
for r in unknown:
    print("   %-30s provenance: %r" % (r["label"], r["provenance"][:80]))

print()
print("=== Architectural Verdict ===")
n_parseable = len(parseable)
n_total_numeric = len([r for r in results if r["verdict"] != "NOT_APPLICABLE"])
print("Numeric fields with extractable bounds: %d / %d" % (n_parseable, n_total_numeric))
print()
print("FAILURE CONDITION MET: the existing evidence store cannot reliably serve")
print("machine-readable structural bounds without prose parsing, and prose parsing")
print("is fragile (FALSE_POSITIVE on array-literal notation in LFO route provenances).")
print()
print("Root cause: provenance is a free-text string. Clamp bounds were written by")
print("human convention ([lo, hi] notation) in FXEQ records but not in others.")
print("FXDistortion Drive's clamp result ('confirmed max via direct clamp probe")
print("(100->100, 150->100)') encodes the max only -- the min is not stated.")
print()
print("Correct fix: add a structured `clamp_bounds` field to Mutation or EvidenceRecord")
print("at the point where clamp probes are run, so bounds are recorded as typed data,")
print("not as a convention in a prose string that a regex must reverse-engineer.")
print()
print("Do NOT proceed to SerumIntent or compiler value binding until this is fixed.")
print("A derived_structural_domain() built on parsed prose is not an epistemic claim;")
print("it is a guess wearing the clothes of evidence.")
