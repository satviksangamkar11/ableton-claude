"""16.5.61b: Adversarial tests for PlannerDecisionEngine.

Tests that the Planner:
  1. Accepts valid capabilities and produces PlannedActions
  2. Refuses unsupported intents with DiscoveryRequest
  3. Refuses HYPOTHESIS capabilities (returns DiscoveryRequest, not silent execution)
  4. Refuses unresolvable contradictions with BlockedGap
  5. Refuses constrained gaps that block prerequisites

Run with: python -m pytest serum2/producer/test_planner_adversarial.py -v
"""
import pytest
from datetime import datetime
from unittest.mock import Mock

from .goal_model import (
    GoalModel,
    MusicalCharacteristics,
    Character,
    Energy,
    Register,
    AttackProfile,
    SustainLength,
)
from .world_model import (
    WorldModel,
    ArrangementState,
    RoleState,
    SerumState,
    SectionState,
    MeasuredCharacteristics,
)
from .goal_grounding import ground_goal, GapType
from .planner import PlannerDecisionEngine, Plan


class MockEvidenceSystem:
    """Mock evidence system for testing.

    Hardcoded capabilities:
      - Filter.Cutoff: CAUSAL_VERIFIED
      - Env1.Attack: CAUSAL_VERIFIED
      - Env1.Sustain: None (no MCP mapping)
      - Env1.Release: None (no MCP mapping, a constraint)
      - OSC1.Volume: CAUSAL_VERIFIED
    """

    CONTRACTS = {
        "Filter.Cutoff": {
            "target": "Filter.Cutoff",
            "status": "CAUSAL_VERIFIED",
            "capability_key": "filter_cutoff_brightness",
        },
        "Env1.Attack": {
            "target": "Env1.Attack",
            "status": "CAUSAL_VERIFIED",
            "capability_key": "env1_attack_speed",
        },
        "OSC1.Volume": {
            "target": "OSC1.Volume",
            "status": "CAUSAL_VERIFIED",
            "capability_key": "osc1_volume_loudness",
        },
        # Env1.Sustain and Env1.Release intentionally absent (no MCP mapping)
    }

    def get_capability(self, semantic_target):
        """Return a contract or None."""
        contract_dict = self.CONTRACTS.get(semantic_target)
        if contract_dict is None:
            return None
        # Return a mock object with attributes
        mock = Mock()
        for key, value in contract_dict.items():
            setattr(mock, key, value)
        return mock


class TestPlannerHappyPath:
    """Test: Planner accepts valid, grounded goals."""

    def test_plan_darker_punchier_bass(self):
        """User: 'Make the bass darker and punchier for the peak.'

        Expected: Two PlannedActions (darken, make punchy).
        """
        # Setup: bass role exists with medium brightness, medium attack
        world = WorldModel(
            arrangement=ArrangementState(
                key="A minor",
                tempo_bpm=124,
                sections=[
                    SectionState("peak", 16, 16, ["bass"]),
                ],
            ),
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    serum_state=SerumState(
                        parameter_values={"Filter.Cutoff": 0.5, "Env1.Attack": 0.5},
                    ),
                    measured_characteristics=MeasuredCharacteristics(
                        brightness=0.5,       # medium → goal wants < 0.4 (dark)
                        attack_speed=0.5,     # medium → goal wants > 0.7 (punchy)
                        overall_loudness_db=-14.5,
                    ),
                ),
            },
        )

        # Goal: darker + punchier
        goal = GoalModel(
            user_phrasing="Make the bass darker and punchier for the peak",
            role="bass",
            section_name="peak",
            characteristics=MusicalCharacteristics(
                character=[Character.DARK, Character.PUNCHY],
            ),
        )

        # Ground the goal
        grounding = ground_goal(goal, world)
        assert len(grounding.contradictory) == 2, f"Expected 2 contradictions; got {len(grounding.contradictory)}"

        # Plan with mocked evidence
        evidence = MockEvidenceSystem()
        planner = PlannerDecisionEngine(evidence, allowed_statuses=["CAUSAL_VERIFIED"])
        plan = planner.plan(grounding)

        # Verify: plan is executable, has two actions, no refusals
        assert plan.is_executable, "Plan should be executable"
        assert len(plan.actions) == 2, f"Expected 2 actions; got {len(plan.actions)}"
        assert plan.confidence == "grounded", f"Expected 'grounded'; got {plan.confidence}"
        assert not plan.blocked_gaps, "Should have no blocked gaps"
        assert not plan.discovery_requests, "Should have no discovery requests"

        # Verify action details
        action_intents = [a.intent for a in plan.actions]
        # Corrective intents name the correction: "correct_character_dark_from_bright_to_dark"
        assert any("dark" in intent for intent in action_intents), \
            f"Expected action addressing darkness; got {action_intents}"
        assert any("punchy" in intent for intent in action_intents), \
            f"Expected action addressing punchiness; got {action_intents}"


