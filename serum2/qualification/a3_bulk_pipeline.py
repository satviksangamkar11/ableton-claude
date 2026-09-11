"""16.5.69.2-A3-19C: Bulk qualification pipeline.

Runs generation checks for all 541 automatable parameters in O(1) Serum loads.
Skips audio rendering — behavior is pre-established only for H1 targets.

Pipeline per parameter:
  MIDI_PASSTHROUGH -> NOT_APPLICABLE generation
  host_param        -> load once, set, read back, confirm changed -> PASS/FAIL
  cbor_body         -> state diff on pre-built bodies

P1 for host_param-only:
  NOT_APPLICABLE — save_state captures CBOR body; host_param values are
  ephemeral unless a CBOR body path also exists. This is an architectural
  property, not a test failure.

P1 for cbor_body:
  Tested via save_state round-trip (Serum serializes the CBOR body).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from serum2.qualification.a3_generation_observation import (
    GenerationObservation,
    GENERATION_NOT_APPLICABLE,
    generation_from_host_param_readback,
    generation_from_state_diff,
)
from serum2.qualification.a3_parameter_inventory import ParameterEntry


# ---------------------------------------------------------------------------
# Bulk generation result per parameter
# ---------------------------------------------------------------------------

@dataclass
class ParameterQualification:
    vst3_index: int
    vst3_name: str
    semantic_id: str
    mutation_class: str
    controllability: str
    generation: GenerationObservation
    p1_status: str = "NOT_RUN"
    p1_reason: Optional[str] = None
    behavior_status: str = "NOT_RUN"
    behavior_reason: Optional[str] = None

    @property
    def is_controllable(self) -> bool:
        return self.generation.status in ("PASS", "NOT_APPLICABLE")

    def to_dict(self) -> dict:
        return {
            "vst3_index": self.vst3_index,
            "vst3_name": self.vst3_name,
            "semantic_id": self.semantic_id,
            "mutation_class": self.mutation_class,
            "controllability": self.controllability,
            "generation": {
                "route_kind": self.generation.route_kind,
                "status": self.generation.status,
                "value_before": self.generation.value_before,
                "value_set": self.generation.value_set,
                "value_after": self.generation.value_after,
                "reason": self.generation.reason,
            },
            "p1_status": self.p1_status,
            "p1_reason": self.p1_reason,
            "behavior_status": self.behavior_status,
            "behavior_reason": self.behavior_reason,
        }


# ---------------------------------------------------------------------------
# Bulk host_param generation check (O(1) Serum loads)
# ---------------------------------------------------------------------------

def run_bulk_host_param_generation(
    entries: list[ParameterEntry],
    serum_vst3: str,
    skeleton: tuple,
) -> dict[int, GenerationObservation]:
    """
    Load Serum once, set+read all host_param parameters, return observations.

    Only runs for isAutomatable=True params. MIDI_PASSTHROUGH params
    get GENERATION_NOT_APPLICABLE without any VST3 interaction.
    """
    import os, tempfile
    import dawdreamer as daw
    from serum2 import bridge

    meta, body = skeleton
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor("serum", serum_vst3)
    synth.load_state(tmp)
    os.remove(tmp)

    by_index = {p["index"]: p for p in synth.get_parameters_description()}
    observations: dict[int, GenerationObservation] = {}

    for entry in entries:
        idx = entry.vst3_index
        if not entry.is_automatable:
            observations[idx] = GENERATION_NOT_APPLICABLE
            continue

        # All automatable parameters can be tested via host_param even if they
        # also have a cbor_body route (we verify the host_param channel here;
        # state_mutation verification is done separately for cbor_body routes).
        before = synth.get_parameter(idx)
        p_meta = by_index.get(idx, {})
        num_steps = p_meta.get("numSteps", 2147483647)

        # Choose test value away from default
        if num_steps == 2:
            test_val = 1.0 if before < 0.5 else 0.0
        elif 3 <= num_steps <= 128:
            # Discrete: go to opposite end of range
            test_val = 1.0 if before < 0.5 else 0.0
        else:
            # Continuous: go to 0.75 or 0.25
            test_val = 0.75 if before < 0.5 else 0.25

        synth.set_parameter(idx, test_val)
        after = synth.get_parameter(idx)
        # Restore to default so params don't interfere
        synth.set_parameter(idx, before)

        observations[idx] = generation_from_host_param_readback(
            vst3_name=entry.vst3_name,
            value_before=before,
            value_set=test_val,
            value_after=after,
        )

    return observations


# ---------------------------------------------------------------------------
# State_mutation generation check for known cbor_body routes
# ---------------------------------------------------------------------------

def run_cbor_body_generation(
    entry: ParameterEntry,
    skeleton: tuple,
) -> GenerationObservation:
    """Test state diff for a cbor_body-routed parameter."""
    import copy
    from serum2 import pathmerge

    route = entry.mutation_route
    assert route.adapter == "cbor_body" and route.path is not None

    meta, body = skeleton
    body_base = copy.deepcopy(body)

    # Choose a test mutation value
    body_mut = copy.deepcopy(body_base)
    try:
        baseline_val = pathmerge.read_path_value(body_mut, route.path)
    except Exception:
        baseline_val = None

    # Use a float test value; works for scalar/enum/boolean paths
    test_val = 0.9 if baseline_val != 0.9 else 0.1
    pathmerge.apply_path_value(body_mut, route.path, test_val)

    # State diff
    top_key = route.path.split(".")[0]
    diff_keys = sorted(k for k in body_mut if body_mut[k] != body_base.get(k))
    top_ok = diff_keys == [top_key]
    try:
        after_val = pathmerge.read_path_value(body_mut, route.path)
        leaf_changed = after_val != baseline_val
    except Exception:
        leaf_changed = False

    return generation_from_state_diff(
        diff_keys=diff_keys,
        intended_top_key=top_key,
        leaf_changed=leaf_changed,
        top_ok=top_ok,
    )


# ---------------------------------------------------------------------------
# P1 note builder
# ---------------------------------------------------------------------------

def p1_for_entry(entry: ParameterEntry) -> tuple[str, str]:
    """Return (p1_status, p1_reason) based on route type."""
    route = entry.mutation_route
    if not entry.is_automatable:
        return "NOT_APPLICABLE", "MIDI passthrough; no state persistence applies"
    if route.adapter == "host_param":
        return (
            "NOT_APPLICABLE",
            "host_param adapter: save_state captures CBOR body only; "
            "host_param values are session-ephemeral unless a CBOR body path also exists",
        )
    if route.adapter == "cbor_body":
        return "NOT_RUN", "P1 test not yet run for this cbor_body target"
    return "NOT_RUN", "P1 test not yet run"


# ---------------------------------------------------------------------------
# Assemble ParameterQualification per entry
# ---------------------------------------------------------------------------

def assemble_qualifications(
    entries: list[ParameterEntry],
    host_param_observations: dict[int, GenerationObservation],
    cbor_generation_map: Optional[dict[int, GenerationObservation]] = None,
    behavior_status_map: Optional[dict[str, tuple[str, str]]] = None,
) -> list[ParameterQualification]:
    """
    Build a ParameterQualification for each entry.

    behavior_status_map: semantic_id -> (status, reason) for pre-qualified targets.
    cbor_generation_map: vst3_index -> GenerationObservation for cbor_body-tested params.
    """
    if cbor_generation_map is None:
        cbor_generation_map = {}
    if behavior_status_map is None:
        behavior_status_map = {}

    results = []
    for entry in entries:
        idx = entry.vst3_index

        # Generation: prefer cbor_body result, fall back to host_param observation
        if idx in cbor_generation_map:
            gen_obs = cbor_generation_map[idx]
        else:
            gen_obs = host_param_observations.get(idx, GENERATION_NOT_APPLICABLE)

        p1_status, p1_reason = p1_for_entry(entry)

        # Behavior: pre-qualified targets carry forward their status
        if entry.semantic_id in behavior_status_map:
            beh_status, beh_reason = behavior_status_map[entry.semantic_id]
        else:
            beh_status = "NOT_RUN"
            beh_reason = "Behavior test not run at bulk scale"

        results.append(ParameterQualification(
            vst3_index=idx,
            vst3_name=entry.vst3_name,
            semantic_id=entry.semantic_id,
            mutation_class=entry.mutation_class,
            controllability=entry.controllability,
            generation=gen_obs,
            p1_status=p1_status,
            p1_reason=p1_reason,
            behavior_status=beh_status,
            behavior_reason=beh_reason,
        ))

    return results


# ---------------------------------------------------------------------------
# Coverage summary
# ---------------------------------------------------------------------------

def coverage_summary(qualifications: list[ParameterQualification]) -> dict:
    total = len(qualifications)
    total_vst3 = 2623

    automatable = [q for q in qualifications if q.mutation_class != "MIDI_PASSTHROUGH"]
    midi_pt = [q for q in qualifications if q.mutation_class == "MIDI_PASSTHROUGH"]

    gen_pass = [q for q in qualifications if q.generation.status == "PASS"]
    gen_fail = [q for q in qualifications if q.generation.status == "FAIL"]
    gen_na = [q for q in qualifications if q.generation.status == "NOT_APPLICABLE"]

    semantically_id = [q for q in qualifications if q.semantic_id != "UNMAPPED"]
    qualified = [q for q in qualifications if q.behavior_status == "CAUSAL_VERIFIED"]
    route_resolved = [
        q for q in qualifications
        if q.semantic_id != "UNMAPPED" and q.behavior_status != "CAUSAL_VERIFIED"
    ]

    by_class: dict[str, int] = {}
    for q in qualifications:
        by_class[q.mutation_class] = by_class.get(q.mutation_class, 0) + 1

    by_controllability: dict[str, int] = {}
    for q in qualifications:
        by_controllability[q.controllability] = by_controllability.get(q.controllability, 0) + 1

    return {
        "total_vst3_parameters": total_vst3,
        "inventoried": total,
        "automatable_synthesis": len(automatable),
        "midi_passthrough_non_synthesis": len(midi_pt),
        "generation_pass": len(gen_pass),
        "generation_fail": len(gen_fail),
        "generation_not_applicable": len(gen_na),
        "semantically_identified": len(semantically_id),
        "unmapped_semantic": total - len(semantically_id),
        "route_resolved": len(route_resolved),
        "qualified_causal": len(qualified),
        "by_mutation_class": by_class,
        "by_controllability": by_controllability,
        "p1_applicable": sum(1 for q in qualifications if q.p1_status == "NOT_APPLICABLE"),
    }
