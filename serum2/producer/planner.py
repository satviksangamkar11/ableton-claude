"""16.5.61b: Planner — deterministic decision engine.

Reads GoalGroundingResult and evidence system, outputs Plan.

Decision rules per gap type:

  SATISFIED      → no action; goal already met
  MISSING        → find qualified capability → PlannedAction
  CONTRADICTORY  → find corrective capability OR report BlockedGap
  CONSTRAINED    → check if constraint lifts; if not → BlockedGap
  UNGROUNDED     → DiscoveryRequest

Invariants:

  1. Planner chooses what, not how. Output is intent-level, not parameter-level.
     Example: "increase_bass_brightness" (intent)
     NOT: "set Filter.Cutoff to 0.7" (parameter)

  2. Zero silent parameter selection.
     If no capability qualifies for a gap, Planner refuses (BlockedGap or DiscoveryRequest).

  3. Evidence system is authoritative.
     Only capabilities with CAUSAL_VERIFIED status (or specified lower status)
     can be selected. HYPOTHESIS/UNGROUNDED returns DiscoveryRequest.

  4. Context prerequisites are caller responsibility.
     Planner signals if prerequisites are missing; executor must verify.

  5. Planner decision is auditable.
     Every PlannedAction names the gap it addresses, the capability it chose,
     and why that capability was selected.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from .goal_grounding import GoalGroundingResult, CharacteristicGap, GapType
from .goal_model import GoalModel


@dataclass(frozen=True)
class PlannedAction:
    """One intentional action the Planner decided to execute.

    intent: human-readable action (e.g., "darken_bass", "increase_punchiness")
    target_dimension: musical dimension being addressed (e.g., "brightness", "attack")
    gap: the CharacteristicGap this action addresses
    selected_capability: semantic_target_name chosen to address the gap
    capability_key: capability_key from the evidence system (for audit)
    capability_status: CAUSAL_VERIFIED | STRUCTURAL_ONLY | HYPOTHESIS | UNGROUNDED
    reasoning: why this capability was chosen (e.g., "CAUSAL_VERIFIED, metric=centroid")
    """
    intent: str
    target_dimension: str
    gap: CharacteristicGap
    selected_capability: str
    capability_key: str
    capability_status: str
    reasoning: str


@dataclass(frozen=True)
class BlockedGap:
    """A gap the Planner could not resolve.

    gap: the CharacteristicGap that couldn't be addressed
    reason: why it's blocked (e.g., "no qualified capability", "constraint prevents action")
    detail: additional context
    """
    gap: CharacteristicGap
    reason: str
    detail: str


@dataclass(frozen=True)
class DiscoveryRequest:
    """Request for new evidence to support a goal.

    gap: the CharacteristicGap that is ungrounded
    reason: why discovery is needed
    candidate_targets: which semantic targets *might* address this
                       (caller must design isolated experiment)
    """
    gap: CharacteristicGap
    reason: str
    candidate_targets: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Plan:
    """Decision output from Planner.

    goal: the original GoalModel
    grounding: the GoalGroundingResult analyzed
    actions: PlannedActions to execute (musical intent level, not parameters)
    blocked_gaps: gaps the Planner could not resolve
    discovery_requests: gaps requiring new evidence
    confidence: "grounded" (all CAUSAL_VERIFIED), "bounded" (mix), "low" (contains HYPOTHESIS)
    """
    goal: GoalModel
    grounding: GoalGroundingResult
    confidence: str
    actions: List[PlannedAction] = field(default_factory=list)
    blocked_gaps: List[BlockedGap] = field(default_factory=list)
    discovery_requests: List[DiscoveryRequest] = field(default_factory=list)

    @property
    def is_executable(self) -> bool:
        """True if plan has no blocking gaps and no discovery requests."""
        return not (self.blocked_gaps or self.discovery_requests)

    @property
    def has_refusals(self) -> bool:
        """True if plan contains any refusals (blocked or discovery)."""
        return bool(self.blocked_gaps or self.discovery_requests)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for audit."""
        return {
            "goal": self.goal.to_dict(),
            "planned_actions": len(self.actions),
            "blocked_gaps": len(self.blocked_gaps),
            "discovery_requests": len(self.discovery_requests),
            "is_executable": self.is_executable,
            "confidence": self.confidence,
            "actions": [
                {
                    "intent": a.intent,
                    "dimension": a.target_dimension,
                    "capability": a.selected_capability,
                    "status": a.capability_status,
                    "reasoning": a.reasoning,
                }
                for a in self.actions
            ],
            "blocked": [
                {
                    "dimension": b.gap.characteristic_name,
                    "reason": b.reason,
                    "detail": b.detail,
                }
                for b in self.blocked_gaps
            ],
            "discoveries": [
                {
                    "dimension": d.gap.characteristic_name,
                    "reason": d.reason,
                    "candidates": d.candidate_targets,
                }
                for d in self.discovery_requests
            ],
        }


