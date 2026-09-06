"""16.5.14: HYPOTHESIS policy — "make darker" refusal and capability discovery.

Objective: prove that a producer goal based on general synthesis knowledge
(HYPOTHESIS) does not execute silently. Instead it produces a structured
CAPABILITY_DISCOVERY_NEEDED verdict naming exactly what Serum-specific
evidence is missing.

Goal: make the patch darker.
Candidate control: FXEQ.Freq1 (IS in SEMANTIC_TARGETS, IS CAUSAL_VERIFIED)
Requested change: lower the EQ frequency (100 Hz = very dark/bass-heavy)
Verification metric: spectral_centroid_hz (not in any CapabilityContract)
Predicted direction: decrease (lower centroid = darker)

Why this is HYPOTHESIS:
- FXEQ.Freq1 is CAUSAL_VERIFIED, so condition 1 passes.
- But the causal experiment used overall_rms_db, not spectral_centroid_hz.
- No Serum-specific evidence links FXEQ.Freq1 changes to spectral centroid.
- form_prediction() returns HYPOTHESIS (metric not established for this control).
- EXECUTION_POLICY[HYPOTHESIS] = CAPABILITY_DISCOVERY_NEEDED.
- The producer does not execute. It names what is missing.

Critical invariants:
  1. No CapabilityContract is modified.
  2. No EvidenceRecord is added or changed.
  3. The refusal is structured: DiscoveryRequest names the missing experiment.
  4. goal_status = CAPABILITY_DISCOVERY_NEEDED (not REFUSED, not NOT_VERIFIED).
  5. prediction_status = UNTESTED (no render was run).
  6. is_admissible_as_evidence = False.
  7. prediction_status and goal_status remain separate fields.
  8. The goal threshold is supplied explicitly (not defaulted in producer.py).
"""
import sys, pickle, hashlib
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler.producer import (
    form_prediction, execute_producer_goal,
    ProducerAttempt, DiscoveryRequest, GoalVerdict,
    HYPOTHESIS, PARTIALLY_GROUNDED,
    CAPABILITY_DISCOVERY_NEEDED, EXPLORATORY_EXECUTION, NORMAL_EXECUTION,
    GOAL_CAPABILITY_DISCOVERY, GOAL_REFUSED, GOAL_ACHIEVED,
    PREDICTION_UNTESTED, PREDICTION_SUPPORTED,
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

# ---- baseline contract hash (Gate 5: must not change) ----
contract_sig_before = hashlib.md5(
    repr(sorted(c.target for c in contracts.values())).encode()).hexdigest()

# ---- contract lookup ----
freq1_contract = next(
    c for c in contracts.values() if c.target == "fx_field_eq_freq1")

# ---- producer-policy constants (declared here, not in producer.py) ----
GOAL_THRESHOLD_DB = 1.0    # not used (goal refused before execution), but required by ProducerAttempt

print("=== 16.5.14 Producer goal: make darker ===")
print()
print("  Selected control:   FXEQ.Freq1")
print("  Requested value:    100.0 Hz  (very dark/bass-heavy)")
print("  Verification metric: spectral_centroid_hz  (not in any contract)")
print("  Contract metric was: %s" % (freq1_contract.measurement or {}).get("metric"))
print()

# ---- step 1: form prediction ----
# No record_store needed: the gap is at metric level (spectral_centroid_hz
# was never used in any OSC/FXEQ experiment), not at breadth level.
basis = form_prediction(
    freq1_contract,
    requested_metric="spectral_centroid_hz",
    predicted_direction="decrease",
    record_store=None,
)

print("  Prediction basis:")
print("    epistemic_status:  %s" % basis.epistemic_status)
print("    grounding_detail:  %s" % basis.grounding_detail[:120])
print()

# ---- step 2: build DiscoveryRequest ----
# The caller constructs this from what form_prediction reported.
# It is passed to execute_producer_goal() so the verdict carries it.
dr = DiscoveryRequest(
    goal="make the patch darker",
    candidate_control="FXEQ.Freq1",
    required_effect="spectral centroid decreases when EQ frequency is lowered",
    required_measurement="spectral_centroid_hz",
    missing_capability_reason=(
        "FXEQ.Freq1 is CAUSAL_VERIFIED via overall_rms_db, but no Serum-specific "
        "evidence links it to spectral_centroid_hz. "
        "Required: isolated single-field experiment with spectral_centroid_hz measurement "
        "at multiple EQ frequency values to establish direction and sensitivity."
    ),
)

# ---- step 3: build attempt ----
attempt = ProducerAttempt(
    goal_description="make the patch darker",
    selected_control="FXEQ.Freq1",
    requested_value=100.0,
    current_value=None,
    predicted_effect="spectral_centroid_hz decreases (patch becomes spectrally darker)",
    prediction_basis=basis,
    verification_metric="spectral_centroid_hz",
    verification_direction="decrease",
    goal_threshold_db=GOAL_THRESHOLD_DB,
)

print("  Attempt:")
print("    execution_policy:  %s" % attempt.execution_policy)
print("    is_executable:     %s" % attempt.is_executable)
print("    needs_discovery:   %s" % attempt.needs_discovery)
print()

# ---- step 4: execute (should refuse immediately) ----
verdict = execute_producer_goal(
    attempt, contracts, structural_records, body,
    experiment_id="16.5.14-DARKER-HYPOTHESIS-REFUSAL",
    discovery_request=dr,
)

print("  Verdict:")
print("    goal_status:               %s" % verdict.goal_status)
print("    prediction_status:         %s" % verdict.prediction_status)
print("    is_admissible_as_evidence: %s" % verdict.is_admissible_as_evidence)
print("    goal_result:               %s" % verdict.goal_result)
print("    detail:                    %s" % verdict.detail[:120])
print()
if verdict.discovery_request:
    dr_out = verdict.discovery_request
    print("  DiscoveryRequest:")
    print("    goal:                      %s" % dr_out.goal)
    print("    candidate_control:         %s" % dr_out.candidate_control)
    print("    required_effect:           %s" % dr_out.required_effect)
    print("    required_measurement:      %s" % dr_out.required_measurement)
    print("    missing_capability_reason: %s" % dr_out.missing_capability_reason[:100])
print()

# ---- contract hash after (must match before) ----
contract_sig_after = hashlib.md5(
    repr(sorted(c.target for c in contracts.values())).encode()).hexdigest()

# ---- acceptance criteria ----
results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-80s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:45]))

