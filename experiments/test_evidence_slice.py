"""Data-only vertical slice test. No Serum execution."""
import sys
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence import fixtures
from serum2.evidence.record import PASS, FAIL, NOT_RUN, NOT_RECORDED
from serum2.evidence.claim import (
    ClaimDefinition, ClaimEngine,
    SINGLE_FIELD, CONTROLLED_MULTI_FIELD,
    INSTANCE, FAMILY, SINGLE_INSTANCE, SAMPLED,
    CONSISTENT, CONTRADICTED,
    FIELD_ATTRIBUTION, INTERACTION_ATTRIBUTION,
    OBJECTIVELY_MEASURABLE,
)

results = []


def assert_that(label, condition, detail=""):
    results.append((label, bool(condition), detail))
    print("%-4s %-58s %s" % ("PASS" if condition else "FAIL", label, detail))


# ---------------------------------------------------------------- definitions
ROUTE_EFFECT = ClaimDefinition(
    claim_type="modulation_route_effect",
    subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"],
                   "family_min_distinct": 2, "scope_on_satisfy": FAMILY},
    contradiction_rule={"incompatible_outcomes": [["effect", "no_effect"]],
                        "require_same_mutation": True},
    dependency_rule={"enabled": True, "require_same_mutation": True,
                     "require_declared_condition_difference": True,
                     "require_isolated_condition_difference": True,
                     "require_runtime_verified": True,
                     "require_outcome_difference": True},
    measurability=OBJECTIVELY_MEASURABLE,
)

# Same policy, but not requiring runtime verification -- used to show the
# dependency rule is what gates the relationship, not correlation.
ROUTE_EFFECT_NO_RTV = ClaimDefinition(
    claim_type="modulation_route_effect_no_rtv",
    subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"],
                   "family_min_distinct": 2, "scope_on_satisfy": FAMILY},
    contradiction_rule={"incompatible_outcomes": [["effect", "no_effect"]],
                        "require_same_mutation": True},
    dependency_rule={"enabled": True, "require_same_mutation": True,
                     "require_declared_condition_difference": True,
                     "require_isolated_condition_difference": True,
                     "require_runtime_verified": False,
                     "require_outcome_difference": True},
)

COEXISTENCE = ClaimDefinition(
    claim_type="route_coexistence",
    subject_pattern={"kind": "modulation_route_pair"},
    predicate="coexist_without_interference",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(CONTROLLED_MULTI_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"incompatible_outcomes": [["effect", "no_effect"]]},
    dependency_rule={"enabled": False},
)

E0, E1, E2a, E2b, E3 = fixtures.all_real()
SYN = fixtures.synthetic_contradiction_of_e0()

print("=== FIXTURES LOADED ===")
for r in [E0, E1, E2a, E2b, E3, SYN]:
    print("  %-22s gates=%s synthetic=%s" % (r.experiment_id, r.gate_completeness(), r.is_synthetic))
print()

print("=== ASSERTIONS ===")

# ---- E0 ----
assert_that("E0 causal gate = PASS", E0.gate("causal") == PASS)
assert_that("E0 carries no interpretation fields",
            not any(hasattr(E0, a) for a in ("status", "confidence", "coverage_scope", "breadth")))
assert_that("E0 unrecorded generation is explicit, not invented",
            E0.state_observation["detail"] == NOT_RECORDED,
            "state_observation.detail=%s" % E0.state_observation["detail"])

eng = ClaimEngine({"route": ROUTE_EFFECT})
g_e0 = eng.add(E0, "route")
assert_that("E0 alone -> instance scope", g_e0.derived_coverage_scope() == INSTANCE,
            "scope=%s" % g_e0.derived_coverage_scope())
assert_that("E0 alone -> single_instance breadth", g_e0.derived_breadth() == SINGLE_INSTANCE)

# ---- E0 + E1 : slot-index independence ----
eng2 = ClaimEngine({"route": ROUTE_EFFECT})
eng2.add(E0, "route")
g01 = eng2.add(E1, "route")
same_group = (g_e0.condition_signature_hash == g01.condition_signature_hash)
assert_that("E0+E1 share condition signature (same prereqs+stimulus)", same_group)
assert_that("E0+E1 -> FAMILY scope via slot_index dimension",
            g01.derived_coverage_scope() == FAMILY,
            "scope=%s supporting=%s" % (g01.derived_coverage_scope(), list(g01.supporting_evidence)))
assert_that("E0+E1 -> sampled breadth", g01.derived_breadth() == SAMPLED)
assert_that("no writable scope field exists on ClaimGroup",
            not any(f in ClaimDefinition.__dataclass_fields__ or f in g01.__dict__
                    for f in ("coverage_scope", "breadth", "confidence", "contradiction_state")))
assert_that("E0+E1 field attribution allowed (single_field)",
            g01.derived_attribution() == FIELD_ATTRIBUTION)

# ---- two-level condition identity (E3 drove this) ----
assert_that("E3 carries TWO distinct measurement conditions",
            len({m.measurement_condition_signature["hash"]
                 for m in E3.causal_measurements}) == 2)
assert_that("E3 measurements share ONE experiment condition",
            len({m.measurement_condition_signature["experiment_hash"]
                 for m in E3.causal_measurements}) == 1)
assert_that("changing a measurement stimulus does NOT change experiment condition",
            E3.causal_measurements[0].measurement_condition_signature["experiment_hash"]
            == E3.experiment["experiment_condition_signature"]["hash"])
