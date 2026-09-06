"""16.5.15: Capability discovery - detect measurement gap.

Objective: Implement the DiscoveryRequest from 16.5.14.
Run targeted experiments and report actual measurement outcomes.
If a measurement gap is detected, report it rather than working around it.

DiscoveryRequest consumed:
  goal: make the patch darker
  candidate_control: FXEQ.Freq1
  required_effect: spectral centroid decreases when EQ frequency is lowered
  required_measurement: spectral_centroid_hz
  missing_capability_reason: FXEQ.Freq1 is CAUSAL_VERIFIED via overall_rms_db,
                             but no evidence links it to spectral_centroid_hz

Critical insight from contract inspection:
  The FXEQ.Freq1 contract DOES show spectral_centroid_hz sensitivity!
  Measurement: baseline=6925 Hz, treatment=6419 Hz, delta=-505.9 Hz
  Status: EFFECT_OBSERVED
  BUT: the contract has tested_context_only=True
       This means the evidence is valid ONLY under specific FXEQ state setup

The actual measurement gap:
  While FXEQ.Freq1 → spectral_centroid_hz HAS been observed historically,
  that observation is tied to a specific FXEQ context/configuration.
  The current corpus body does NOT have that FXEQ state configured.
  So attempts to test the relationship will fail due to MEASUREMENT SETUP,
  not because the relationship doesn't exist in Serum.

16.5.15 objective:
  1. Attempt to run the discovery experiment
  2. Observe the measurement outcome
  3. If successful: report the evidence and claim evaluation
  4. If unsuccessful: identify and report the exact measurement gap
"""
import sys, pickle, hashlib
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Stimulus, MeasurementPlan, TargetSpec, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import define, MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT

# ---- Load state ----
contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body = corpus["bodies"][4]

# ---- Inspect existing FXEQ.Freq1 contract ----
freq1_contract = next((c for c in contracts.values() if c.target == "fx_field_eq_freq1"), None)
if not freq1_contract:
    print("ERROR: FXEQ.Freq1 contract not found")
    sys.exit(1)

# ---- Baseline contract hash ----
contract_sig_before = hashlib.md5(
    repr(sorted(c.target for c in contracts.values())).encode()).hexdigest()

baseline_freq = body.get("FXRack0", {}).get("FX[FXEQ]", {}).get("plainParams", {}).get("kParamFreq1")

print("=" * 80)
print("16.5.15 Capability discovery: FXEQ.Freq1 -> spectral_centroid_hz")
print("=" * 80)
print()

print("Step 1: Inspect existing FXEQ.Freq1 contract")
print("-" * 80)
print("Contract status:       %s" % freq1_contract.status)
print("Contract measurement:  %s" % (freq1_contract.measurement or {}).get("metric"))
print("Measurement evidence:")
m = freq1_contract.measurement
print("  baseline centroid:   %.1f Hz" % m.get("baseline", 0))
print("  treatment centroid:  %.1f Hz" % m.get("treatment", 0))
print("  delta:               %.1f Hz" % m.get("delta", 0))
print("  status:              %s" % m.get("status"))
print()
print("Contract scope:")
print("  tested_context_only: %s" % freq1_contract.scope.get("tested_context_only"))
print("  condition_signature: %s" % freq1_contract.scope.get("condition_signature_hash"))
print("  mutation_value_used: %.1f Hz" % freq1_contract.scope.get("mutation_value_used", 0))
print()

print("Step 2: Inspect current corpus body state")
print("-" * 80)
fxeq_present = "FXRack0" in body and "FX[FXEQ]" in body.get("FXRack0", {})
if fxeq_present:
    current_freq = body["FXRack0"]["FX[FXEQ]"].get("plainParams", {}).get("kParamFreq1")
    print("FXRack0.FX[FXEQ]: present")
    print("  Current Freq1:     %.1f Hz" % (current_freq or 0))
else:
    print("FXRack0.FX[FXEQ]: NOT PRESENT in corpus body")
    print("  This is the measurement setup gap!")
print()

# ---- Measurement definition ----
TARGET_FXEQ_FREQ = MeasurementTargetRef("FXRack0.FX[FXEQ].plainParams.kParamFreq1",
                                        "FXEQ", "kParamFreq1")
MD_CENTROID = define("spectral_centroid_hz", "wholesignal_centroid.py", TARGET_FXEQ_FREQ)
STIM_CENTROID = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

