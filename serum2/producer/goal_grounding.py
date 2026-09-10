"""16.5.61: Goal Grounding — compare goal to world state.

Takes GoalModel + WorldModel → identifies gaps, contradictions, satisfactions.

Gap types:

  SATISFIED
    The goal's characteristic is already met in the world state.
    Example: goal requires "dark" and measured_characteristics.brightness is low.

  MISSING
    The goal requires a characteristic, but the world state has no evidence for it.
    Planner should find a capability that provides it.
    Example: goal requires "punchy" but attack_speed is not measured.

  CONTRADICTORY
    The goal's characteristic conflicts with current state.
    Example: goal requires "bright" but brightness is currently low.
    May require reversal of a prior change.

  CONSTRAINED
    The goal requires a characteristic, but available capabilities are blocked
    by prerequisites or limitations.
    Example: goal requires "longer sustain" but "no MCP mapping for Env1.Sustain"
    is in unresolved_limitations.

  UNGROUNDED
    The goal requires a characteristic, but evidence provides no capability.
    This is a discovery request.
    Example: goal requires "subtle warble" but no capability maps to that.
"""
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from enum import Enum

from .goal_model import GoalModel, Character, Energy, Register, Density, AttackProfile, SustainLength, Spread
from .world_model import WorldModel, RoleState


class GapType(str, Enum):
    SATISFIED = "satisfied"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"
    CONSTRAINED = "constrained"
    UNGROUNDED = "ungrounded"


@dataclass(frozen=True)
class CharacteristicGap:
    """One gap identified by goal grounding.

    characteristic_name: e.g., "attack", "brightness"
    goal_value: what the goal requires (e.g., "punchy")
    current_value: what the world state shows (e.g., None or "slow")
    gap_type: SATISFIED | MISSING | CONTRADICTORY | CONSTRAINED | UNGROUNDED
    detail: human-readable explanation
    possible_capabilities: list of semantic targets that *might* address this gap
                          (caller must verify against evidence system)
    """
    characteristic_name: str
    goal_value: Any
    current_value: Optional[Any]
    gap_type: GapType
    detail: str
    possible_capabilities: List[str] = None


@dataclass(frozen=True)
class GoalGroundingResult:
    """Complete analysis of goal vs. world state.

    goal: the structured goal
    role_state: the role state (if the role exists; None otherwise)
    all_gaps: all CharacteristicGaps identified
    satisfied: gaps where goal is already met
    missing: gaps where goal is needed but not measured
    contradictory: gaps where goal conflicts with current state
    constrained: gaps where evidence exists but prerequisites block execution
    ungrounded: gaps where evidence does not provide a capability

    has_blocking_gap: True if any gap type prevents execution (contradictory, constrained, ungrounded)
    recommended_next_step: human-readable suggestion for the Planner
    """
    goal: GoalModel
    role_state: Optional[RoleState]
    all_gaps: List[CharacteristicGap]
    satisfied: List[CharacteristicGap]
    missing: List[CharacteristicGap]
    contradictory: List[CharacteristicGap]
    constrained: List[CharacteristicGap]
    ungrounded: List[CharacteristicGap]

    @property
    def has_blocking_gap(self) -> bool:
        """True if any gap prevents execution."""
        return bool(self.contradictory or self.constrained or self.ungrounded)

    @property
    def requires_discovery(self) -> bool:
        """True if ungrounded gaps require new evidence."""
        return bool(self.ungrounded)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal.to_dict(),
            "role_exists": self.role_state is not None,
            "satisfied": len(self.satisfied),
            "missing": len(self.missing),
            "contradictory": len(self.contradictory),
            "constrained": len(self.constrained),
            "ungrounded": len(self.ungrounded),
            "has_blocking_gap": self.has_blocking_gap,
            "requires_discovery": self.requires_discovery,
            "gaps": [
                {
                    "characteristic": g.characteristic_name,
                    "goal_value": str(g.goal_value),
                    "current_value": str(g.current_value) if g.current_value else None,
                    "type": g.gap_type.value,
                    "detail": g.detail,
                    "possible_capabilities": g.possible_capabilities or [],
                }
                for g in self.all_gaps
            ],
        }