assert_that("E0/E1 share experiment AND measurement condition",
            E0.experiment["experiment_condition_signature"]["hash"]
            == E1.experiment["experiment_condition_signature"]["hash"]
            and E0.causal_measurements[0].measurement_condition_signature["hash"]
            == E1.causal_measurements[0].measurement_condition_signature["hash"])
assert_that("E2a/E2b differ at EXPERIMENT condition level",
            E2a.experiment["experiment_condition_signature"]["hash"]
            != E2b.experiment["experiment_condition_signature"]["hash"])

# ---- E2a ----
assert_that("E2a causal gate = FAIL", E2a.gate("causal") == FAIL)
assert_that("E2a measurement status = NO_OBSERVED_EFFECT",
            E2a.causal_measurements[0].status == "NO_OBSERVED_EFFECT")
assert_that("E2a does NOT become NON_AUDIBLE_BY_DESIGN",
            "NON_AUDIBLE_BY_DESIGN" not in str(E2a.to_dict()))

# ---- E2b ----
assert_that("E2b causal gate = PASS", E2b.gate("causal") == PASS)

# ---- E2a + E2b : dependency, not contradiction ----
eng3 = ClaimEngine({"route": ROUTE_EFFECT})
ga = eng3.add(E2a, "route")
gb = eng3.add(E2b, "route")
assert_that("E2a/E2b land in DIFFERENT claim groups", ga is not gb)
assert_that("E2a/E2b produce NO contradiction",
            ga.derived_contradiction_state() == CONSISTENT and
            gb.derived_contradiction_state() == CONSISTENT)
eng3.derive_relationships()
rels_strict = list(ga.relationships) + list(gb.relationships)
assert_that("dependency NOT derived when runtime verification required "
            "(historical runs lack it)", len(rels_strict) == 0,
            "relationships=%d" % len(rels_strict))

eng4 = ClaimEngine({"route": ROUTE_EFFECT_NO_RTV})
ga4 = eng4.add(E2a, "route")
gb4 = eng4.add(E2b, "route")
eng4.derive_relationships()
rels = list(ga4.relationships)
assert_that("dependency IS derived when rule permits", len(rels) == 1,
            "relationships=%d" % len(rels))
if rels:
    assert_that("dependency isolates exactly the Macro 8 condition",
                rels[0]["differing_condition_fields"] == ["host:Macro 8"],
                str(rels[0]["differing_condition_fields"]))

# ---- E3 ----
eng5 = ClaimEngine({"coexist": COEXISTENCE, "route": ROUTE_EFFECT})
g3 = eng5.add(E3, "coexist")
assert_that("E3 supports coexistence claim", g3 is not None and
            len(g3.supporting_evidence) == 1)
assert_that("E3 attribution = interaction, NOT field",
            g3.derived_attribution() == INTERACTION_ATTRIBUTION,
            g3.derived_attribution())
rejected_before = len(eng5.rejected)
eng5.add(E3, "route")
assert_that("E3 rejected from field-level claim definition",
            len(eng5.rejected) == rejected_before + 1,
            eng5.rejected[-1]["reason"] if eng5.rejected else "")

# ---- synthetic contradiction ----
# A definition that explicitly admits synthetic records, used ONLY to exercise
# contradiction handling. Real-capability definitions refuse them (asserted below).
CONTRADICTION_TESTBED = ClaimDefinition(
    claim_type="contradiction_testbed",
    subject_pattern={"kind": "modulation_route", "allow_synthetic": True},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2},
    contradiction_rule={"incompatible_outcomes": [["effect", "no_effect"]],
                        "require_same_mutation": True},
    dependency_rule={"enabled": False},
)
eng6 = ClaimEngine({"route": CONTRADICTION_TESTBED})
eng6.add(E0, "route")
gsyn = eng6.add(SYN, "route")
assert_that("synthetic contradiction fires",
            gsyn is not None and gsyn.derived_contradiction_state() == CONTRADICTED,
            "state=%s" % (gsyn.derived_contradiction_state() if gsyn else "None"))
assert_that("contradicted group flagged reverify_required",
            bool(gsyn and gsyn.reverify["required"]))
assert_that("reverify names both comparison conditions",
            bool(gsyn and len(gsyn.reverify["required_comparison_conditions"]) == 2))

# synthetic must not contribute to real capability claims
REAL_ONLY = ClaimDefinition(
    claim_type="modulation_route_effect_real_only",
    subject_pattern={"kind": "modulation_route", "allow_synthetic": False},
    predicate="produces_measurable_effect",
    required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,),
    breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2},
    contradiction_rule={"incompatible_outcomes": [["effect", "no_effect"]]},
    dependency_rule={"enabled": False},
)
eng7 = ClaimEngine({"route": REAL_ONLY})
eng7.add(E0, "route")
before = len(eng7.rejected)
eng7.add(SYN, "route")
assert_that("synthetic excluded from real-capability claim",
            len(eng7.rejected) == before + 1)

print()
n_pass = sum(1 for _, ok, _ in results if ok)
print("ALL ASSERTIONS: %d/%d PASS" % (n_pass, len(results)))
if n_pass != len(results):
    print("FAILURES:")
    for label, ok, detail in results:
        if not ok:
            print("  -", label, detail)
    sys.exit(1)
