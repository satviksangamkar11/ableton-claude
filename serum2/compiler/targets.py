"""16.5.4: Semantic target resolution.

SemanticTargetRef is a dumb alias only: name -> capability_key.
No structural knowledge, no RequiredContext, no admission decision.

RequiredContext derivation is entirely delegated to context.py via
extract_required_context(). This module does not reimplement it.

Resolution chain:
  "FXEQ.Freq1"
    -> SemanticTargetRef   (SEMANTIC_TARGETS lookup)
    -> CapabilityContract  (contracts lookup by c.target == capability_key)
    -> RequiredContext      (context.extract_required_context on contract's path)
    -> concrete path       (RequiredContext.resolve_index(body))

SEMANTIC_TARGETS carries no index knowledge. An index here would be a layering
violation: list positions are body-state details, never vocabulary.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from . import context as ctx_mod

CONTEXT_NOT_SATISFIED = "CONTEXT_NOT_SATISFIED"
UNKNOWN_SEMANTIC_TARGET = "UNKNOWN_SEMANTIC_TARGET"
CAPABILITY_NOT_FOUND = "CAPABILITY_NOT_FOUND"


@dataclass(frozen=True)
class SemanticTargetRef:
    name: str
    capability_key: str


@dataclass(frozen=True)
class ResolvedTarget:
    ref: SemanticTargetRef
    contract: Any  # CapabilityContract -- Any avoids a circular import


@dataclass(frozen=True)
class TargetRefusal:
    reason: str
    detail: str


# Vocabulary only. No index, no path, no structural knowledge.
SEMANTIC_TARGETS: Dict[str, SemanticTargetRef] = {
    "FXEQ.Freq1":        SemanticTargetRef("FXEQ.Freq1",        "fx_field_eq_freq1"),
    "FXEQ.Freq2":        SemanticTargetRef("FXEQ.Freq2",        "fx_field_eq_freq2"),
    "FXEQ.Reso1":        SemanticTargetRef("FXEQ.Reso1",        "fx_field_eq_reso1"),
    "FXEQ.Reso2":        SemanticTargetRef("FXEQ.Reso2",        "fx_field_eq_reso2"),
    "FXEQ.Gain1":        SemanticTargetRef("FXEQ.Gain1",        "fx_field_eq_gain1"),
    "FXEQ.Gain2":        SemanticTargetRef("FXEQ.Gain2",        "fx_field_eq_gain2"),
    "FXEQ.LevelOut":     SemanticTargetRef("FXEQ.LevelOut",     "fx_field_eq_level_out"),
    "FXDistortion.Drive": SemanticTargetRef("FXDistortion.Drive", "fx_field_dist_drive"),
    # Oscillator
    "OSC1.Volume":        SemanticTargetRef("OSC1.Volume",        "oscillator_field_OSC-VOLUME"),
    "OSC1.Octave":        SemanticTargetRef("OSC1.Octave",        "oscillator_field_OSC-OCTAVE"),
    # Envelope
    "Env1.Decay":         SemanticTargetRef("Env1.Decay",         "envelope_field_decay"),
    "Env1.Release":       SemanticTargetRef("Env1.Release",       "envelope_field_release"),
    "Env1.Sustain":       SemanticTargetRef("Env1.Sustain",       "envelope_field_sustain"),
    # Global
    "Global.MasterVolume": SemanticTargetRef("Global.MasterVolume", "global_field_mastervolume"),
}


def resolve_semantic_target(
    name: str,
    contracts: Dict[Tuple[str, str], Any],
) -> "ResolvedTarget | TargetRefusal":
    """Resolve a semantic name to a (ref, contract) pair.

    Does NOT grant admission. Does NOT check whether the contract is usable.
    The caller is responsible for running admission.admit() independently.

    Invariants:
    - Returns TargetRefusal if the name is not in SEMANTIC_TARGETS
    - Returns TargetRefusal if no contract exists for the capability_key
    - Prefers CAUSAL_VERIFIED contract when multiple exist for the same key
    - Never contains a literal list index
    """
    ref = SEMANTIC_TARGETS.get(name)
    if ref is None:
        return TargetRefusal(
            UNKNOWN_SEMANTIC_TARGET,
            "no semantic target named %r -- not in SEMANTIC_TARGETS vocabulary" % name,
        )
    matches = [c for c in contracts.values() if c.target == ref.capability_key]
    if not matches:
        return TargetRefusal(
            CAPABILITY_NOT_FOUND,
            "no CapabilityContract for capability_key %r -- "
            "no evidence has been collected for this target" % ref.capability_key,
        )
    # Preference only -- admission still required before any execution.
    from ..evidence.capability_contract import CAUSAL_VERIFIED
    contract = next((c for c in matches if c.status == CAUSAL_VERIFIED), matches[0])
    return ResolvedTarget(ref=ref, contract=contract)


def resolve_path(resolved_target: ResolvedTarget, body: Dict[str, Any]) -> Optional[str]:
    """Resolve the concrete mutation path for this target in the given body.

    Uses context.extract_required_context() -- the sole RequiredContext
    derivation mechanism -- to find where the target lives in body regardless
    of which list index the witness experiment happened to use.

    Returns:
        str   -- concrete path where the target lives in body
        None  -- body does not satisfy the required structural context
                 (e.g. no FXEQ element in FXRack0.FX)
    """
    mutation_path = resolved_target.contract.scope.get("mutation_target_path")
    if mutation_path is None:
        return None
    ctx = ctx_mod.extract_required_context(mutation_path)
    if ctx is None:
        # No list traversal required -- path addresses a dict field directly.
        return mutation_path
    if not ctx.satisfied_by(body):
        return None
    return ctx.resolve_path(mutation_path, body)