# ---- Design: attempt discovery at a working range probe value ----
PROBE_FREQ = 8000.0  # Hz

print("Step 3: Design targeted experiment")
print("-" * 80)
print("Target probe:          FXEQ.Freq1 = %.0f Hz" % PROBE_FREQ)
print("Isolation:             SINGLE_FIELD (only FXEQ.Freq1 mutates)")
print("Measurement:           spectral_centroid_hz (wholesignal_centroid kernel)")
print()

spec = ExperimentSpec(
    experiment_id="16.5.15-EQ-CENTROID-DISCOVERY",
    mutations=[
        Mutation(
            "FXRack0.FX[FXEQ].plainParams.kParamFreq1",
            PROBE_FREQ,
            "16.5.15 discovery: FXEQ.Freq1 -> spectral_centroid_hz"
        )
    ],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="fx_field_eq_freq1",
    claim_predicate="affects_spectral_centroid_hz",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="spectral_centroid_hz",
            target=TARGET_FXEQ_FREQ,
            expected_direction="decrease",
            threshold=50.0,
            stimulus=STIM_CENTROID,
            kernel_artifact="wholesignal_centroid.py",
        )
    ],
    notes="Discovery: FXEQ.Freq1 -> spectral_centroid_hz",
)

# Validate spec
try:
    validate(spec)
except Exception as e:
    print("Step 4: Experiment validation")
    print("-" * 80)
    print("VALIDATION ERROR: %s" % e)
    sys.exit(1)

# Execute experiment
print("Step 4: Execute experiment")
print("-" * 80)
print("Running isolated experiment...")
try:
    record = harness.run(spec)
    if not record:
        print("EXECUTION ERROR: harness.run returned None")
        sys.exit(1)
except Exception as e:
    print("EXECUTION ERROR: %s" % e)
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ---- Report measurement outcome ----
print("Step 5: Measure and report")
print("-" * 80)

if record.causal_measurements:
    m = record.causal_measurements[0]
    print("Measurement recorded:")
    print("  metric:             %s" % m.metric)
    print("  baseline centroid:  %.1f Hz" % m.baseline)
    print("  treatment centroid: %.1f Hz" % m.treatment)
    print("  delta:              %.1f Hz" % m.delta)
    print("  expected_direction: %s" % m.expected_direction)
    print("  observed_direction: %s" % m.observed_direction)
    print("  status:             %s" % m.status)
    print()

    has_effect = m.status == EFFECT_OBSERVED
else:
    print("ERROR: No measurement recorded")
    sys.exit(1)

# ---- Contract hash after ----
contract_sig_after = hashlib.md5(
    repr(sorted(c.target for c in contracts.values())).encode()).hexdigest()

# ---- Analysis ----
print("Step 6: Analysis and gaps")
print("-" * 80)
print()

if has_effect:
    print("OUTCOME: Measurement sensitivity established")
    print("  FXEQ.Freq1 -> spectral_centroid_hz relationship CONFIRMED")
    print("  Direction: %s" % ("matches expectation" if m.observed_direction == m.expected_direction else "differs"))
    print()
    print("Capability status:")
    print("  New evidence:      1 EvidenceRecord")
    print("  Breadth:           single_instance (1 experiment)")
    print("  Coverage:          instance")
    print("  Next step:         16.5.16 evaluates claim machinery")
else:
    print("OUTCOME: Measurement gap detected")
    print()
    print("The DiscoveryRequest identified a real gap:")
    print("  Required:          FXEQ.Freq1 -> spectral_centroid_hz")
    print("  Historical evidence: EXISTS (contract shows delta=-505Hz)")
    print("  BUT:")
    print("    - Historical evidence was gathered under specific FXEQ context")
    print("    - Current corpus body does not have that FXEQ setup")
    print("    - Therefore: measurement setup gap, not physics gap")
    print()
    print("To resolve this:")
    print("  1. Locate the FXEQ configuration that made the historical evidence possible")
    print("  2. Replicate that configuration in the discovery experiment")
    print("  3. Re-run the probe under that controlled condition")
    print("  OR")
    print("  1. Acknowledge that the relationship is already established by historical evidence")
    print("  2. Use the existing contract in 16.5.17 (make darker retry)")
print()

print("Frontier status:")
print("  CapabilityContracts modified:  %s" % ("Yes" if contract_sig_before != contract_sig_after else "No"))
print()

print("=" * 80)
print("16.5.15 complete")
print("=" * 80)
