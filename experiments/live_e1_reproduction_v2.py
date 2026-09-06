"""14.3: real live E1, wired to the archived windowed_mean_centroid kernel --
the SAME kernel that produced historical E1's 946.04 Hz result."""
import sys, json
sys.path.insert(0, r"D:\ableton claude")

from serum2 import codec
from serum2.evidence import fixtures, harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite,
                                  Stimulus, MeasurementPlan, TargetSpec, SINGLE_FIELD)
from serum2.evidence.record import PASS
from serum2.evidence.claim import (ClaimDefinition, ClaimEngine, CONSISTENT,
                                   FAMILY, COMPARABLE, NOT_COMPARABLE,
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
        target=TargetSpec("VoiceFilter0.plainParams.kParamFreq", "VoiceFilter", "kParamFreq"),
        expected_direction="increase",
        threshold=100.0,
        stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
        kernel_artifact="windowed_mean_centroid.py",   # historical kernel, not whole-signal
    )],
    notes="live reproduction of historical E1, wired to the archived kernel",
)

print("=== 14.1/14.3: RUNNING LIVE HARNESS WITH ARCHIVED KERNEL ===")
rec = harness.run(spec)

print("epoch (execution)   :", rec.epoch["execution_epoch_id"])
print("gates                :", rec.gate_completeness())
print("runtime verified     :", rec.runtime_verified())
m = rec.causal_measurements[0]
print("measurement_definition_id :", m.measurement_definition_id)
print("causal: base=%.2f treat=%.2f delta=%+.2f dir=%s status=%s"
      % (m.baseline, m.treatment, m.delta, m.observed_direction, m.status))
print("persistence          :", rec.persistence_observation["status"])

hist = fixtures.e1()
hm = hist.causal_measurements[0]
print()
print("=== 14.2 CHECK: no silent <no_measurement> ===")
assert m.measurement_definition_id is not None, "FAIL: measurement_definition_id is None"
print("measurement_definition_id is NOT None: PASS")

print()
print("=== HISTORICAL vs LIVE ===")
print("historical measurement_definition_id:", hm.measurement_definition_id)
print("live       measurement_definition_id:", m.measurement_definition_id)
same_def = hm.measurement_definition_id == m.measurement_definition_id
print("SAME measurement_definition_id:", same_def)
print("historical delta: %+.2f  |  live delta: %+.2f" % (hm.delta, m.delta))
print("live treatment ~946 Hz:", abs(m.treatment - 946.04) < 5.0)
print("live delta ~+597 Hz  :", abs(m.delta - 597.30) < 5.0)

DEF = ClaimDefinition(
    claim_type="modulation_route_effect", subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect", required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2,
                   "scope_on_satisfy": FAMILY},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "spectral_centroid_hz",
                          "target": "VoiceFilter0.plainParams.kParamFreq"},
)
eng = ClaimEngine({"route": DEF})
eng.add(fixtures.e0(), "route")
eng.add(hist, "route")
g = eng.add(rec, "route")

print()
print("=== CLAIM ADJUDICATION (real engine, unmodified cohort logic) ===")
print("cohorts       :", g.derived_cohorts())
print("primary cohort:", g.derived_primary_cohort())
print("comparability :", g.derived_comparability())
print("coverage_scope:", g.derived_coverage_scope())
print("breadth       :", g.derived_breadth())
print("contradiction :", g.derived_contradiction_state())

verdict = "CORROBORATES" if (g.derived_comparability().get("E1-live") == COMPARABLE
                             and g.derived_contradiction_state() == CONSISTENT) else "NOT_COMPARABLE_OR_CONTRADICTS"
print()
print("VERDICT:", verdict)

print()
print("=== 14.3 ASSERTIONS ===")
checks = [
    ("measurement_definition_id matches historical", same_def),
    ("comparability = COMPARABLE", g.derived_comparability().get("E1-live") == COMPARABLE),
    ("E0/E1/E1-live share primary cohort",
     set(g.derived_cohorts().get(g.derived_primary_cohort(), [])) >= {"E0", "E1", "E1-live"}),
    ("no contradiction", g.derived_contradiction_state() == CONSISTENT),
    ("live treatment ~946 Hz", abs(m.treatment - 946.04) < 5.0),
    ("live delta ~+597 Hz", abs(m.delta - 597.30) < 5.0),
    ("verdict = CORROBORATES", verdict == "CORROBORATES"),
]
ok = True
for label, cond in checks:
    ok &= cond
    print("%-4s %s" % ("PASS" if cond else "FAIL", label))
print()
print("14.3 OVERALL:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
