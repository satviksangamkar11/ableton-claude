"""Step 15.1: v8 capability inventory.

Distinction from statemodel.py: statemodel tells us WHAT EXISTS. This module
tells us WHAT WE CAN SAFELY DO WITH IT -- and only claims that by reading
already-derived ClaimGroup status, never by manual assertion.

Every family starts UNKNOWN. A family is promoted only when a real ClaimGroup
in the evidence system reports PROVEN/SAMPLED for it. No family is ever marked
UNSUPPORTED merely because we haven't looked yet -- that status is reserved for
a family Serum has demonstrably rejected.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

UNKNOWN = "UNKNOWN"
MAPPING_DECISION_REQUIRED = "MAPPING_DECISION_REQUIRED"
CONSTRUCTIBLE = "CONSTRUCTIBLE"        # we can build valid v8 state containing it
MUTABLE = "MUTABLE"                    # + we can change it and Serum accepts the change
PERSISTENT_STRUCTURAL = "PERSISTENT_STRUCTURAL"  # + Serum's re-save preserves it, causal NOT attempted
CAUSALLY_VERIFIED = "CAUSALLY_VERIFIED"  # + a measurable effect was demonstrated
PERSISTENT = "PERSISTENT"              # + causal AND Serum's own re-save preserves it
UNSUPPORTED = "UNSUPPORTED"            # Serum demonstrably rejects it (not "untested")

CAPABILITY_ORDER = [UNKNOWN, MAPPING_DECISION_REQUIRED, CONSTRUCTIBLE,
                    MUTABLE, PERSISTENT_STRUCTURAL, CAUSALLY_VERIFIED, PERSISTENT, UNSUPPORTED]


@dataclass
class FamilyCapability:
    family: str
    status: str = UNKNOWN
    evidence: List[str] = field(default_factory=list)       # experiment_ids
    claim_groups: List[str] = field(default_factory=list)   # claim_definition_ids
    prerequisites: List[Dict[str, Any]] = field(default_factory=list)
    open_mapping_decision: Optional[str] = None
    notes: str = ""

    def to_dict(self):
        return {
            "family": self.family, "status": self.status,
            "evidence": self.evidence, "claim_groups": self.claim_groups,
            "prerequisites": self.prerequisites,
            "open_mapping_decision": self.open_mapping_decision,
            "notes": self.notes,
        }


def status_from_claim_group(group) -> str:
    """Derive a capability status from a REAL ClaimGroup's own derived methods.
    Never asserted -- if the group can't answer, the family stays UNKNOWN."""
    if group is None:
        return UNKNOWN
    gc = group.derived_gate_completeness()
    if not gc:
        return UNKNOWN
    any_persistence_pass = any(g.get("persistence") == "PASS" for g in gc.values())
    any_causal_pass = any(g.get("causal") == "PASS" for g in gc.values())
    any_load_pass = any(g.get("load") == "PASS" for g in gc.values())
    any_generation_pass = any(g.get("generation") == "PASS" for g in gc.values())

    if any_persistence_pass and any_causal_pass:
        return PERSISTENT
    if any_causal_pass:
        return CAUSALLY_VERIFIED
    if any_persistence_pass and any_load_pass:
        # Persistence proven (Serum's own re-save preserves the write), but
        # causal effect was never attempted -- e.g. an LFO parameter with no
        # active route. Distinct from MUTABLE: this is stronger evidence,
        # just not the same claim as CAUSALLY_VERIFIED.
        return PERSISTENT_STRUCTURAL
    if any_load_pass:
        return MUTABLE
    if any_generation_pass:
        return CONSTRUCTIBLE
    return UNKNOWN