def ground_goal(goal: GoalModel, world: WorldModel) -> GoalGroundingResult:
    """Analyze a goal against the current world state.

    Returns GoalGroundingResult with all gaps identified.

    Gap analysis per characteristic dimension:
      1. Does the goal constrain this dimension?
      2. Does the role state have a measured value?
      3. If yes: is it satisfied, contradictory?
      4. If no: is there a known capability, or is it missing/ungrounded?
    """
    # Verify role exists
    role_state = world.get_role_in_section(goal.role, goal.section_name)
    if role_state is None and goal.section_name:
        # Role doesn't exist in this section; try without section check
        role_state = world.get_role(goal.role)

    all_gaps = []

    # ---- Analyze character constraints ----
    if goal.characteristics.character:
        for char in goal.characteristics.character:
            gap = _analyze_character_gap(char, role_state)
            all_gaps.append(gap)

    # ---- Analyze energy ----
    if goal.characteristics.energy is not None:
        gap = _analyze_energy_gap(goal.characteristics.energy, role_state)
        all_gaps.append(gap)

    # ---- Analyze register ----
    if goal.characteristics.register is not None:
        gap = _analyze_register_gap(goal.characteristics.register, role_state)
        all_gaps.append(gap)

    # ---- Analyze density ----
    if goal.characteristics.density is not None:
        gap = _analyze_density_gap(goal.characteristics.density, role_state)
        all_gaps.append(gap)

    # ---- Analyze attack ----
    if goal.characteristics.attack is not None:
        gap = _analyze_attack_gap(goal.characteristics.attack, role_state)
        all_gaps.append(gap)

    # ---- Analyze sustain ----
    if goal.characteristics.sustain_length is not None:
        gap = _analyze_sustain_gap(goal.characteristics.sustain_length, role_state)
        all_gaps.append(gap)

    # ---- Analyze spread ----
    if goal.characteristics.spread is not None:
        gap = _analyze_spread_gap(goal.characteristics.spread, role_state)
        all_gaps.append(gap)

    # Categorize gaps
    satisfied = [g for g in all_gaps if g.gap_type == GapType.SATISFIED]
    missing = [g for g in all_gaps if g.gap_type == GapType.MISSING]
    contradictory = [g for g in all_gaps if g.gap_type == GapType.CONTRADICTORY]
    constrained = [g for g in all_gaps if g.gap_type == GapType.CONSTRAINED]
    ungrounded = [g for g in all_gaps if g.gap_type == GapType.UNGROUNDED]

    # Recommend next step
    if contradictory:
        recommended = (
            "This goal contradicts the current state. "
            "The following characteristics would need to be reversed: " +
            ", ".join(g.characteristic_name for g in contradictory)
        )
    elif ungrounded:
        recommended = (
            "This goal requires characteristics that have no known capability: " +
            ", ".join(g.characteristic_name for g in ungrounded) + ". "
            "A discovery experiment is needed."
        )
    elif constrained:
        recommended = (
            "This goal is blocked by known limitations: " +
            ", ".join(g.detail for g in constrained) + ". "
            "Check if the limitation can be lifted."
        )
    elif missing:
        recommended = (
            "This goal requires characteristics that are not yet measured. "
            "Apply the capabilities and measure to confirm."
        )
    else:
        recommended = "This goal is already satisfied; no changes needed."

    return GoalGroundingResult(
        goal=goal,
        role_state=role_state,
        all_gaps=all_gaps,
        satisfied=satisfied,
        missing=missing,
        contradictory=contradictory,
        constrained=constrained,
        ungrounded=ungrounded,
    )


# ---- Per-dimension gap analysis helpers ----

