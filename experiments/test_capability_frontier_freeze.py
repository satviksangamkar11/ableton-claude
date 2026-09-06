"""15.5: Capability Frontier Freeze enforcement.

Re-runs the full promotion pipeline from source evidence (not from a cached
pickle) and confirms the resulting contracts + family inventory hash-match
the frozen snapshot in CAPABILITY_FRONTIER_FREEZE.json. This is the actual
freeze mechanism: any future change to evidence, claim definitions, the
contract builder, or the family inventory that silently shifts what the
system believes it can do will fail this test loudly, rather than drifting
unnoticed. A deliberate, reviewed change to the frontier means regenerating
CAPABILITY_FRONTIER_FREEZE.json on purpose -- this test never does that itself.
"""
import sys, json, subprocess, hashlib
from collections import Counter
sys.path.insert(0, r"D:\ableton claude")

FREEZE_PATH = r"D:\ableton claude\experiments\CAPABILITY_FRONTIER_FREEZE.json"

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-70s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:120]))

frozen = json.load(open(FREEZE_PATH, encoding="utf-8"))

print("=== re-running the full promotion pipeline from source evidence ===")
proc = subprocess.run([sys.executable, r"D:\ableton claude\experiments\step15_2_2_promote.py"],
                     capture_output=True, text=True, timeout=300)
assert_that("promoter script exits 0", proc.returncode == 0, proc.stderr[-500:] if proc.returncode else "")
assert_that("promoter reports no rejected records", "rejected: []" in proc.stdout, "")

import pickle
contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
inv = pickle.load(open(r"D:\ableton claude\experiments\_capability_inventory.pkl", "rb"))

def jsonable(x):
    if isinstance(x, tuple): return [jsonable(v) for v in x]
    if isinstance(x, dict): return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, list): return [jsonable(v) for v in x]
    return x

contracts_out = {"%s|%s" % (cdid, cond): jsonable(c.to_dict())
                 for (cdid, cond), c in sorted(contracts.items(), key=lambda kv: (kv[0][0], kv[0][1]))}
inv_out = {fam: jsonable(fc.to_dict()) for fam, fc in sorted(inv.items())}
status_counts = dict(Counter(c["status"] for c in contracts_out.values()))

print()
print("=== structural comparison against the frozen snapshot ===")
assert_that("contract_count unchanged", len(contracts_out) == frozen["contract_count"],
           "now=%d frozen=%d" % (len(contracts_out), frozen["contract_count"]))
assert_that("family_count unchanged", len(inv_out) == frozen["family_count"],
           "now=%d frozen=%d" % (len(inv_out), frozen["family_count"]))
assert_that("status_counts unchanged", status_counts == frozen["status_counts"],
           "now=%s frozen=%s" % (status_counts, frozen["status_counts"]))

# Per-target status regression: no target may SILENTLY move to a stronger
# status without a deliberate re-freeze -- this is the guard against exactly
# the kind of laundering 15.3/15.4 were built to prevent.
frozen_status_by_key = {k: v["status"] for k, v in frozen["contracts"].items()}
now_status_by_key = {k: v["status"] for k, v in contracts_out.items()}
changed = {k: (frozen_status_by_key.get(k), now_status_by_key.get(k))
          for k in set(frozen_status_by_key) | set(now_status_by_key)
          if frozen_status_by_key.get(k) != now_status_by_key.get(k)}
assert_that("no contract's status changed vs the frozen snapshot", not changed, changed)

blob = json.dumps({
    "freeze_id": frozen["freeze_id"], "pipeline": frozen["pipeline"],
    "contract_count": len(contracts_out), "family_count": len(inv_out),
    "status_counts": status_counts, "contracts": contracts_out, "family_inventory": inv_out,
}, sort_keys=True).encode("utf-8")
recomputed_hash = hashlib.sha256(blob).hexdigest()
assert_that("full content hash matches frozen snapshot exactly",
           recomputed_hash == frozen["content_hash"],
           "now=%s frozen=%s" % (recomputed_hash, frozen["content_hash"]))

print()
print("=== named guard cases still hold at the frozen boundary ===")
type1 = contracts_out.get([k for k in contracts_out if "fx_field_eq_kParamType1" in k][0])
assert_that("FXEQ.Type1 still NEGATIVE... structural, never CAUSAL_VERIFIED",
           type1["status"] != "CAUSAL_VERIFIED", type1["status"])
lfo_key = [k for k in contracts_out if "lfo_as_modulation_source" in k][0]
assert_that("LFO-as-source still NEGATIVE_EVIDENCE, never CAUSAL_VERIFIED",
           contracts_out[lfo_key]["status"] != "CAUSAL_VERIFIED", contracts_out[lfo_key]["status"])
macro_key = [k for k in contracts_out if "macro_field_name" in k][0]
assert_that("Macro.name still NEGATIVE_EVIDENCE (persistence FAIL), never promoted",
           contracts_out[macro_key]["status"] == "NEGATIVE_EVIDENCE", contracts_out[macro_key]["status"])

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL FRONTIER FREEZE ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