def build_inventory(module_families: Dict[str, Any], claim_engine=None,
                    open_mapping_families=()) -> Dict[str, FamilyCapability]:
    """module_families: output of statemodel.module_families(skeleton_body).
    claim_engine: an evidence.claim.ClaimEngine holding real ClaimGroups, or
                  None to produce an all-UNKNOWN starting inventory.
    open_mapping_families: families with a known-unresolved v5<->v8 mapping
                  question (e.g. lfoPointModAssignments, midiMap). These are
                  marked explicitly rather than silently lumped into UNKNOWN,
                  and they do not block classification of any other family.
    """
    inventory = {}
    for fam in module_families:
        fc = FamilyCapability(family=fam)
        if fam in open_mapping_families:
            fc.status = MAPPING_DECISION_REQUIRED
            fc.open_mapping_decision = (
                "v5 top-level '%s' has no established v8 semantic mapping; "
                "carried forward as an open decision, not classified unsupported." % fam
            )
        inventory[fam] = fc

    if claim_engine is not None:
        for group in claim_engine.groups.values():
            touched = set()
            for eid in group.supporting_evidence:
                rec = claim_engine.records.get(eid)
                if rec:
                    touched |= _families_touched(rec)
            status = status_from_claim_group(group)
            for fam in touched:
                if fam not in inventory:
                    continue
                fc = inventory[fam]
                if fc.status == MAPPING_DECISION_REQUIRED:
                    continue  # open mapping decisions not silently resolved by unrelated evidence
                if CAPABILITY_ORDER.index(status) > CAPABILITY_ORDER.index(fc.status):
                    fc.status = status
                fc.evidence.extend(e for e in group.supporting_evidence if e not in fc.evidence)
                cdid = group.claim_definition_id
                if cdid not in fc.claim_groups:
                    fc.claim_groups.append(cdid)

    return inventory


def _families_touched(record) -> set:
    """Every module family a record's evidence actually speaks to -- not just
    where the mutation was WRITTEN (ModSlot*), but the destination module it
    NAMES (destModuleTypeString) and any body-level prerequisite family.
    Missing the destination family was a real bug: it credited ModSlot with
    every route test while leaving VoiceFilter/FXRack at UNKNOWN despite being
    the most rigorously causally-verified families in the whole evidence set.
    """
    from .statemodel import module_family
    fams = set()
    for m in record.experiment.get("mutations", []):
        # target_path may be a dotted path ("Env0.plainParams.kParamDecay") --
        # module_family() only strips a trailing digit run, so it must be
        # given the TOP-LEVEL segment first, or a dotted path (no trailing
        # digit) passes through unreduced and never matches any real family.
        fams.add(module_family(m["target_path"].split(".")[0]))
        val = m.get("value")
        if isinstance(val, dict) and "destModuleTypeString" in val:
            fams.add(module_family(val["destModuleTypeString"] + "0"))
    for p in record.experiment.get("prerequisites", []):
        fp = p.get("field_path", "")
        if fp.startswith("body:"):
            fams.add(module_family(fp.split("body:", 1)[1].split(".")[0]))
    for m in record.experiment.get("baseline_overrides", []):
        fams.add(module_family(m["target_path"].split(".")[0]))
    return fams


def _family_from_claim_subject(subject_pattern, supporting_evidence, records):
    """Deprecated single-family accessor, retained for callers needing one
    representative family. Prefer _families_touched for full credit."""
    for eid in supporting_evidence:
        rec = records.get(eid)
        if rec:
            fams = _families_touched(rec)
            if fams:
                return sorted(fams)[0]
    return None


def report(inventory: Dict[str, FamilyCapability]) -> str:
    lines = []
    lines.append("%-22s %-24s %-8s %s" % ("family", "status", "evidence", "open_decision"))
    for fam, fc in sorted(inventory.items()):
        lines.append("%-22s %-24s %-8d %s" % (
            fam, fc.status, len(fc.evidence),
            "YES" if fc.open_mapping_decision else ""))
    counts = {}
    for fc in inventory.values():
        counts[fc.status] = counts.get(fc.status, 0) + 1
    lines.append("")
    lines.append("=== SUMMARY ===")
    for status in CAPABILITY_ORDER:
        if status in counts:
            lines.append("  %-24s %d" % (status, counts[status]))
    lines.append("  %-24s %d" % ("TOTAL", len(inventory)))
    return "\n".join(lines)
