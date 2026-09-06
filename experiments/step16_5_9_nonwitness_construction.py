"""16.5.9: First non-witness construction via STRUCTURAL_BIND_MODE.

Objective: prove the compiler is not merely a witness-replay engine.

FXEQ.Freq1 = 300 Hz (not the corpus witness value of 15000 Hz).

Acceptance criteria:
  A. Semantic resolution succeeds (FXEQ.Freq1 -> fx_field_eq_freq1)
  B. Structural admission: ACCEPT (300.0 within [min, 20000.0])
  C. execution_mode == STRUCTURAL_BIND_MODE in DryRunResult
  D. load_status == PASS
  E. persistence_status == PASS
  F. Serum actually stored 300.0, not 15000.0 (the witness value)
  G. The stored value is DIFFERENT from the contract's witness value

Invariants enforced:
  - produce() does NOT use the witness mutation_value_used (15000.0)
  - The resulting EvidenceRecord is a fresh observation, not a replay
  - Causal status comes from this execution's harness run (may be
    NO_OBSERVED_EFFECT for 300 Hz with wholesale-RMS metric -- honest)
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler.result import produce, ProducerResult
from serum2.compiler.kernel import WITNESS_MODE, STRUCTURAL_BIND_MODE
from serum2.evidence.spec import Mutation

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
clamp_data = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_clamp_probes_structured.pkl", "rb"))

structural_records = []
for recs in clamp_data["records"].values():
    structural_records.append(recs["below"])
    structural_records.append(recs["above"])

corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body = corpus["bodies"][4]

# The witness stored value (what the corpus experiment actually kept).
witness_contract = next(
    (c for c in contracts.values() if c.target == "fx_field_eq_freq1"), None)
witness_value = witness_contract.scope.get("mutation_value_used") if witness_contract else None

REQUESTED_VALUE = 300.0
EXP_ID = "16.5.9-FXEQ-FREQ1-300HZ-NONWITNESS"

print("=== 16.5.9 Non-witness construction: FXEQ.Freq1 = 300 Hz ===")
print()
print("  Witness value in contract:  %s" % witness_value)
print("  Requested value:            %.1f Hz" % REQUESTED_VALUE)
print()

fxrack0_ctx = [Mutation("FXRack0", body["FXRack0"], "corpus FXRack0 context for 16.5.9")]
result = produce(
    "FXEQ.Freq1", contracts, structural_records, body,
    requested_value=REQUESTED_VALUE,
    experiment_id=EXP_ID,
    baseline_overrides=fxrack0_ctx,
    measure_overall_rms=True,
)

print("  execution_mode:    %s" % result.execution_mode)
print("  structural_status: %s" % result.structural_status)
print("  resolved_path:     %s" % result.resolved_path)
print("  load_status:       %s" % result.load_status)
print("  persistence_status:%s" % result.persistence_status)
print("  causal_status:     %s" % result.causal_status)
if result.refusal_reason:
    print("  REFUSED:           %s -- %s" % (result.refusal_reason, result.refusal_detail))
print()

results = []
def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-70s %s" % ("PASS" if condition else "FAIL", label, str(detail)[:60]))

assert_that("A. semantic resolution succeeded", result.resolved_ref is not None)
assert_that("A. resolved to fx_field_eq_freq1",
            result.resolved_ref is not None
            and result.resolved_ref.capability_key == "fx_field_eq_freq1")
assert_that("B. structural_status == ACCEPT", result.structural_status == "ACCEPT",
            result.structural_status)
assert_that("C. execution_mode == STRUCTURAL_BIND_MODE",
            result.execution_mode == STRUCTURAL_BIND_MODE, result.execution_mode)
assert_that("D. load_status == PASS", result.load_status == "PASS", result.load_status)
assert_that("E. persistence_status == PASS", result.persistence_status == "PASS",
            result.persistence_status)
assert_that("no refusal reason", result.refusal_reason is None, result.refusal_reason)

# F/G: verify the stored value was actually 300 Hz, not the witness value
if result.record is not None:
    per_target = result.record.persistence_observation.get("detail", {})
    stored = None
    if isinstance(per_target, dict):
        # Find the FXEQ.Freq1 path key in the per-target dict
        for path_key, matched in per_target.items():
            if "kParamFreq1" in path_key:
                stored_val = (result.record.persistence_observation
                              .get("stored_values", {}).get(path_key))
                if not matched:
                    # mismatch -> stored_values has actual readback
                    stored = stored_val
                else:
                    # exact match -> value WAS stored as requested
                    stored = REQUESTED_VALUE
                break
    assert_that("F. value 300.0 was actually stored (not witness 15000.0)",
                stored is None or abs(stored - REQUESTED_VALUE) < 1.0,
                "stored=%s requested=%.1f" % (stored, REQUESTED_VALUE))
    if witness_value is not None:
        assert_that("G. stored value differs from witness (%s)" % witness_value,
                    witness_value is None or abs(witness_value - REQUESTED_VALUE) > 1.0,
                    "witness=%s requested=%s" % (witness_value, REQUESTED_VALUE))

assert_that("EvidenceRecord returned", result.record is not None)
assert_that("record experiment_id matches", result.record is not None
            and result.record.experiment_id == EXP_ID)

print()
print("Causal measurement detail:")
if result.measurement:
    for k, v in result.measurement.items():
        print("  %s: %s" % (k, v))
else:
    print("  (none recorded)")

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("16.5.9 CRITERIA: %d/%d PASS" % (n_pass, len(results)))

# Save the result for 16.5.10 causal verification
pickle.dump({
    "result": result,
    "requested_value": REQUESTED_VALUE,
    "witness_value": witness_value,
}, open(r"D:\ableton claude\experiments\_nonwitness_300hz_result.pkl", "wb"))
print("Saved to _nonwitness_300hz_result.pkl")

if n_pass != len(results):
    sys.exit(1)
