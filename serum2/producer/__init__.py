"""16.5.61: Producer World Model + Goal Planner.

Sits above the compiler/capability infrastructure to add strategic reasoning:

    User Intent
        ↓ (Goal Parser)
    GoalModel (structured musical objective, no parameters)
        ↓ (Planner reads)
    WorldModel (current state: sections, roles, capabilities)
        ↓ (Gap Analysis)
    GoalGrounding (satisfied/missing/contradictory/constrained/ungrounded)
        ↓ (Planner decides)
    Plan (intentional actions, not raw MCP calls)
        ↓ (Executor)
    Measurement / Evaluation
        ↓ (Feedback to Planner)

Modules:
  - goal_model: GoalModel (user intent → structured musical objectives)
  - world_model: WorldModel (current state snapshot)
  - goal_grounding: GoalGroundingResult (goal vs. state gap analysis)
  - planner: ProductionPlan (goal + gaps + capabilities → actions)

INVARIANTS:
  1. No Serum parameters in GoalModel or Plan inputs
  2. WorldModel is read-only (updated externally)
  3. Gap types are closed enum (SATISFIED, MISSING, CONTRADICTORY, CONSTRAINED, UNGROUNDED)
  4. Planner output is intentional (e.g., "increase_bass_brightness") not tactical (e.g., "set Filter1Freq to 0.5")
"""

from .goal_model import (
    GoalModel,
    MusicalCharacteristics,
    Character,
    Energy,
    Register,
    Density,
    AttackProfile,
    SustainLength,
    Spread,
)

from .world_model import (
    WorldModel,
    ArrangementState,
    RoleState,
    SerumState,
    SectionState,
    VerifiedCapability,
    MeasuredCharacteristics,
)

from .goal_grounding import (
    GoalGroundingResult,
    CharacteristicGap,
    GapType,
    ground_goal,
)

__all__ = [
    # Goal Model
    "GoalModel",
    "MusicalCharacteristics",
    "Character",
    "Energy",
    "Register",
    "Density",
    "AttackProfile",
    "SustainLength",
    "Spread",
    # World Model
    "WorldModel",
    "ArrangementState",
    "RoleState",
    "SerumState",
    "SectionState",
    "VerifiedCapability",
    "MeasuredCharacteristics",
    # Goal Grounding
    "GoalGroundingResult",
    "CharacteristicGap",
    "GapType",
    "ground_goal",
]
