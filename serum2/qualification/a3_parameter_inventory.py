"""16.5.69.2-A3-19A: Full Serum 2 parameter inventory.

Enumerates the complete 2,623-parameter VST3 surface and assigns:
  - mutation_class (SCALAR/INTEGER/BOOLEAN/MIDI_PASSTHROUGH)
  - mutation_route (host_param for all; cbor_body for known-mapped ones)
  - semantic_id (verified for known targets; UNMAPPED for the rest)
  - controllability classification

Classification:
  AUTOMATABLE_SYNTHESIS: indices 0-540 (Serum synthesis/FX controls)
  MIDI_PASSTHROUGH: indices 541+ (Pitch Bend Chan N, CC0-127 Chan N)

Semantic ID policy:
  Only assign meaningful semantic_id to parameters with proven route resolution
  (established in Steps 14-18). All others get semantic_id="UNMAPPED".
  Fabricated semantic IDs are explicitly prohibited.

Mutation class assignment:
  numSteps == 2              -> BOOLEAN
  3 <= numSteps <= 128       -> INTEGER  (discrete with audible steps)
  numSteps > 128 (or None)   -> SCALAR   (continuous)
  non-automatable            -> MIDI_PASSTHROUGH
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from serum2.qualification.a3_route import MutationRoute, BehaviorRoute


# ---------------------------------------------------------------------------
# Semantic IDs with proven route resolution (Steps 14-18)
# ---------------------------------------------------------------------------

# Maps vst3_name -> (semantic_id, mutation_route)
_KNOWN_ROUTES: dict[str, tuple[str, MutationRoute]] = {
    "Filter 1 Res": (
        "Filter.Resonance",
        MutationRoute(
            adapter="cbor_body",
            path="VoiceFilter0.plainParams.kParamResonance",
        ),
    ),
    "Filter 1 Type": (
        "Filter.Type",
        MutationRoute(
            adapter="cbor_body",
            path="VoiceFilter0.plainParams.kParamType",
        ),
    ),
    # OSC1.Enable: VoicePanel0 is the proven cbor_body path; A Enable is the behavior route host
    # The VoicePanel0 path is what generation gate tests; A Enable is behavior arm context
    "A Enable": (
        "OSC1.Enable",
        MutationRoute(
            adapter="cbor_body",
            path="VoicePanel0.plainParams.kParamEnableOsc1",
            notes="CBOR path proven writable; behavior tested via A Enable host param arm contexts",
        ),
    ),
    "A Unison": (
        "OSC1.Unison",
        MutationRoute(
            adapter="host_param",
            host_param="A Unison",
            notes="No CBOR body path; host_param-only route confirmed",
        ),
    ),
    "Env 2 Attack": (
        "Env1.Attack",
        MutationRoute(
            adapter="cbor_body",
            path="Env1.plainParams.kParamAttack",
            notes="Env1.plainParams.kParamAttack -> Env 2 Attack host param confirmed",
        ),
    ),
}


# ---------------------------------------------------------------------------
# ParameterEntry
# ---------------------------------------------------------------------------

@dataclass
class ParameterEntry:
    vst3_index: int
    vst3_name: str
    num_steps: int
    is_discrete: bool
    is_automatable: bool
    default_value: float
    mutation_class: str
    mutation_route: MutationRoute
    semantic_id: str
    controllability: str


def _classify_mutation_class(p: dict) -> str:
    """Derive mutation class from VST3 parameter metadata."""
    if not p.get("isAutomatable", True):
        return "MIDI_PASSTHROUGH"
    num_steps = p.get("numSteps", 2147483647)
    if num_steps == 2:
        return "BOOLEAN"
    if 3 <= num_steps <= 128:
        return "INTEGER"
    return "SCALAR"


def _make_mutation_route(p: dict) -> MutationRoute:
    """Assign mutation route. Known CBOR-mapped params get cbor_body; all others host_param."""
    name = p["name"]
    if name in _KNOWN_ROUTES:
        _, route = _KNOWN_ROUTES[name]
        return route
    if not p.get("isAutomatable", True):
        return MutationRoute(
            adapter="NOT_SUPPORTED",
            notes="MIDI passthrough parameter; not a synthesis control",
        )
    return MutationRoute(adapter="host_param", host_param=name)


def _make_semantic_id(p: dict) -> str:
    """Assign semantic_id. Only proven-mapped params get a meaningful name."""
    name = p["name"]
    if name in _KNOWN_ROUTES:
        semantic_id, _ = _KNOWN_ROUTES[name]
        return semantic_id
    return "UNMAPPED"


def _make_controllability(p: dict) -> str:
    if not p.get("isAutomatable", True):
        return "MIDI_PASSTHROUGH"
    name = p["name"]
    if name in _KNOWN_ROUTES:
        _, route = _KNOWN_ROUTES[name]
        if route.adapter == "cbor_body":
            return "CBOR_AND_HOST"
        return "HOST_PARAM_ONLY"
    return "HOST_PARAM_ONLY"


def build_inventory(params: list[dict]) -> list[ParameterEntry]:
    """Build the full ParameterEntry list from raw DawDreamer parameter descriptions."""
    entries = []
    for p in params:
        mutation_class = _classify_mutation_class(p)
        mutation_route = _make_mutation_route(p)
        semantic_id = _make_semantic_id(p)
        controllability = _make_controllability(p)
        entries.append(ParameterEntry(
            vst3_index=p["index"],
            vst3_name=p["name"],
            num_steps=p.get("numSteps", 2147483647),
            is_discrete=p.get("isDiscrete", False),
            is_automatable=p.get("isAutomatable", True),
            default_value=p.get("defaultValue", 0.0),
            mutation_class=mutation_class,
            mutation_route=mutation_route,
            semantic_id=semantic_id,
            controllability=controllability,
        ))
    return entries


# ---------------------------------------------------------------------------
# Summary helpers
# ---------------------------------------------------------------------------

def summarize_inventory(entries: list[ParameterEntry]) -> dict:
    total = len(entries)
    automatable = [e for e in entries if e.is_automatable]
    midi_passthrough = [e for e in entries if not e.is_automatable]
    known_semantic = [e for e in entries if e.semantic_id != "UNMAPPED"]
    cbor_and_host = [e for e in entries if e.controllability == "CBOR_AND_HOST"]
    host_only = [e for e in entries if e.controllability == "HOST_PARAM_ONLY"]
    by_class: dict[str, int] = {}
    for e in entries:
        by_class[e.mutation_class] = by_class.get(e.mutation_class, 0) + 1
    return {
        "total_vst3_parameters": total,
        "automatable_synthesis": len(automatable),
        "midi_passthrough": len(midi_passthrough),
        "semantically_identified": len(known_semantic),
        "unmapped_semantic": total - len(known_semantic),
        "cbor_and_host_controllable": len(cbor_and_host),
        "host_param_only_controllable": len(host_only),
        "mutation_class_distribution": by_class,
    }
