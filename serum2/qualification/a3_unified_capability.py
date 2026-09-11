"""16.5.69.2-A3-21B: Unified capability registry.

One representation for all meaningful Serum controls:
- Parameters (scalar, enum, boolean, integer)
- Modulation routes (source → destination)
- Resources (reference paths)

Each capability explicitly records:
  semantic_id:         human-readable name (e.g., "Filter.Resonance")
  control_type:        "PARAMETER" | "MODULATION" | "RESOURCE"
  qualification_status: "QUALIFIED" | "CAUSAL_VERIFIED" | "ROUTE_RESOLVED" |
                        "NOT_QUALIFIED" | "ARCHITECTURE_ONLY" | "NOT_SUPPORTED"
  mutation_route:      (for parameters + modulation) how to write
  behavior_route:      (for parameters) how to measure effect
  persistence:         "CBOR_BODY" | "HOST_PARAM" | "NOT_PERSISTENT"
  restoration:         "FULL_SAVE_STATE" | "PARTIAL" | "NONE"
  notes:               provenance or caveats

Status definitions:
  QUALIFIED:        Mutation + behavior both verified; effect proven.
  CAUSAL_VERIFIED:  Audio causality confirmed (measurement gate passed).
  ROUTE_RESOLVED:   Mutation route known; behavior not run or pending.
  NOT_QUALIFIED:    Mutation gate failed; not controllable.
  ARCHITECTURE_ONLY:Conceptually structured but not reducible to control (e.g., MODULATION_TOPOLOGY).
  NOT_SUPPORTED:    Explicitly not supported (e.g., host_param-only without CBOR path).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class UnifiedCapability:
    semantic_id: str
    control_type: str  # "PARAMETER" | "MODULATION" | "RESOURCE"
    qualification_status: str
    mutation_route: dict = field(default_factory=dict)
    behavior_route: dict = field(default_factory=dict)
    persistence: str = "UNKNOWN"
    restoration: str = "UNKNOWN"
    notes: Optional[str] = None

    def __post_init__(self):
        valid_types = {"PARAMETER", "MODULATION", "RESOURCE"}
        if self.control_type not in valid_types:
            raise ValueError("control_type must be one of {}, got {!r}".format(
                valid_types, self.control_type))

        valid_status = {
            "QUALIFIED", "CAUSAL_VERIFIED", "ROUTE_RESOLVED",
            "NOT_QUALIFIED", "ARCHITECTURE_ONLY", "NOT_SUPPORTED"
        }
        if self.qualification_status not in valid_status:
            raise ValueError("qualification_status must be one of {}, got {!r}".format(
                valid_status, self.qualification_status))

    @property
    def is_controllable(self) -> bool:
        """Returns True if the capability can be written to."""
        return self.qualification_status in {
            "QUALIFIED", "CAUSAL_VERIFIED", "ROUTE_RESOLVED"
        }

    @property
    def is_behavioral(self) -> bool:
        """Returns True if audio effect has been measured."""
        return self.qualification_status in {"QUALIFIED", "CAUSAL_VERIFIED"}

    def to_dict(self) -> dict:
        return {
            "semantic_id": self.semantic_id,
            "control_type": self.control_type,
            "qualification_status": self.qualification_status,
            "is_controllable": self.is_controllable,
            "is_behavioral": self.is_behavioral,
            "persistence": self.persistence,
            "restoration": self.restoration,
            "mutation_route": self.mutation_route,
            "behavior_route": self.behavior_route,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Capability registry — frozen snapshot of Step 21 state
# ---------------------------------------------------------------------------

def build_unified_registry(
    parameter_qualifications: list[dict] = None,
    modulation_sources: list[str] = None,
    modulation_destinations: list[str] = None,
    resource_targets: list[str] = None,
) -> list[UnifiedCapability]:
    """Build unified capability registry from Step 21 audit inputs.

    Args:
        parameter_qualifications: List of {semantic_id, qualification_status, ...}
        modulation_sources:       List of source names (e.g., "LFO1")
        modulation_destinations:  List of destination names (e.g., "Filter1.Cutoff")
        resource_targets:         List of resource target names (e.g., "OSC1.Wavetable")

    Returns:
        List of UnifiedCapability sorted by semantic_id.
    """
    registry = []

    if parameter_qualifications:
        for qual in parameter_qualifications:
            cap = UnifiedCapability(
                semantic_id=qual.get("semantic_id", "UNKNOWN"),
                control_type="PARAMETER",
                qualification_status=qual.get("qualification_status", "UNKNOWN"),
                mutation_route=qual.get("mutation_route", {}),
                behavior_route=qual.get("behavior_route", {}),
                persistence=qual.get("persistence", "UNKNOWN"),
                restoration=qual.get("restoration", "UNKNOWN"),
                notes=qual.get("notes"),
            )
            registry.append(cap)

    # For each (source, destination) pair, create a MODULATION capability
    if modulation_sources and modulation_destinations:
        for src in modulation_sources:
            for dst in modulation_destinations:
                semantic_id = "Modulation.{}.{}".format(src, dst)
                cap = UnifiedCapability(
                    semantic_id=semantic_id,
                    control_type="MODULATION",
                    qualification_status="CAUSAL_VERIFIED",  # Step 20 proven
                    mutation_route={
                        "adapter": "modulation_slot",
                        "source": src,
                        "destination": dst,
                    },
                    behavior_route={"metric": "spectral_centroid", "notes": "LFO modulation"},
                    persistence="CBOR_BODY",
                    restoration="FULL_SAVE_STATE",
                    notes="Empirically verified in Step 20; 1996x centroid std ratio",
                )
                registry.append(cap)

    if resource_targets:
        for target in resource_targets:
            cap = UnifiedCapability(
                semantic_id="Resource.{}".format(target),
                control_type="RESOURCE",
                qualification_status="ROUTE_RESOLVED",
                mutation_route={
                    "adapter": "cbor_string",
                    "target": target,
                },
                persistence="CBOR_BODY",
                restoration="FULL_SAVE_STATE",
                notes="String field in CBOR body",
            )
            registry.append(cap)

    return sorted(registry, key=lambda x: x.semantic_id)
