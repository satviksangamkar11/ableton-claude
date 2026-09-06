"""First live harness integration: reproduce E1 (Aardvark ModSlot0 -> empty
ModSlot30) through the evidence pipeline.

The historical E1 record is IMMUTABLE. This run produces a NEW record in the
CURRENT epoch; the ClaimEngine then decides whether it corroborates or conflicts.
"""
import sys, json
sys.path.insert(0, r"D:\ableton claude")

from serum2 import codec
from serum2.evidence import fixtures, harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite,
                                  Stimulus, MeasurementPlan, TargetSpec, SINGLE_FIELD)
from serum2.evidence.record import PASS
from serum2.evidence.claim import (ClaimDefinition, ClaimEngine, CONSISTENT,
                                   CONTRADICTED, FAMILY, SAMPLED, INSTANCE,
                                   SINGLE_INSTANCE, FIELD_ATTRIBUTION,
                                   OBJECTIVELY_MEASURABLE)

AARDVARK = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
_, aardvark_body = codec.load_preset_file(AARDVARK)
ROUTE = aardvark_body["ModSlot0"]

spec = ExperimentSpec(
    experiment_id="E1-live",
    mutations=[Mutation("ModSlot30", ROUTE, "Aardvark ModSlot0")],
    prerequisites=[Prerequisite("host:Filter 1 On", 1.0)],
    isolation_level=SINGLE_FIELD,
    claim_subject="modulation_route:VoiceFilter.kParamFreq",
    claim_predicate="produces_measurable_effect",
    measurement_plans=[MeasurementPlan(
        metric="spectral_centroid_hz",
        target=TargetSpec("VoiceFilter0.plainParams.kParamFreq",
                          "VoiceFilter", "kParamFreq"),
        expected_direction="increase",
        threshold=100.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="windowed_mean_centroid.py",   # SAME kernel as historical E1
    )],
    notes="live reproduction of historical E1",
)

print("=== RUNNING LIVE HARNESS ===")
rec = harness.run(spec)

print("epoch:", rec.epoch["evidence_epoch_id"])
print("gates:", rec.gate_completeness())
print("runtime verified:", rec.runtime_verified())
for v in rec.runtime_verifications:
    print("  runtime verification:", v["verified"], v["failures"] or "")
print("state:", {k: rec.state_observation[k] for k in
                 ("status", "matches_intent", "control_hash", "treatment_hash")})
for m in rec.causal_measurements:
    print("causal: %s base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
          % (m.metric, m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence:", rec.persistence_observation["status"],
      rec.persistence_observation.get("detail"))

# ---- compare with historical E1 (semantic, not byte-identical) ----
hist = fixtures.e1()
print()
print("=== HISTORICAL vs LIVE (semantic equivalence) ===")
hm, lm = hist.causal_measurements[0], rec.causal_measurements[0]
print("metric match          :", hm.metric == lm.metric)
print("target match          :", hm.target.module == lm.target.module and
                                 hm.target.parameter == lm.target.parameter)
print("direction match       :", hm.observed_direction == lm.observed_direction)
print("status match          :", hm.status == lm.status)
print("historical delta      : %+.2f" % hm.delta)
print("live delta            : %+.2f" % lm.delta)
print("delta within 5%%       :", abs(lm.delta - hm.delta) / abs(hm.delta) < 0.05)
print("measurement cond match:",
      hm.measurement_condition_signature["hash"] == lm.measurement_condition_signature["hash"])
print("experiment cond match :",
      hist.experiment["experiment_condition_signature"]["hash"]
      == rec.experiment["experiment_condition_signature"]["hash"])
print("mutation sig match    :",
      hist.experiment["mutation_signature"] == rec.experiment["mutation_signature"])
print("epochs differ (expected, immutability preserved):",
      hist.epoch["evidence_epoch_id"] != rec.epoch["evidence_epoch_id"])

# ---- ClaimEngine adjudication ----
DEF = ClaimDefinition(
    claim_type="modulation_route_effect",
    subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"],
                   "family_min_distinct": 2, "scope_on_satisfy": FAMILY},
    contradiction_rule={"require_same_mutation": True,
                        "require_comparable_measurement": True},
    dependency_rule={"enabled": False},
    measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "spectral_centroid_hz",
                          "target": "VoiceFilter0.plainParams.kParamFreq"},
)
eng = ClaimEngine({"route": DEF})
eng.add(fixtures.e0(), "route")
eng.add(hist, "route")
g = eng.add(rec, "route")

print()
print("=== CLAIM ADJUDICATION ===")
print(json.dumps({k: v for k, v in g.summary().items()
                  if k not in ("derived_gate_completeness",)}, indent=1, default=str))
comp = g.derived_comparability().get(rec.experiment_id)
print()
print("comparability of live record:", comp)
if comp == "NOT_COMPARABLE":
    verdict = "NOT_COMPARABLE (different measurement kernel)"
elif g.derived_contradiction_state() == CONSISTENT and rec.experiment_id in g.supporting_evidence:
    verdict = "CORROBORATES"
else:
    verdict = "CONTRADICTS"
print("VERDICT:", verdict)
