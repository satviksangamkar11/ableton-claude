"""Step 10: re-adjudicate under the measurement-identity model. Data-only."""
import sys
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence import fixtures
from serum2.evidence.record import PASS, EvidenceRecord, CausalMeasurement, MeasurementTarget, NO_OBSERVED_EFFECT, EFFECT_OBSERVED
from serum2.evidence.measurement import define, MeasurementTargetRef
from serum2.evidence.claim import (
    ClaimDefinition, ClaimEngine, SINGLE_FIELD, CONTROLLED_MULTI_FIELD,
    INSTANCE, FAMILY, SINGLE_INSTANCE, SAMPLED, CONSISTENT, CONTRADICTED,
    COMPARABLE, NOT_COMPARABLE, FIELD_ATTRIBUTION, INTERACTION_ATTRIBUTION,
    OBJECTIVELY_MEASURABLE,
)

results = []


def a(label, cond, detail=""):
    results.append((label, bool(cond), detail))
    print("%-4s %-62s %s" % ("PASS" if cond else "FAIL", label, detail))


E0, E1, E2a, E2b, E3 = fixtures.all_real()
SYN = fixtures.synthetic_contradiction_of_e0()

TARGET_VF = "VoiceFilter0.plainParams.kParamFreq"
TARGET_FX = "FXRack0.FX[FXDelay].plainParams.kParamWet"

ROUTE_VF = ClaimDefinition(
    claim_type="modulation_route_effect",
    subject_pattern={"kind": "modulation_route"},
    predicate="causal_effect",
    required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"],
                   "family_min_distinct": 2, "scope_on_satisfy": FAMILY},
    contradiction_rule={"require_same_mutation": True,
                        "require_comparable_measurement": True},
    dependency_rule={"enabled": False},
    measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "spectral_centroid_hz", "target": TARGET_VF},
)
ROUTE_FX = ClaimDefinition(
    claim_type="modulation_route_effect",
    subject_pattern={"kind": "modulation_route"},
    predicate="causal_effect",                      # SAME broad predicate
    required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True},
    dependency_rule={"enabled": True, "require_same_mutation": True,
                     "require_declared_condition_difference": True,
                     "require_isolated_condition_difference": True,
                     "require_runtime_verified": False,
                     "require_same_measurement_definition": True,
                     "require_outcome_difference": True},
    required_measurement={"metric_name": "tail_rms_db", "target": TARGET_FX},
)

print("=== IDENTITY ===")
a("same predicate, different required_measurement -> different claim id",
  ROUTE_VF.claim_definition_id != ROUTE_FX.claim_definition_id,
  "%s vs %s" % (ROUTE_VF.claim_definition_id, ROUTE_FX.claim_definition_id))

print()
print("=== E0 + E1 : same kernel, family claim must SURVIVE ===")
eng = ClaimEngine({"vf": ROUTE_VF})
eng.add(E0, "vf")
g = eng.add(E1, "vf")
a("E0/E1 share one cohort", len(g.derived_cohorts()) == 1, str(list(g.derived_cohorts())))
a("both COMPARABLE", set(g.derived_comparability().values()) == {COMPARABLE})
a("family scope preserved", g.derived_coverage_scope() == FAMILY, g.derived_coverage_scope())
a("sampled breadth preserved", g.derived_breadth() == SAMPLED)

print()
print("=== E1-live style (wholesignal kernel) must be NOT_COMPARABLE ===")
MD_WS = define("spectral_centroid_hz", "wholesignal_centroid.py",
               MeasurementTargetRef(TARGET_VF, "VoiceFilter", "kParamFreq"))
live = EvidenceRecord(
    experiment_id="E1-live", epoch=dict(E1.epoch, execution_epoch_id="live"),
    experiment=E1.experiment, arms=E1.arms, runtime_verifications=(),
    state_observation=E1.state_observation, load_observation={"status": PASS},
    render_observation={"status": PASS},
    causal_measurements=(CausalMeasurement(
        metric="spectral_centroid_hz",
        target=MeasurementTarget(TARGET_VF, "VoiceFilter", "kParamFreq"),
        baseline=349.14, treatment=1402.92, delta=1053.78,
        expected_direction="increase", observed_direction="increase",
        threshold=100.0, status=EFFECT_OBSERVED,
        measurement_condition_signature=E1.causal_measurements[0].measurement_condition_signature,
        measurement_definition_id=MD_WS.measurement_definition_id),),
    persistence_observation={"status": PASS, "exact_match": True})
g2 = eng.add(live, "vf")
comp = g2.derived_comparability()
a("E1-live forms a second cohort", len(g2.derived_cohorts()) == 2, str(list(g2.derived_cohorts())))
a("E1-live is NOT_COMPARABLE", comp.get("E1-live") == NOT_COMPARABLE, str(comp))
a("E1-live is NOT a contradiction", g2.derived_contradiction_state() == CONSISTENT)
a("family scope still from the comparable cohort", g2.derived_coverage_scope() == FAMILY)
a("E1-live excluded from qualifying evidence",
  "E1-live" not in [r.experiment_id for r in g2._qualifying()])

print()
print("=== E2a + E2b : same kernel, dependency must SURVIVE ===")
eng2 = ClaimEngine({"fx": ROUTE_FX})
ga = eng2.add(E2a, "fx")
gb = eng2.add(E2b, "fx")
a("E2a/E2b in different claim groups", ga is not gb)
a("no contradiction", ga.derived_contradiction_state() == CONSISTENT)
eng2.derive_relationships()
rels = list(ga.relationships)
a("prerequisite_dependency survives kernel identity", len(rels) == 1, "n=%d" % len(rels))
if rels:
    a("dependency isolates Macro 8", rels[0]["differing_condition_fields"] == ["host:Macro 8"])

print()
print("=== E3 : different centroid kernel from E0/E1 ===")
e3_centroid = [m for m in E3.causal_measurements if m.metric == "spectral_centroid_hz"][0]
a("E3 centroid kernel differs from E0/E1 kernel",
  e3_centroid.measurement_definition_id != E0.causal_measurements[0].measurement_definition_id)
a("E3 tail kernel matches E2a/E2b kernel",
  [m for m in E3.causal_measurements if m.metric == "tail_rms_db"][0].measurement_definition_id
  == E2a.causal_measurements[0].measurement_definition_id)

print()
print("=== admissibility: wrong property cannot support a claim ===")
eng3 = ClaimEngine({"vf": ROUTE_VF})
before = len(eng3.rejected)
eng3.add(E2b, "vf")          # tail_rms_db evidence vs a centroid claim
a("tail evidence rejected by centroid claim", len(eng3.rejected) == before + 1)

print()
print("=== synthetic contradiction still fires (same kernel) ===")
TESTBED = ClaimDefinition(
    claim_type="contradiction_testbed",
    subject_pattern={"kind": "modulation_route", "allow_synthetic": True},
    predicate="causal_effect",
    required_gate={"load": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True,
                        "require_comparable_measurement": True},
    dependency_rule={"enabled": False},
    required_measurement={"metric_name": "spectral_centroid_hz", "target": TARGET_VF},
)
eng4 = ClaimEngine({"t": TESTBED})
eng4.add(E0, "t")
gs = eng4.add(SYN, "t")
a("synthetic contradiction fires", gs.derived_contradiction_state() == CONTRADICTED)
a("reverify required", gs.reverify["required"])

print()
n = sum(1 for _, ok, _ in results if ok)
print("ALL ASSERTIONS: %d/%d PASS" % (n, len(results)))
if n != len(results):
    for l, ok, d in results:
        if not ok:
            print("  FAIL:", l, d)
    sys.exit(1)