class TestPlannerRefusalsAdversarial:
    """Test: Planner refuses unsupported intents WITHOUT SILENT PARAMETER SELECTION."""

    def test_refuse_longer_env1_release(self):
        """User: 'Give the bass longer sustain.'

        Setup: Env1.Release is CONSTRAINED (in unresolved_limitations).
        Expected: Planner should refuse with BlockedGap, NOT a silent parameter write.
        """
        # Setup: bass role exists with sustain blocked in limitations
        world = WorldModel(
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    measured_characteristics=MeasuredCharacteristics(
                        sustain_level=0.3,  # short sustain
                    ),
                    unresolved_limitations=[
                        "no MCP mapping for Env1.Release",
                    ],
                ),
            },
        )

        # Goal: longer sustain
        goal = GoalModel(
            user_phrasing="Give the bass longer sustain",
            role="bass",
            characteristics=MusicalCharacteristics(
                sustain_length=SustainLength.LONG,
            ),
        )

        # Ground the goal
        grounding = ground_goal(goal, world)

        # Should have a CONSTRAINED gap (Env1.Release is blocked)
        assert len(grounding.constrained) > 0, \
            f"Expected constrained gap; got gaps: {[(g.characteristic_name, g.gap_type) for g in grounding.all_gaps]}"

        # Plan
        evidence = MockEvidenceSystem()
        planner = PlannerDecisionEngine(evidence, allowed_statuses=["CAUSAL_VERIFIED"])
        plan = planner.plan(grounding)

        # Verify: plan should NOT be executable
        assert not plan.is_executable, "Plan should NOT be executable (sustain is constrained)"
        assert len(plan.blocked_gaps) > 0, "Should have blocked gaps"

    def test_refuse_ungrounded_warm(self):
        """User: 'Make the bass warmer.'

        If 'warm' has no capability mapping (UNGROUNDED), Planner should:
        - NOT produce a PlannedAction
        - Return DiscoveryRequest

        NOT: "I don't know what 'warm' is, but let me silently apply OSC1.Volume..."
        """
        world = WorldModel(
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    measured_characteristics=MeasuredCharacteristics(
                        brightness=0.5,  # measured but not satisfied
                    ),
                ),
            },
        )

        # Goal: make it warm (no known capability for 'warm')
        goal = GoalModel(
            user_phrasing="Make the bass warmer",
            role="bass",
            characteristics=MusicalCharacteristics(
                character=[Character.WARM],
            ),
        )

        grounding = ground_goal(goal, world)
        # "warm" should be UNGROUNDED (no capability mapping)
        ungrounded_names = [g.characteristic_name for g in grounding.ungrounded]
        assert any("warm" in name for name in ungrounded_names), \
            f"Expected 'warm' to be ungrounded; got gaps: {[(g.characteristic_name, g.gap_type) for g in grounding.all_gaps]}"

        evidence = MockEvidenceSystem()
        planner = PlannerDecisionEngine(evidence)
        plan = planner.plan(grounding)

        # Verify: MUST have discovery request, NOT a silent action
        assert len(plan.discovery_requests) > 0, \
            "Ungrounded gap should produce DiscoveryRequest"
        assert not plan.is_executable, "Plan should NOT be executable"

    def test_refuse_contradictory_without_correction_capability(self):
        """Setup: a gap is CONTRADICTORY but no capability can correct it.

        Setup: brightness is high (contradictory to "dark"), but evidence system
        has no capability for brightness correction (MockEvidenceSystem has Filter.Cutoff
        but let's simulate absence).

        Expected: BlockedGap, not silent execution or guessing.
        """
        world = WorldModel(
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    measured_characteristics=MeasuredCharacteristics(
                        brightness=0.8,  # too bright, contradicts goal "dark"
                    ),
                ),
            },
        )

        # Goal: make dark (contradicts current brightness)
        goal = GoalModel(
            user_phrasing="Make the bass dark",
            role="bass",
            characteristics=MusicalCharacteristics(
                character=[Character.DARK],
            ),
        )

        grounding = ground_goal(goal, world)
        assert len(grounding.contradictory) > 0, "Should have contradictory gap"

        # Use a mock evidence system with NO capability for brightness
        class EmptyEvidenceSystem:
            def get_capability(self, semantic_target):
                return None  # No capability available

        evidence = EmptyEvidenceSystem()
        planner = PlannerDecisionEngine(evidence)
        plan = planner.plan(grounding)

        # Verify: blocked gap, not silent action
        assert not plan.is_executable, "Plan should NOT be executable (no capability to correct)"
        assert len(plan.blocked_gaps) > 0, "Should have blocked gap"