class PlannerDecisionEngine:
    """Planner that reads GoalGroundingResult and evidence system, outputs Plan.

    Caller supplies:
      - grounding: GoalGroundingResult (goal vs. world state analysis)
      - evidence_system: object with capabilities() query method
      - allowed_statuses: list of CapabilityContract.status values to accept
                          (default: ["CAUSAL_VERIFIED"] for fully grounded)

    Planner decides:
      - SATISFIED gaps → skip (goal already met)
      - MISSING gaps → find capability → PlannedAction
      - CONTRADICTORY gaps → find corrective capability OR BlockedGap
      - CONSTRAINED gaps → BlockedGap (prerequisites block execution)
      - UNGROUNDED gaps → DiscoveryRequest
    """

    def __init__(
        self,
        evidence_system: Any,
        allowed_statuses: Optional[List[str]] = None,
    ):
        """Initialize the Planner.

        evidence_system: object that can answer queries like:
          - evidence_system.get_capability(semantic_target_name, dimension)
          - evidence_system.get_contracts_for_dimension(dimension)

        allowed_statuses: which CapabilityContract.status values are acceptable
                         (default: ["CAUSAL_VERIFIED"])
                         To allow bounded/exploratory: ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY"]
        """
        self.evidence_system = evidence_system
        self.allowed_statuses = allowed_statuses or ["CAUSAL_VERIFIED"]

    def plan(self, grounding: GoalGroundingResult) -> Plan:
        """Convert GoalGroundingResult into an executable Plan.

        Returns Plan with actions, blocked_gaps, and discovery_requests.
        """
        actions = []
        blocked_gaps = []
        discovery_requests = []
        confidences = []

        goal = grounding.goal

        # ---- SATISFIED gaps: no action needed ----
        for gap in grounding.satisfied:
            # Confidence boost: goal is already met
            pass

        # ---- MISSING gaps: find capability ----
        for gap in grounding.missing:
            decision = self._plan_missing_gap(gap)
            if isinstance(decision, PlannedAction):
                actions.append(decision)
                confidences.append(decision.capability_status)
            elif isinstance(decision, DiscoveryRequest):
                discovery_requests.append(decision)
            elif isinstance(decision, BlockedGap):
                blocked_gaps.append(decision)

        # ---- CONTRADICTORY gaps: find corrective capability ----
        for gap in grounding.contradictory:
            decision = self._plan_contradictory_gap(gap)
            if isinstance(decision, PlannedAction):
                actions.append(decision)
                confidences.append(decision.capability_status)
            elif isinstance(decision, DiscoveryRequest):
                discovery_requests.append(decision)
            elif isinstance(decision, BlockedGap):
                blocked_gaps.append(decision)

        # ---- CONSTRAINED gaps: cannot execute ----
        for gap in grounding.constrained:
            blocked_gaps.append(BlockedGap(
                gap=gap,
                reason="CONSTRAINED",
                detail=gap.detail,
            ))

        # ---- UNGROUNDED gaps: discovery request ----
        for gap in grounding.ungrounded:
            discovery_requests.append(DiscoveryRequest(
                gap=gap,
                reason="UNGROUNDED",
                candidate_targets=gap.possible_capabilities or [],
            ))

        # Determine confidence
        confidence = self._determine_confidence(confidences)

        return Plan(
            goal=goal,
            grounding=grounding,
            actions=actions,
            blocked_gaps=blocked_gaps,
            discovery_requests=discovery_requests,
            confidence=confidence,
        )

    def _plan_missing_gap(self, gap: CharacteristicGap) -> "PlannedAction | BlockedGap | DiscoveryRequest":
        """Decide how to address a MISSING gap (goal required, not measured yet).

        MISSING gaps do NOT have a current contradiction. The characteristic
        is either not measured or unmeasured.

        Decision:
          1. Find a capability from gap.possible_capabilities that is in allowed_statuses
          2. If found and CAUSAL_VERIFIED → PlannedAction
          3. If found but lower status → PlannedAction with lower confidence
          4. If not found or status not allowed → DiscoveryRequest
        """
        if not gap.possible_capabilities:
            # No known capability for this gap
            return DiscoveryRequest(
                gap=gap,
                reason="NO_KNOWN_CAPABILITY",
                candidate_targets=[],
            )

        # Find the best qualified capability
        best_capability = None
        best_status = None
        best_key = None

        for semantic_target in gap.possible_capabilities:
            contract = self.evidence_system.get_capability(semantic_target)
            if contract is None:
                continue

            contract_status = getattr(contract, "status", "UNKNOWN")
            if contract_status not in self.allowed_statuses:
                continue

            # Prefer CAUSAL_VERIFIED over STRUCTURAL_ONLY
            if best_status is None or (
                contract_status == "CAUSAL_VERIFIED"
                and best_status != "CAUSAL_VERIFIED"
            ):
                best_capability = semantic_target
                best_status = contract_status
                best_key = getattr(contract, "target", semantic_target)

        if best_capability is None:
            # No qualified capability found
            return DiscoveryRequest(
                gap=gap,
                reason="NO_QUALIFIED_CAPABILITY",
                candidate_targets=gap.possible_capabilities,
            )

        # Found a qualified capability
        intent = self._intent_for_gap(gap)
        return PlannedAction(
            intent=intent,
            target_dimension=gap.characteristic_name,
            gap=gap,
            selected_capability=best_capability,
            capability_key=best_key,
            capability_status=best_status,
            reasoning=f"{best_status} contract available; metric link verified",
        )

    def _plan_contradictory_gap(self, gap: CharacteristicGap) -> "PlannedAction | BlockedGap | DiscoveryRequest":
        """Decide how to address a CONTRADICTORY gap (goal conflicts with current state).

        CONTRADICTORY means:
          - Goal requires value A
          - World state shows value B
          - A ≠ B (or A > B or A < B)

        Decision:
          1. Find a capability that moves in the correction direction
          2. If found and qualified → PlannedAction with "corrective" intent
          3. If not found or not qualified → BlockedGap (cannot proceed)
        """
        if not gap.possible_capabilities:
            return BlockedGap(
                gap=gap,
                reason="CONTRADICTORY_NO_CORRECTION",
                detail="Goal contradicts current state, but no known capability can correct it",
            )

        # Try to find a corrective capability
        # For now, assume the first possible_capability is the corrective one.
        # (In practice, this would be more nuanced based on measurement direction.)
        for semantic_target in gap.possible_capabilities:
            contract = self.evidence_system.get_capability(semantic_target)
            if contract is None:
                continue

            contract_status = getattr(contract, "status", "UNKNOWN")
            if contract_status not in self.allowed_statuses:
                continue

            # Found a corrective capability
            intent = self._intent_for_corrective_gap(gap)
            return PlannedAction(
                intent=intent,
                target_dimension=gap.characteristic_name,
                gap=gap,
                selected_capability=semantic_target,
                capability_key=getattr(contract, "target", semantic_target),
                capability_status=contract_status,
                reasoning=f"{contract_status}; reversing current {gap.current_value} to meet goal {gap.goal_value}",
            )

        # No qualified capability found
        return BlockedGap(
            gap=gap,
            reason="CONTRADICTORY_NO_QUALIFIED_CORRECTION",
            detail=(
                f"Goal {gap.goal_value} contradicts current {gap.current_value}; "
                f"no qualified capability found to correct it"
            ),
        )

    def _intent_for_gap(self, gap: CharacteristicGap) -> str:
        """Generate an intent string for a MISSING gap.

        Examples:
          - "darken_bass" (characteristic_name=brightness, goal_value=dark)
          - "increase_punchiness" (characteristic_name=attack, goal_value=punchy)
        """
        dim = gap.characteristic_name.replace(":", "_").replace(" ", "_")
        goal = str(gap.goal_value).replace(" ", "_")
        return f"{dim}_{goal}"

    def _intent_for_corrective_gap(self, gap: CharacteristicGap) -> str:
        """Generate an intent string for a CONTRADICTORY gap.

        Examples:
          - "correct_bass_brightness_from_bright_to_dark"
        """
        dim = gap.characteristic_name.replace(":", "_").replace(" ", "_")
        from_val = str(gap.current_value).replace(" ", "_")
        to_val = str(gap.goal_value).replace(" ", "_")
        return f"correct_{dim}_from_{from_val}_to_{to_val}"

    def _determine_confidence(self, statuses: List[str]) -> str:
        """Determine overall confidence level.

        "grounded" if all actions are CAUSAL_VERIFIED
        "bounded" if mix of CAUSAL_VERIFIED and STRUCTURAL_ONLY
        "low" if any HYPOTHESIS
        """
        if not statuses:
            return "unknown"
        if all(s == "CAUSAL_VERIFIED" for s in statuses):
            return "grounded"
        if "HYPOTHESIS" in statuses:
            return "low"
        if "STRUCTURAL_ONLY" in statuses and "CAUSAL_VERIFIED" in statuses:
            return "bounded"
        if all(s == "STRUCTURAL_ONLY" for s in statuses):
            return "structural"
        return "unknown"
