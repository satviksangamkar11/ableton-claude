"""16.5.13: First closed-loop producer goal — "make this patch quieter."

Objective: prove the producer reasoning loop works end-to-end:
  goal → hypothesis formation → prediction with provenance →
  execution → measurement → prediction evaluation → goal verdict

The prediction is formed by the evidence system, not asserted:
  - form_prediction() checks the four grounding conditions
  - query_claim_coverage() (in claim.py) provides authoritative coverage/breadth
  - Expected result: PARTIALLY_GROUNDED (OSC-VOLUME is SINGLE_INSTANCE breadth)
  - Execution proceeds as EXPLORATORY_EXECUTION
  - is_admissible_as_evidence = False (exploratory result ≠ capability evidence)

Prediction and goal verdicts are kept separate:
  prediction_status: SUPPORTED | CONTRADICTED | INCONCLUSIVE | UNTESTED
  goal_status:       ACHIEVED  | INSUFFICIENT | NOT_VERIFIED  | REFUSED

Goal threshold (1.0 dB) is a producer-policy choice declared explicitly here,
not a default buried in producer.py.

Acceptance criteria:
  A. prediction_basis.epistemic_status == PARTIALLY_GROUNDED
     (OSC-VOLUME: CAUSAL_VERIFIED, metric linked, direction verified,
      but SINGLE_INSTANCE breadth → cannot claim GROUNDED)
  B. execution_policy == EXPLORATORY_EXECUTION
  C. is_admissible_as_evidence == False
  D. goal_result.overall_accepted == True (Serum construction succeeded)
  E. goal_result.persistence_status == PASS (value was stored)
  F. prediction_status in (SUPPORTED, INCONCLUSIVE)
     -- direction check is honest; either outcome is acceptable
  G. goal_status separates from prediction_status:
     - if prediction_status == SUPPORTED and magnitude >= threshold → ACHIEVED
     - if prediction_status == SUPPORTED and magnitude < threshold → INSUFFICIENT
     - if prediction_status == INCONCLUSIVE → NOT_VERIFIED (distinct from ACHIEVED)
  H. GoalVerdict carries the full GoalResult for traceability
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence.spec import Mutation
from serum2.compiler.producer import (
    form_prediction, execute_producer_goal,
    ProducerAttempt, GoalVerdict,
    PARTIALLY_GROUNDED, GROUNDED,
    EXPLORATORY_EXECUTION, NORMAL_EXECUTION,
    GOAL_ACHIEVED, GOAL_INSUFFICIENT, GOAL_NOT_VERIFIED, GOAL_REFUSED,
    PREDICTION_SUPPORTED, PREDICTION_INCONCLUSIVE, PREDICTION_CONTRADICTED,
)

# ---- load state ----
contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
clamp_data = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))
structural_records = []
for recs in clamp_data["records"].values():
    structural_records.append(recs["below"])
    structural_records.append(recs["above"])

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body = corpus["bodies"][4]

osc_records_raw = pickle.load(open(r"D:\ableton claude\experiments\_osc_records.pkl", "rb"))
# Build a flat record_store keyed by experiment_id for query_claim_coverage
record_store = {}
for key, val in osc_records_raw.items():
    if isinstance(val, list):
        for r in val:
            record_store[r.experiment_id] = r
    else:
        record_store[val.experiment_id] = val

# ---- contract lookup ----
osc_contract = next(
    c for c in contracts.values() if c.target == "oscillator_field_OSC-VOLUME")
current_volume = body.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")

# ---- producer-policy constants (declared here, not in producer.py) ----
GOAL_THRESHOLD_DB = 1.0   # minimum magnitude change to call the goal ACHIEVED
TARGET_VOLUME = 0.15      # quieter than current (0.337); above witness (0.05)

print("=== 16.5.13 Producer goal: make quieter ===")
print()
print("  Current OSC1.Volume: %.4f" % current_volume)
print("  Target  OSC1.Volume: %.4f" % TARGET_VOLUME)
print("  Goal threshold:      %.1f dB" % GOAL_THRESHOLD_DB)
print()

# ---- step 1: form prediction with authoritative coverage query ----
basis = form_prediction(
    osc_contract,
    requested_metric="overall_rms_db",
    predicted_direction="decrease",
    record_store=record_store,      # passed so query_claim_coverage can run
)

print("  Prediction basis:")
print("    capability_key:     %s" % basis.capability_key)
print("    epistemic_status:   %s" % basis.epistemic_status)
print("    metric_sensitivity: %s" % basis.metric_sensitivity)
print("    claim_breadth:      %s" % basis.claim_breadth)
print("    claim_coverage:     %s" % basis.claim_coverage_scope)
print("    grounding_detail:   %s" % basis.grounding_detail[:100])
print()

# ---- step 2: build attempt ----
attempt = ProducerAttempt(
    goal_description="make this patch quieter",
    selected_control="OSC1.Volume",
    requested_value=TARGET_VOLUME,
    current_value=current_volume,
    predicted_effect="overall_rms_db decreases when OSC1.Volume is reduced",
    prediction_basis=basis,
    verification_metric="overall_rms_db",
    verification_direction="decrease",
    goal_threshold_db=GOAL_THRESHOLD_DB,
)

print("  Attempt:")
print("    selected_control:   %s" % attempt.selected_control)
print("    requested_value:    %.4f" % attempt.requested_value)
print("    execution_policy:   %s" % attempt.execution_policy)
print("    is_executable:      %s" % attempt.is_executable)
print()

# ---- step 3: execute ----
verdict = execute_producer_goal(
    attempt, contracts, structural_records, body,
    experiment_id="16.5.13-PRODUCER-QUIETER-OSC-VOL-015",
    baseline_overrides=None,   # Oscillator0 needs no special context
)

print("  Verdict:")
print("    goal_status:              %s" % verdict.goal_status)
print("    prediction_status:        %s" % verdict.prediction_status)
print("    is_admissible_as_evidence:%s" % verdict.is_admissible_as_evidence)
print("    detail:                   %s" % verdict.detail[:100])
if verdict.measurement:
    m = verdict.measurement
    print("    metric:     %s" % m.get("metric"))
    print("    baseline:   %.4f dB" % m.get("baseline", 0))
    print("    treatment:  %.4f dB" % m.get("treatment", 0))
    print("    delta:      %.4f dB" % m.get("delta", 0))
    print("    rms_status: %s" % m.get("status"))
print()

# ---- acceptance criteria ----
results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-75s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:50]))

assert_that("A. prediction_basis.epistemic_status == PARTIALLY_GROUNDED",
            basis.epistemic_status == PARTIALLY_GROUNDED, basis.epistemic_status)
assert_that("B. execution_policy == EXPLORATORY_EXECUTION",
            attempt.execution_policy == EXPLORATORY_EXECUTION, attempt.execution_policy)
assert_that("C. is_admissible_as_evidence == False",
            verdict.is_admissible_as_evidence is False, verdict.is_admissible_as_evidence)
assert_that("D. goal_result.overall_accepted == True",
            verdict.goal_result is not None and verdict.goal_result.overall_accepted,
            verdict.goal_result.overall_accepted if verdict.goal_result else "None")
assert_that("E. goal_result.persistence_status == PASS",
            verdict.goal_result is not None
            and verdict.goal_result.persistence_status == "PASS",
            verdict.goal_result.persistence_status if verdict.goal_result else "None")
assert_that("F. prediction_status is honest (SUPPORTED or INCONCLUSIVE)",
            verdict.prediction_status in (PREDICTION_SUPPORTED, PREDICTION_INCONCLUSIVE),
            verdict.prediction_status)
assert_that("G. goal_status is consistent with prediction_status",
            not (verdict.prediction_status == PREDICTION_SUPPORTED
                 and verdict.goal_status == GOAL_NOT_VERIFIED)
            and not (verdict.prediction_status == PREDICTION_INCONCLUSIVE
                     and verdict.goal_status == GOAL_ACHIEVED),
            "goal=%s prediction=%s" % (verdict.goal_status, verdict.prediction_status))
assert_that("H. GoalVerdict carries GoalResult for traceability",
            verdict.goal_result is not None)

print()
print("Epistemic summary:")
print("  OSC1.Volume causal evidence: single-instance witness at %.2f" %
      (osc_contract.scope.get("mutation_value_used", 0.0)))
print("  Requested change: %.4f -> %.4f" % (current_volume, TARGET_VOLUME))
print("  Prediction grounding: %s (GROUNDED requires SAMPLED breadth via claim machinery)" %
      basis.epistemic_status)
print("  This run is EXPLORATORY: informative to producer loop, not admissible as capability evidence.")
print()

n_pass = sum(1 for _, ok, _ in results if ok)
print("16.5.13 CRITERIA: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