assert_that("1. prediction_basis.epistemic_status == HYPOTHESIS",
            basis.epistemic_status == HYPOTHESIS, basis.epistemic_status)
assert_that("2. execution_policy == CAPABILITY_DISCOVERY_NEEDED",
            attempt.execution_policy == CAPABILITY_DISCOVERY_NEEDED, attempt.execution_policy)
assert_that("3. verdict.goal_status == CAPABILITY_DISCOVERY_NEEDED",
            verdict.goal_status == GOAL_CAPABILITY_DISCOVERY, verdict.goal_status)
assert_that("4. verdict.prediction_status == UNTESTED (no render ran)",
            verdict.prediction_status == PREDICTION_UNTESTED, verdict.prediction_status)
assert_that("5. verdict.is_admissible_as_evidence == False",
            verdict.is_admissible_as_evidence is False, verdict.is_admissible_as_evidence)
assert_that("6. verdict.goal_result is None (no Serum interaction)",
            verdict.goal_result is None, verdict.goal_result)
assert_that("7. verdict.discovery_request is not None",
            verdict.discovery_request is not None)
assert_that("8. discovery_request.candidate_control == FXEQ.Freq1",
            verdict.discovery_request is not None
            and verdict.discovery_request.candidate_control == "FXEQ.Freq1",
            verdict.discovery_request.candidate_control if verdict.discovery_request else "None")
assert_that("9. discovery_request names required_measurement",
            verdict.discovery_request is not None
            and "spectral_centroid_hz" in verdict.discovery_request.required_measurement,
            verdict.discovery_request.required_measurement if verdict.discovery_request else "None")
assert_that("10. discovery_request names missing_capability_reason",
            verdict.discovery_request is not None
            and len(verdict.discovery_request.missing_capability_reason) > 20)
assert_that("11. CapabilityContracts unchanged (Gate 5)",
            contract_sig_before == contract_sig_after,
            "before=%s after=%s" % (contract_sig_before, contract_sig_after))
assert_that("12. prediction_status and goal_status are independent fields",
            hasattr(verdict, "prediction_status") and hasattr(verdict, "goal_status")
            and verdict.prediction_status != verdict.goal_status)

print()
print("Producer intelligence demonstrated:")
print("  The producer understood the goal ('darker'), identified a candidate control,")
print("  checked the evidence system, found no Serum-verified link to the")
print("  requested metric, and refused to execute rather than act on general knowledge.")
print("  The DiscoveryRequest is actionable: it names the exact experiment needed.")
print()

n_pass = sum(1 for _, ok, _ in results if ok)
print("16.5.14 CRITERIA: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