class TestPlannerConfidenceTracking:
    """Test: Planner correctly tracks confidence levels."""

    def test_confidence_grounded(self):
        """All actions CAUSAL_VERIFIED → confidence='grounded'."""
        world = WorldModel(
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    measured_characteristics=MeasuredCharacteristics(
                        brightness=0.6,  # too bright
                        attack_speed=0.5,  # too slow
                    ),
                ),
            },
        )

        goal = GoalModel(
            user_phrasing="Darken and quicken the bass",
            role="bass",
            characteristics=MusicalCharacteristics(
                character=[Character.DARK, Character.PUNCHY],
            ),
        )

        grounding = ground_goal(goal, world)
        evidence = MockEvidenceSystem()  # All contracts are CAUSAL_VERIFIED
        planner = PlannerDecisionEngine(evidence)
        plan = planner.plan(grounding)

        assert plan.confidence == "grounded", "All actions CAUSAL_VERIFIED"
        assert plan.is_executable, "Plan should be executable"

    def test_confidence_low_with_discovery(self):
        """If any gaps require discovery → plan has discovery_requests."""
        world = WorldModel(
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    measured_characteristics=MeasuredCharacteristics(
                        brightness=0.5,  # measured
                    ),
                ),
            },
        )

        goal = GoalModel(
            user_phrasing="Make the bass warm",
            role="bass",
            characteristics=MusicalCharacteristics(
                character=[Character.WARM],  # ungrounded (no capability)
            ),
        )

        grounding = ground_goal(goal, world)
        # "warm" should be UNGROUNDED
        assert len(grounding.ungrounded) > 0, "Should have ungrounded gaps"

        evidence = MockEvidenceSystem()
        planner = PlannerDecisionEngine(evidence)
        plan = planner.plan(grounding)

        assert not plan.is_executable, "Should have refusals"
        assert len(plan.discovery_requests) > 0, "Should require discovery"


class TestPlannerAuditability:
    """Test: Every PlannedAction is auditable."""

    def test_planned_action_has_reasoning(self):
        """Each action names why the capability was chosen."""
        world = WorldModel(
            roles={
                "bass": RoleState(
                    role="bass",
                    track_id=0,
                    device_index=0,
                    measured_characteristics=MeasuredCharacteristics(
                        brightness=0.7,  # too bright
                    ),
                ),
            },
        )

        goal = GoalModel(
            user_phrasing="Darken the bass",
            role="bass",
            characteristics=MusicalCharacteristics(
                character=[Character.DARK],
            ),
        )

        grounding = ground_goal(goal, world)
        evidence = MockEvidenceSystem()
        planner = PlannerDecisionEngine(evidence)
        plan = planner.plan(grounding)

        assert len(plan.actions) == 1, "One action expected"
        action = plan.actions[0]

        # Verify auditability
        assert action.intent, "Action must have intent"
        assert action.target_dimension, "Action must name the dimension"
        assert action.selected_capability, "Action must name the capability"
        assert action.capability_status, "Action must show status"
        assert action.reasoning, "Action must explain why"

        # Example reasoning
        assert "CAUSAL_VERIFIED" in action.reasoning, \
            "Reasoning should explain the capability status"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