def _analyze_character_gap(char: Character, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze a character constraint (dark, bright, warm, etc.)."""
    if role_state is None:
        return CharacteristicGap(
            characteristic_name=f"character:{char.value}",
            goal_value=char.value,
            current_value=None,
            gap_type=GapType.MISSING,
            detail=f"role does not exist yet; {char.value} cannot be verified",
            possible_capabilities=["OSC1.Volume", "Filter.Cutoff", "Filter.Resonance"],
        )

    measured = role_state.measured_characteristics
    limitations = role_state.unresolved_limitations

    # Darkness → low brightness
    if char == Character.DARK:
        if measured.brightness is not None:
            if measured.brightness < 0.4:
                return CharacteristicGap(
                    characteristic_name="character:dark",
                    goal_value="dark",
                    current_value="dark",
                    gap_type=GapType.SATISFIED,
                    detail="brightness is already low",
                )
            else:
                return CharacteristicGap(
                    characteristic_name="character:dark",
                    goal_value="dark",
                    current_value="bright",
                    gap_type=GapType.CONTRADICTORY,
                    detail=f"brightness is {measured.brightness:.2f}, needs to be < 0.4",
                    possible_capabilities=["Filter.Cutoff"],
                )
        else:
            return CharacteristicGap(
                characteristic_name="character:dark",
                goal_value="dark",
                current_value=None,
                gap_type=GapType.MISSING,
                detail="darkness not yet measured; apply filter cutoff and measure",
                possible_capabilities=["Filter.Cutoff"],
            )

    # Brightness → high brightness
    if char == Character.BRIGHT:
        if measured.brightness is not None:
            if measured.brightness > 0.6:
                return CharacteristicGap(
                    characteristic_name="character:bright",
                    goal_value="bright",
                    current_value="bright",
                    gap_type=GapType.SATISFIED,
                    detail="brightness is already high",
                )
            else:
                return CharacteristicGap(
                    characteristic_name="character:bright",
                    goal_value="bright",
                    current_value="dark",
                    gap_type=GapType.CONTRADICTORY,
                    detail=f"brightness is {measured.brightness:.2f}, needs to be > 0.6",
                    possible_capabilities=["Filter.Cutoff"],
                )
        else:
            return CharacteristicGap(
                characteristic_name="character:bright",
                goal_value="bright",
                current_value=None,
                gap_type=GapType.MISSING,
                detail="brightness not yet measured",
                possible_capabilities=["Filter.Cutoff"],
            )

    # Other characters: unknown capability mapping for now
    return CharacteristicGap(
        characteristic_name=f"character:{char.value}",
        goal_value=char.value,
        current_value=None,
        gap_type=GapType.UNGROUNDED,
        detail=f"no known capability maps to {char.value}; discovery required",
        possible_capabilities=[],
    )


def _analyze_energy_gap(energy: Energy, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze energy constraint (low, medium, high)."""
    if role_state is None:
        return CharacteristicGap(
            characteristic_name="energy",
            goal_value=energy.value,
            current_value=None,
            gap_type=GapType.MISSING,
            detail=f"role does not exist; {energy.value} energy cannot be verified",
            possible_capabilities=["OSC1.Volume"],
        )

    measured = role_state.measured_characteristics

    # Energy → overall loudness
    if measured.overall_loudness_db is not None:
        # Heuristic thresholds (can be refined)
        if energy == Energy.LOW:
            if measured.overall_loudness_db < -18:
                return CharacteristicGap(
                    characteristic_name="energy",
                    goal_value="low",
                    current_value="low",
                    gap_type=GapType.SATISFIED,
                    detail=f"loudness is {measured.overall_loudness_db:.1f} dB",
                )
        elif energy == Energy.HIGH:
            if measured.overall_loudness_db > -12:
                return CharacteristicGap(
                    characteristic_name="energy",
                    goal_value="high",
                    current_value="high",
                    gap_type=GapType.SATISFIED,
                    detail=f"loudness is {measured.overall_loudness_db:.1f} dB",
                )
    else:
        return CharacteristicGap(
            characteristic_name="energy",
            goal_value=energy.value,
            current_value=None,
            gap_type=GapType.MISSING,
            detail=f"energy not yet measured",
            possible_capabilities=["OSC1.Volume"],
        )

    # Default: ungrounded
    return CharacteristicGap(
        characteristic_name="energy",
        goal_value=energy.value,
        current_value=None,
        gap_type=GapType.UNGROUNDED,
        detail=f"no capability for {energy.value} energy",
        possible_capabilities=[],
    )


def _analyze_register_gap(register: Register, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze register constraint (sub, low, mid, high)."""
    # Register is primarily determined by oscillator tuning and filter cutoff.
    # For now, treat as ungrounded (requires frequency analysis).
    return CharacteristicGap(
        characteristic_name="register",
        goal_value=register.value,
        current_value=None,
        gap_type=GapType.UNGROUNDED,
        detail=f"register analysis ({register.value}) requires spectral decomposition; not yet implemented",
        possible_capabilities=[],
    )


def _analyze_density_gap(density: Density, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze density constraint (sparse, medium, dense)."""
    # Density is texture thickness, primarily MIDI-driven (note density).
    # Serum control contribution is indirect (envelope sustain, resonance).
    return CharacteristicGap(
        characteristic_name="density",
        goal_value=density.value,
        current_value=None,
        gap_type=GapType.UNGROUNDED,
        detail=f"density ({density.value}) is primarily MIDI-driven; Serum controls are secondary",
        possible_capabilities=["Env1.Sustain", "Filter.Resonance"],
    )


def _analyze_attack_gap(attack: AttackProfile, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze attack constraint (slow, medium, fast, punchy)."""
    if role_state is None:
        return CharacteristicGap(
            characteristic_name="attack",
            goal_value=attack.value,
            current_value=None,
            gap_type=GapType.MISSING,
            detail=f"role does not exist; {attack.value} attack cannot be verified",
            possible_capabilities=["Env1.Attack"],
        )

    measured = role_state.measured_characteristics

    if measured.attack_speed is not None:
        if attack == AttackProfile.PUNCHY:
            if measured.attack_speed > 0.7:
                return CharacteristicGap(
                    characteristic_name="attack",
                    goal_value="punchy",
                    current_value="punchy",
                    gap_type=GapType.SATISFIED,
                    detail=f"attack speed is {measured.attack_speed:.2f} (fast)",
                )
        elif attack == AttackProfile.SLOW:
            if measured.attack_speed < 0.3:
                return CharacteristicGap(
                    characteristic_name="attack",
                    goal_value="slow",
                    current_value="slow",
                    gap_type=GapType.SATISFIED,
                    detail=f"attack speed is {measured.attack_speed:.2f} (slow)",
                )

    return CharacteristicGap(
        characteristic_name="attack",
        goal_value=attack.value,
        current_value=None,
        gap_type=GapType.MISSING,
        detail=f"attack ({attack.value}) not yet verified",
        possible_capabilities=["Env1.Attack"],
    )


def _analyze_sustain_gap(sustain: SustainLength, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze sustain constraint (short, medium, long)."""
    if role_state is None:
        return CharacteristicGap(
            characteristic_name="sustain_length",
            goal_value=sustain.value,
            current_value=None,
            gap_type=GapType.MISSING,
            detail=f"role does not exist; {sustain.value} sustain cannot be verified",
            possible_capabilities=["Env1.Sustain"],
        )

    limitations = role_state.unresolved_limitations

    # Check if Env1.Sustain is blocked
    if any("Env1.Sustain" in lim for lim in limitations):
        return CharacteristicGap(
            characteristic_name="sustain_length",
            goal_value=sustain.value,
            current_value=None,
            gap_type=GapType.CONSTRAINED,
            detail="Env1.Sustain is not available via MCP; a discovery request would be needed",
            possible_capabilities=["Env1.Sustain"],
        )

    measured = role_state.measured_characteristics

    if measured.sustain_level is not None:
        if sustain == SustainLength.LONG:
            if measured.sustain_level > 0.6:
                return CharacteristicGap(
                    characteristic_name="sustain_length",
                    goal_value="long",
                    current_value="long",
                    gap_type=GapType.SATISFIED,
                    detail=f"sustain level is {measured.sustain_level:.2f}",
                )
        elif sustain == SustainLength.SHORT:
            if measured.sustain_level < 0.3:
                return CharacteristicGap(
                    characteristic_name="sustain_length",
                    goal_value="short",
                    current_value="short",
                    gap_type=GapType.SATISFIED,
                    detail=f"sustain level is {measured.sustain_level:.2f}",
                )

    return CharacteristicGap(
        characteristic_name="sustain_length",
        goal_value=sustain.value,
        current_value=None,
        gap_type=GapType.MISSING,
        detail=f"sustain ({sustain.value}) not yet verified",
        possible_capabilities=["Env1.Sustain"],
    )


def _analyze_spread_gap(spread: Spread, role_state: Optional[RoleState]) -> CharacteristicGap:
    """Analyze spread constraint (mono, medium, wide)."""
    # Spread is primarily pan/width, not a core Serum synthesis parameter.
    return CharacteristicGap(
        characteristic_name="spread",
        goal_value=spread.value,
        current_value=None,
        gap_type=GapType.UNGROUNDED,
        detail=f"spread ({spread.value}) is primarily track panning, not Serum synthesis",
        possible_capabilities=[],
    )
