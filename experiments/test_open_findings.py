"""Regression test for the Open Findings Ledger. Two jobs:
  1. validate_ledger() must report zero problems against the real ledger --
     this is where evidence_ref hash-rot would surface, as a hard failure,
     never as a silent STALE status.
  2. Pin the 16.3-M1 taxonomy-collapse invariant: structural construction
     success + a measurement miss must remain LEGAL and DISTINCT from a
     construction/capability failure -- checked against the actual frozen
     compiler record, plus a structural import-graph guard proving findings
     can never write capability status.
"""
import sys, pickle, ast
sys.path.insert(0, r"D:\ableton claude")
from serum2 import findings

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-72s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:120]))

print("=== ledger validation ===")
ledger = findings.load_ledger(r"D:\ableton claude\experiments\OPEN_FINDINGS.json")
problems = findings.validate_ledger(ledger, base_dir=r"D:\ableton claude", check_hashes=True)
assert_that("ledger validates with zero problems", not problems, problems)
assert_that("ledger has exactly 4 findings (no silent growth/shrink)", len(ledger["findings"]) == 4,
           len(ledger["findings"]))
assert_that("every finding is OPEN (none prematurely closed)",
           all(f["status"] == "OPEN" for f in ledger["findings"]))
assert_that("Macro.name is NOT in the ledger (excluded per the locked triage decision)",
           not any("macro" in f["id"].lower() for f in ledger["findings"]))

print()
print("=== 16.3-M1 taxonomy-collapse invariant, pinned to the real frozen record ===")
rec = pickle.load(open(r"D:\ableton claude\experiments\_compiler_goal4_ctx_record.pkl", "rb"))
gate = rec.gate_completeness()
from serum2.compiler import kernel
result = kernel.evaluate_construction_goal(rec)

load_pass = gate.get("load") == "PASS"
matches_intent = rec.state_observation.get("matches_intent") is True
overall_pass = result["overall_pass"]
causal_outcome = rec.causal_measurements[0].status if rec.causal_measurements else None

assert_that("load == PASS", load_pass, gate.get("load"))
assert_that("state_observation.matches_intent is True", matches_intent)
assert_that("causal_outcome == NO_OBSERVED_EFFECT", causal_outcome == "NO_OBSERVED_EFFECT", causal_outcome)
assert_that("overall_pass == False", overall_pass is False, overall_pass)
assert_that("structural success + measurement miss coexist legally (no exception, no forced collapse)",
           load_pass and matches_intent and (overall_pass is False) and causal_outcome == "NO_OBSERVED_EFFECT")

assert_that("evaluate_construction_goal() output carries no capability-status-shaped key "
           "(no 'construction_status'/'capability_status' field to misread as failure/unsupported)",
           not any("status" in k and k not in ("state_matches_intent",) for k in result
                   if k not in ("load_pass", "persistence_pass", "overall_pass")),
           list(result.keys()))

print()
print("=== structural separation: findings cannot write capability status ===")
findings_src = open(r"D:\ableton claude\serum2\findings.py", encoding="utf-8").read()
admission_src = open(r"D:\ableton claude\serum2\evidence\admission.py", encoding="utf-8").read()
capcontract_src = open(r"D:\ableton claude\serum2\evidence\capability_contract.py", encoding="utf-8").read()

def imports_module(source: str, name: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(name in (a.name or "") for a in node.names):
                return True
        if isinstance(node, ast.ImportFrom):
            if node.module and name in node.module:
                return True
    return False

assert_that("findings.py does NOT import admission.py", not imports_module(findings_src, "admission"))
assert_that("findings.py does NOT import capability_contract.py",
           not imports_module(findings_src, "capability_contract"))
assert_that("admission.py does NOT import findings.py", not imports_module(admission_src, "findings"))
assert_that("capability_contract.py does NOT import findings.py",
           not imports_module(capcontract_src, "findings"))

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL OPEN FINDINGS ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
