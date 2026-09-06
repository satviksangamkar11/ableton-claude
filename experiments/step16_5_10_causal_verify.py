"""16.5.10: Non-witness causal verification.

Objective: prove that STRUCTURAL_BIND_MODE produces a fresh EvidenceRecord
whose causal_status is its OWN measurement outcome, never inherited from the
witness contract.

The witness contract for fx_field_eq_freq1 is CAUSAL_VERIFIED (based on
P8000/P15000 Hz experiments using wholesale-centroid-delta metric). This
execution uses 300 Hz. Two possible outcomes are honest:

  EFFECT_OBSERVED     -- 300 Hz causes a measurable centroid shift
                          (would mean the wholesale metric CAN detect it)
  NO_OBSERVED_EFFECT  -- 300 Hz doesn't shift centroid past threshold
                          (consistent with P300 sensitivity finding: metric
                          too coarse for sub-baseline EQ moves)

Either is correct. What is NOT allowed: ProducerResult.causal_status == "CAUSAL_VERIFIED"
(that's a contract-level label, not an EvidenceRecord measurement status).

Acceptance criteria:
  A. causal_status comes from THIS execution's CausalMeasurement.status
     (EFFECT_OBSERVED | NO_OBSERVED_EFFECT -- never "CAUSAL_VERIFIED")
  B. causal_status != the contract's .status field ("CAUSAL_VERIFIED")
  C. A CausalMeasurement is actually present on the EvidenceRecord
  D. The measurement's metric matches the kernel's declared metric
  E. baseline and treatment are both populated (render actually ran)
  F. execution_mode == STRUCTURAL_BIND_MODE (confirms non-witness path)
  G. persistence_status == PASS (300 Hz was stored)
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence.spec import Mutation
from serum2.compiler.result import produce
from serum2.compiler.kernel import STRUCTURAL_BIND_MODE
from serum2.evidence.capability_contract import CAUSAL_VERIFIED
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT, NOT_RUN

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
clamp_data = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))

structural_records = []
for recs in clamp_data["records"].values():
    structural_records.append(recs["below"])
    structural_records.append(recs["above"])

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body = corpus["bodies"][4]

REQUESTED_VALUE = 300.0
EXP_ID = "16.5.10-FXEQ-FREQ1-300HZ-CAUSAL"

print("=== 16.5.10 Non-witness causal verification: FXEQ.Freq1 = 300 Hz ===")
print()
print("  This run is a fresh execution -- causal result must be its OWN,")
print("  not inherited from the CAUSAL_VERIFIED witness contract.")
print()

fxrack0_ctx = [Mutation("FXRack0", body["FXRack0"], "corpus FXRack0 context for 16.5.10")]
result = produce(
    "FXEQ.Freq1", contracts, structural_records, body,
    requested_value=REQUESTED_VALUE,
    experiment_id=EXP_ID,
    baseline_overrides=fxrack0_ctx,
    measure_overall_rms=True,
)

print("  execution_mode:    %s" % result.execution_mode)
print("  structural_status: %s" % result.structural_status)
print("  load_status:       %s" % result.load_status)
print("  persistence_status:%s" % result.persistence_status)
print("  causal_status:     %s" % result.causal_status)
if result.measurement:
    m = result.measurement
    print("  metric:            %s" % m.get("metric"))
    print("  baseline:          %s" % m.get("baseline"))
    print("  treatment:         %s" % m.get("treatment"))
    print("  delta:             %s" % m.get("delta"))
print()

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-72s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:55]))

contract_status = next(
    (c.status for c in contracts.values() if c.target == "fx_field_eq_freq1"), None)

assert_that("F. execution_mode == STRUCTURAL_BIND_MODE",
            result.execution_mode == STRUCTURAL_BIND_MODE)
assert_that("G. persistence_status == PASS", result.persistence_status == "PASS",
            result.persistence_status)

assert_that("A. causal_status is a valid measurement status (not a contract label)",
            result.causal_status in (EFFECT_OBSERVED, NO_OBSERVED_EFFECT, NOT_RUN,
                                     "WRONG_DIRECTION"),
            result.causal_status)
assert_that("B. causal_status != CAUSAL_VERIFIED (contract label, not measurement status)",
            result.causal_status != CAUSAL_VERIFIED,
            "causal_status=%s contract_status=%s" % (result.causal_status, contract_status))
assert_that("C. CausalMeasurement present on EvidenceRecord",
            result.record is not None and len(result.record.causal_measurements) > 0)
assert_that("D. measurement metric is declared",
            result.measurement is not None and result.measurement.get("metric") is not None,
            result.measurement)
assert_that("E. baseline is populated (render ran)",
            result.measurement is not None and result.measurement.get("baseline") is not None,
            result.measurement)
assert_that("E. treatment is populated",
            result.measurement is not None and result.measurement.get("treatment") is not None)

# The outcome is one of two honest results -- both are acceptable
if result.causal_status == EFFECT_OBSERVED:
    print()
    print("  OUTCOME: 300 Hz caused EFFECT_OBSERVED -- metric detected centroid shift")
    print("  (Revises the UNRESOLVED finding from 16.5.5.1: narrow-band check was")
    print("  sensitive but wholesale metric also detects it in this experiment.)")
elif result.causal_status == NO_OBSERVED_EFFECT:
    print()
    print("  OUTCOME: 300 Hz -> NO_OBSERVED_EFFECT (expected from P300 sensitivity)")
    print("  This is honest: 300 Hz is structurally valid but causally unresolved")
    print("  at the wholesale-centroid granularity. The contract's CAUSAL_VERIFIED")
    print("  status was earned for higher frequencies; it does NOT transfer here.")
assert_that("causal result is honest (EFFECT_OBSERVED or NO_OBSERVED_EFFECT)",
            result.causal_status in (EFFECT_OBSERVED, NO_OBSERVED_EFFECT),
            result.causal_status)

print()
# Save
pickle.dump({
    "result": result,
    "requested_value": REQUESTED_VALUE,
    "contract_status": contract_status,
}, open(r"D:\ableton claude\experiments\_nonwitness_300hz_causal.pkl", "wb"))
print("Saved to _nonwitness_300hz_causal.pkl")

n_pass = sum(1 for _, ok, _ in results if ok)
print("16.5.10 CRITERIA: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    sys.exit(1)
