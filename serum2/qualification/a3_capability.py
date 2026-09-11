"""16.5.69.2-A3-18: ControlCapability registry.

A ControlCapability binds a semantic identity to its explicit mutation_route
and behavior_route. This makes the route disconnect an architectural concept
rather than a hidden special case.

Qualification status values:
  QUALIFIED           - behavior route verified CAUSAL_VERIFIED (Steps 14-17)
  ROUTE_RESOLVED      - mutation and behavior routes empirically confirmed,
                        behavior test not yet run under the new pipeline
  NOT_QUALIFIED       - routes defined but behavior not yet tested
  ARCHITECTURE_ONLY   - adapter boundary defined; no pipeline execution yet
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from serum2.qualification.a3_route import MutationRoute, BehaviorRoute


@dataclass(frozen=True)
class ControlCapability:
    semantic_id: str
    mutation_class: str
    mutation_route: MutationRoute
    behavior_route: BehaviorRoute
    qualification_status: str
    notes: Optional[str] = None

    def __post_init__(self):
        valid_classes = {
            "SCALAR", "ENUM", "BOOLEAN", "INTEGER",
            "REFERENCE", "ARRAY_OBJECT", "MODULATION_TOPOLOGY",
        }
        if self.mutation_class not in valid_classes:
            raise ValueError("Unknown mutation_class: {!r}".format(self.mutation_class))
        valid_status = {
            "QUALIFIED", "ROUTE_RESOLVED", "NOT_QUALIFIED", "ARCHITECTURE_ONLY",
        }
        if self.qualification_status not in valid_status:
            raise ValueError("Unknown status: {!r}".format(self.qualification_status))

    @property
    def is_qualified(self) -> bool:
        return self.qualification_status == "QUALIFIED"

    @property
    def can_run_behavior(self) -> bool:
        return (
            self.qualification_status in {"QUALIFIED", "ROUTE_RESOLVED", "NOT_QUALIFIED"}
            and self.behavior_route.is_observable
        )


# ---------------------------------------------------------------------------
# H1 targets — already CAUSAL_VERIFIED in Steps 14-17
# ---------------------------------------------------------------------------

FILTER_RESONANCE = ControlCapability(
    semantic_id="Filter.Resonance",
    mutation_class="SCALAR",
    mutation_route=MutationRoute(
        adapter="cbor_body",
        path="VoiceFilter0.plainParams.kParamResonance",
        notes="VoiceFilter0.plainParams maps directly to Filter 1 host params",
    ),
    behavior_route=BehaviorRoute(
        metric="overall_rms_db",
        exercise_context=(
            ("Filter 1 On", 1.0),
            ("Filter 1 Freq", 0.15),
        ),
        effect_threshold=0.5,
        notes="Low cutoff makes resonance peak audible; +2.74 dB confirmed",
    ),
    qualification_status="QUALIFIED",
    notes="Step 17 result: CAUSAL_VERIFIED, delta=+2.74 dB",
)

FILTER_TYPE = ControlCapability(
    semantic_id="Filter.Type",
    mutation_class="ENUM",
    mutation_route=MutationRoute(
        adapter="cbor_body",
        path="VoiceFilter0.plainParams.kParamType",
        notes="VoiceFilter0.plainParams maps directly to Filter 1 host params",
    ),
    behavior_route=BehaviorRoute(
        metric="spectral_centroid_hz",
        exercise_context=(
            ("Filter 1 On", 1.0),
            ("Filter 1 Freq", 0.35),
        ),
        effect_threshold=200.0,
        notes="LP vs BP shifts centroid; +349 Hz confirmed",
    ),
    qualification_status="QUALIFIED",
    notes="Step 17 result: CAUSAL_VERIFIED, delta=+349 Hz",
)

OSC1_ENABLE = ControlCapability(
    semantic_id="OSC1.Enable",
    mutation_class="BOOLEAN",
    mutation_route=MutationRoute(
        adapter="cbor_body",
        path="VoicePanel0.plainParams.kParamEnableOsc1",
        notes=(
            "CBOR path confirmed writable (generation=PASS). "
            "VoiceOsc0.plainParams.kParamEnable does NOT map to 'A Enable' host param; "
            "behavior is tested via arm-specific host context."
        ),
    ),
    behavior_route=BehaviorRoute(
        metric="overall_rms_db",
        baseline_host_context=(("A Enable", 0.0),),
        mutated_host_context=(("A Enable", 1.0),),
        effect_threshold=3.0,
        notes="Arm-specific host context; mutation_route != behavior_route (CBOR/host disconnect)",
    ),
    qualification_status="QUALIFIED",
    notes="Step 17 result: CAUSAL_VERIFIED, delta=+99.95 dB",
)


# ---------------------------------------------------------------------------
# Step 18 new targets — routes empirically resolved
# ---------------------------------------------------------------------------

OSC1_UNISON = ControlCapability(
    semantic_id="OSC1.Unison",
    mutation_class="INTEGER",
    mutation_route=MutationRoute(
        adapter="host_param",
        host_param="A Unison",
        notes=(
            "No CBOR body path exists for unison count. "
            "isDiscrete=True, numSteps=16, range 1-16 voices. "
            "Host-param-only route confirmed: resaved body has no unison field."
        ),
    ),
    behavior_route=BehaviorRoute(
        metric="overall_rms_db",
        baseline_host_context=(("A Unison", 0.0),),
        mutated_host_context=(("A Unison", 0.9),),
        effect_threshold=0.5,
        notes="1 voice vs ~14 voices; +0.97 dB RMS confirmed",
    ),
    qualification_status="ROUTE_RESOLVED",
    notes="Empirically verified: no CBOR path, host-param route only",
)

ENV1_ATTACK = ControlCapability(
    semantic_id="Env1.Attack",
    mutation_class="SCALAR",
    mutation_route=MutationRoute(
        adapter="cbor_body",
        path="Env1.plainParams.kParamAttack",
        notes=(
            "Env1.plainParams.kParamAttack -> 'Env 2 Attack' host param confirmed. "
            "Env0->Env1, Env1->Env2 indexing verified empirically."
        ),
    ),
    behavior_route=BehaviorRoute(
        metric="overall_rms_db",
        notes=(
            "Envelope attack time affects amplitude shape. "
            "Behavior route uses same cbor_body path; host param confirms mapping."
        ),
    ),
    qualification_status="ROUTE_RESOLVED",
    notes="CBOR->host mapping confirmed; behavior test not yet run under generic pipeline",
)

OSC1_WAVETABLE = ControlCapability(
    semantic_id="OSC1.Wavetable",
    mutation_class="REFERENCE",
    mutation_route=MutationRoute(
        adapter="cbor_string",
        path="Oscillator0.WTOsc0.relativePathToWT",
        notes=(
            "String field in CBOR body. Mutation changes path to a different .wav file. "
            "Persistence confirmed: resaved body retains new path. "
            "File must exist on disk (Serum logs warning but loads)."
        ),
    ),
    behavior_route=BehaviorRoute(
        metric="spectral_centroid_hz",
        effect_threshold=100.0,
        notes="Different wavetable shapes produce different spectral content",
    ),
    qualification_status="ROUTE_RESOLVED",
    notes=(
        "Default Shapes vs 808 Harms: -1129 Hz centroid delta confirmed. "
        "Represents REFERENCE/RESOURCE mutation class."
    ),
)

MODULATION_SLOT = ControlCapability(
    semantic_id="Modulation.Slot0",
    mutation_class="MODULATION_TOPOLOGY",
    mutation_route=MutationRoute(
        adapter="NOT_SUPPORTED",
        notes=(
            "ModSlot0-63 have plainParams with source/target/amount fields. "
            "Routing topology requires a dedicated adapter that understands "
            "source identity, target identity, and amount simultaneously. "
            "Cannot be expressed as a single scalar mutation."
        ),
    ),
    behavior_route=BehaviorRoute(
        metric="NOT_OBSERVABLE",
        notes="Topology capability requires dedicated qualification path, not generic pipeline",
    ),
    qualification_status="ARCHITECTURE_ONLY",
    notes=(
        "Adapter boundary defined. Modulation topology is NOT reducible to the "
        "scalar/enum/boolean/integer/reference pipeline. Dedicated Step N required."
    ),
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_CAPABILITIES: dict[str, ControlCapability] = {
    cap.semantic_id: cap
    for cap in [
        FILTER_RESONANCE,
        FILTER_TYPE,
        OSC1_ENABLE,
        OSC1_UNISON,
        ENV1_ATTACK,
        OSC1_WAVETABLE,
        MODULATION_SLOT,
    ]
}


def get_capability(semantic_id: str) -> ControlCapability:
    if semantic_id not in ALL_CAPABILITIES:
        raise KeyError("Unknown semantic_id: {!r}".format(semantic_id))
    return ALL_CAPABILITIES[semantic_id]
