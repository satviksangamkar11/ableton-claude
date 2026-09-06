"""Step 15.1: build the v8 capability inventory from existing proven evidence
plus statemodel.py's family enumeration. No new Serum experiments."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")

from serum2 import statemodel, bridge
from serum2.evidence import fixtures
from serum2.evidence.claim import (ClaimDefinition, ClaimEngine, SINGLE_FIELD,
                                   CONTROLLED_MULTI_FIELD, FAMILY, OBJECTIVELY_MEASURABLE)
from serum2.evidence.record import PASS
from serum2 import capability

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
skel_meta, skel_body = bridge.capture_v8_skeleton(VST3)
families = statemodel.module_families(skel_body)

# ---- claim definitions for every family of evidence we actually have ----
ROUTE_VF = ClaimDefinition(
    claim_type="modulation_route_voicefilter", subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect", required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": ["slot_index"], "family_min_distinct": 2,
                   "scope_on_satisfy": FAMILY},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": False}, measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "spectral_centroid_hz",
                          "target": "VoiceFilter0.plainParams.kParamFreq"},
)
ROUTE_FX = ClaimDefinition(
    claim_type="modulation_route_fxdelay", subject_pattern={"kind": "modulation_route"},
    predicate="produces_measurable_effect", required_gate={"load": PASS, "causal": PASS},
    required_isolation=(SINGLE_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True, "require_comparable_measurement": True},
    dependency_rule={"enabled": True, "require_same_mutation": True,
                     "require_declared_condition_difference": True,
                     "require_isolated_condition_difference": True,
                     "require_runtime_verified": False, "require_outcome_difference": True},
    measurability=OBJECTIVELY_MEASURABLE,
    required_measurement={"metric_name": "tail_rms_db",
                          "target": "FXRack0.FX[FXDelay].plainParams.kParamWet"},
)
COEXIST = ClaimDefinition(
    claim_type="route_coexistence", subject_pattern={"kind": "modulation_route_pair"},
    predicate="coexist_without_interference",
    required_gate={"load": PASS, "causal": PASS, "persistence": PASS},
    required_isolation=(CONTROLLED_MULTI_FIELD,), breadth_rule={"sampled_min": 2},
    coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 2},
    contradiction_rule={"require_same_mutation": True}, dependency_rule={"enabled": False},
)

eng = ClaimEngine({"vf": ROUTE_VF, "fx": ROUTE_FX, "coexist": COEXIST})
E0, E1, E2a, E2b, E3 = fixtures.all_real()
eng.add(E0, "vf"); eng.add(E1, "vf")
eng.add(E2a, "fx"); eng.add(E2b, "fx")
eng.add(E3, "coexist")

OPEN_MAPPING = {"lfoPointModAssignments", "midiMap"}
# these are v5-only families -- not in the v8 `families` dict at all, so they
# must be added explicitly as open decisions per the instruction not to drop them
if "lfoPointModAssignments" not in families:
    families["lfoPointModAssignments"] = {"instances": 1, "indexed": False, "index_range": None}
if "midiMap" not in families:
    families["midiMap"] = {"instances": 1, "indexed": False, "index_range": None}

inv = capability.build_inventory(families, eng, open_mapping_families=OPEN_MAPPING)

print(capability.report(inv))
print()
print("=== FAMILIES WITH EVIDENCE-BACKED PROMOTION ===")
for fam, fc in sorted(inv.items()):
    if fc.status not in (capability.UNKNOWN, capability.MAPPING_DECISION_REQUIRED):
        print("  %-14s status=%-18s evidence=%s claim_groups=%s"
              % (fam, fc.status, fc.evidence, fc.claim_groups))

print()
print("=== OPEN MAPPING DECISIONS (explicitly carried forward, not blocking) ===")
for fam, fc in sorted(inv.items()):
    if fc.status == capability.MAPPING_DECISION_REQUIRED:
        print("  %-24s %s" % (fam, fc.open_mapping_decision))

pickle.dump(inv, open(r"D:\ableton claude\experiments\_capability_inventory.pkl", "wb"))
