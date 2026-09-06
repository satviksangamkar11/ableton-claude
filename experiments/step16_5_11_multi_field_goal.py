"""16.5.11: First multi-field producer goal.

Objective: prove the compiler can express and construct a coherent two-field
producer goal containing one caller-selected structural value (STRUCTURAL_BIND)
and one witness-backed value (WITNESS), using a single ExperimentSpec and one
Serum write.

Goal:
  FXEQ.Freq1   = 300.0 Hz         (STRUCTURAL_BIND: caller override, proven range)
  OSC1.Volume  = contract witness  (WITNESS: no override, replays contract value)

New compiler property being tested:
  - Per-field execution_mode is knowable and correctly labeled independently
  - Cross-context composition (FXRack0.FX[FXEQ] + Oscillator0) works atomically
  - overall_execution_mode = STRUCTURAL_BIND_MODE because at least one field has override
  - GoalResult.field(name) provides per-field outcome without ambiguity
  - Honest about what is shared: load/persistence/causal come from ONE record

Acceptance criteria:
  A. Both fields semantically resolved (no TargetRefusal)
  B. FXEQ.Freq1 execution_mode  = STRUCTURAL_BIND_MODE
  C. OSC1.Volume execution_mode = WITNESS_MODE
  D. FXEQ.Freq1 structural_status = ACCEPT (300.0 within proven range)
  E. OSC1.Volume structural_status = NOT_CHECKED (no override -> no gate)
  F. overall_accepted = True
  G. overall_execution_mode = STRUCTURAL_BIND_MODE
  H. load_status == PASS
  I. persistence_status == PASS
  J. FXEQ.Freq1 resolved_path contains "kParamFreq1"
  K. OSC1.Volume resolved_path contains "kParamVolume"
  L. GoalResult.field() lookups return the correct FieldResult for each name
  M. No cross-contract conflict (FXRack0 path vs Oscillator0 path)
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence.spec import Mutation
from serum2.compiler.result import produce_goal, GoalField, GoalResult, FieldResult
from serum2.compiler.kernel import WITNESS_MODE, STRUCTURAL_BIND_MODE
from serum2.compiler.structural_admission import ACCEPT, NOT_CHECKED

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
clamp_data = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))

structural_records = []
for recs in clamp_data["records"].values():
    structural_records.append(recs["below"])
    structural_records.append(recs["above"])

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body = corpus["bodies"][4]

EXP_ID = "16.5.11-MULTI-FREQ1-300HZ-OSC-VOLUME-WITNESS"

print("=== 16.5.11 Multi-field producer goal ===")
print()
print("  FXEQ.Freq1  = 300.0 Hz  [STRUCTURAL_BIND]")
print("  OSC1.Volume = witness   [WITNESS_MODE]")
print()

fxrack0_ctx = [Mutation("FXRack0", body["FXRack0"], "corpus FXRack0 context for 16.5.11")]

goal = produce_goal(
    [
        GoalField("FXEQ.Freq1",  300.0),   # structural bind
        GoalField("OSC1.Volume", None),     # witness replay
    ],
    contracts, structural_records, body,
    experiment_id=EXP_ID,
    baseline_overrides=fxrack0_ctx,
    measure_overall_rms=True,
)

print("  overall_accepted:        %s" % goal.overall_accepted)
print("  overall_execution_mode:  %s" % goal.overall_execution_mode)
print("  load_status:             %s" % goal.load_status)
print("  persistence_status:      %s" % goal.persistence_status)
print("  causal_status:           %s" % goal.causal_status)
if goal.refusal_reason:
    print("  REFUSED:                 %s -- %s" % (goal.refusal_reason, goal.refusal_detail))
print()

for fr in goal.fields:
    print("  Field: %-20s exec_mode=%-22s struct=%-12s path=%s" % (
        fr.name, fr.execution_mode, fr.structural_status,
        (fr.resolved_path or "NONE")[:60]))
print()

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-75s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:55]))

freq1 = goal.field("FXEQ.Freq1")
osc_vol = goal.field("OSC1.Volume")

assert_that("A. FXEQ.Freq1 resolved (not None)", freq1 is not None and freq1.resolved_ref is not None)
assert_that("A. OSC1.Volume resolved (not None)", osc_vol is not None and osc_vol.resolved_ref is not None)
assert_that("B. FXEQ.Freq1 execution_mode = STRUCTURAL_BIND_MODE",
            freq1 is not None and freq1.execution_mode == STRUCTURAL_BIND_MODE,
            freq1.execution_mode if freq1 else "MISSING")
assert_that("C. OSC1.Volume execution_mode = WITNESS_MODE",
            osc_vol is not None and osc_vol.execution_mode == WITNESS_MODE,
            osc_vol.execution_mode if osc_vol else "MISSING")
assert_that("D. FXEQ.Freq1 structural_status = ACCEPT",
            freq1 is not None and freq1.structural_status == ACCEPT,
            freq1.structural_status if freq1 else "MISSING")
assert_that("E. OSC1.Volume structural_status = NOT_CHECKED",
            osc_vol is not None and osc_vol.structural_status == NOT_CHECKED,
            osc_vol.structural_status if osc_vol else "MISSING")
assert_that("F. overall_accepted = True", goal.overall_accepted)
assert_that("G. overall_execution_mode = STRUCTURAL_BIND_MODE",
            goal.overall_execution_mode == STRUCTURAL_BIND_MODE, goal.overall_execution_mode)
assert_that("H. load_status == PASS", goal.load_status == "PASS", goal.load_status)
assert_that("I. persistence_status == PASS", goal.persistence_status == "PASS", goal.persistence_status)
assert_that("J. FXEQ.Freq1 resolved_path contains kParamFreq1",
            freq1 is not None and freq1.resolved_path is not None
            and "kParamFreq1" in (freq1.resolved_path or ""),
            freq1.resolved_path if freq1 else "NONE")
assert_that("K. OSC1.Volume resolved_path contains kParamVolume",
            osc_vol is not None and osc_vol.resolved_path is not None
            and "kParamVolume" in (osc_vol.resolved_path or ""),
            osc_vol.resolved_path if osc_vol else "NONE")
assert_that("L. field('FXEQ.Freq1') lookup returns correct FieldResult",
            freq1 is not None and freq1.name == "FXEQ.Freq1")
assert_that("L. field('OSC1.Volume') lookup returns correct FieldResult",
            osc_vol is not None and osc_vol.name == "OSC1.Volume")
assert_that("M. no cross-contract conflict (overall_accepted)",
            goal.overall_accepted and goal.refusal_reason is None)

print()
print("Per-field execution mode summary (the new property):")
print("  %-20s -> %s (structural_status=%s)" % (
    "FXEQ.Freq1", freq1.execution_mode if freq1 else "?",
    freq1.structural_status if freq1 else "?"))
print("  %-20s -> %s (structural_status=%s)" % (
    "OSC1.Volume", osc_vol.execution_mode if osc_vol else "?",
    osc_vol.structural_status if osc_vol else "?"))
print()
print("Shared gates (one construction, one EvidenceRecord):")
print("  load=%s  persistence=%s  causal=%s" % (
    goal.load_status, goal.persistence_status, goal.causal_status))
print()
print("Honest constraint verified: per-field causal isolation is NOT claimed.")
print("(One Serum render -> one measurement -> one overall causal_status.)")

print()
pickle.dump({"goal": goal, "experiment_id": EXP_ID},
            open(r"D:\ableton claude\experiments\_multi_field_goal_16_5_11.pkl", "wb"))
print("Saved to _multi_field_goal_16_5_11.pkl")

n_pass = sum(1 for _, ok, _ in results if ok)
print()
print("16.5.11 CRITERIA: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
