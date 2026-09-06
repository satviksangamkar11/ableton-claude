"""16.5.3: parameterization audit. Standalone, read-only checkpoint --
no schema changes, no capability promotion, no new experiments, no
compiler changes. Runs the frozen promoter to get the live ClaimEngine +
contracts, then reports, per contract, exactly what evidence exists."""
import sys, runpy, re
sys.path.insert(0, r"D:\ableton claude")

ns = runpy.run_path(r"D:\ableton claude\experiments\step15_2_2_promote.py", run_name="__audit__")
eng = ns["eng"]
contracts = ns["contracts"]

CLAMP_PROBE_MARKERS = ("clamp", "range", "ceiling", "floor")

def audit_group(key, group):
    cdef = group.claim_definition
    records = [eng.records[eid] for eid in group.supporting_evidence if eid in eng.records]

    distinct_values = {}
    causal_pass_values = set()
    persistence_pass_values = set()
    clamp_probe_mentioned = False

    for r in records:
        muts = r.experiment.get("mutations", [])
        if len(muts) != 1:
            continue
        val = muts[0]["value"]
        prov = (muts[0].get("provenance") or "")
        hashable_val = str(val) if isinstance(val, dict) else val
        distinct_values[hashable_val] = distinct_values.get(hashable_val, 0) + 1
        if any(m in prov.lower() for m in CLAMP_PROBE_MARKERS):
            clamp_probe_mentioned = True
        gate = r.gate_completeness()
        if gate.get("causal") == "PASS":
            causal_pass_values.add(hashable_val)
        if gate.get("persistence") == "PASS":
            persistence_pass_values.add(hashable_val)

    n_distinct = len(distinct_values)
    n_causal_distinct = len(causal_pass_values)
    n_persist_distinct = len(persistence_pass_values)

    if n_causal_distinct >= 2:
        classification = "DOMAIN_CANDIDATE(causal)"
    elif n_persist_distinct >= 2 and n_causal_distinct <= 1:
        classification = "STRUCTURAL_DOMAIN_CANDIDATE(persistence-only)"
    elif clamp_probe_mentioned:
        classification = "STRUCTURAL_BOUNDS_KNOWN(single causal point)"
    else:
        classification = "POINT"

    interval_representativeness = "N/A"
    if n_causal_distinct >= 2:
        interval_representativeness = ("UNKNOWN -- isolated points only, no evidence "
                                       "the interval BETWEEN them behaves consistently")

    return {
        "target": cdef.claim_type,
        "n_supporting_records": len(records),
        "n_distinct_values_tested": n_distinct,
        "n_distinct_causal_pass_values": n_causal_distinct,
        "n_distinct_persistence_pass_values": n_persist_distinct,
        "clamp_probe_mentioned_in_provenance": clamp_probe_mentioned,
        "classification": classification,
        "interval_representativeness": interval_representativeness,
    }

rows = [audit_group(k, g) for k, g in eng.groups.items()]
rows.sort(key=lambda r: r["target"])

print("%-38s %-6s %-8s %-8s %-8s %-6s %s" % (
    "target", "n_rec", "n_dist", "n_caus", "n_pers", "clamp", "classification"))
for r in rows:
    print("%-38s %-6d %-8d %-8d %-8d %-6s %s" % (
        r["target"][:38], r["n_supporting_records"], r["n_distinct_values_tested"],
        r["n_distinct_causal_pass_values"], r["n_distinct_persistence_pass_values"],
        "YES" if r["clamp_probe_mentioned_in_provenance"] else "no", r["classification"]))

from collections import Counter
counts = Counter(r["classification"] for r in rows)
print()
print("=== SUMMARY ===")
for cls, n in counts.most_common():
    print("  %-45s %d" % (cls, n))
print("  %-45s %d" % ("TOTAL", len(rows)))

print()
print("=== DOMAIN_CANDIDATE(causal) details (n_causal_distinct >= 2) ===")
for r in rows:
    if r["classification"] == "DOMAIN_CANDIDATE(causal)":
        print(" ", r["target"], "-> n_causal_distinct=%d, interval_representativeness=%s" % (
            r["n_distinct_causal_pass_values"], r["interval_representativeness"]))

print()
print("=== STRUCTURAL_BOUNDS_KNOWN details (clamp-probed, but only 1 causal point) ===")
for r in rows:
    if r["classification"] == "STRUCTURAL_BOUNDS_KNOWN(single causal point)":
        print(" ", r["target"])
