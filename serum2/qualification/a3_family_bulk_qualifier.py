"""16.5.69.2-A3: Family-based bulk qualification framework.

Replicates the OSC1 family-qualification strategy across arbitrary parameter families.

Pipeline:
  1. discover_family()            — extract all controls in a family
  2. select_representatives()      — pick key controls for route resolution
  3. qualify_representatives()     — measure representatives experimentally
  4. bulk_qualify_members()        — apply proven routes to family members
  5. isolate_exceptions()          — separate outliers for deeper investigation

Route reuse principle:
  Proven route pattern
      ↓
  eligible family member
      ↓
  bulk mutation
      ↓
  individual readback/evidence
      ↓
  PASS → keep family classification
  FAIL → exception queue

Never assume evidence reuse; always observe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from serum2.qualification.a3_route import MutationRoute, BehaviorRoute
from serum2.qualification.a3_control_executor import ControlExecutor


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class MutationClass(Enum):
    """Parameter mutation type classification."""

    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    INTEGER = "INTEGER"
    SCALAR = "SCALAR"
    STRING = "STRING"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class FamilyControl:
    """A single control within a family."""

    family: str
    semantic_id: str
    vst3_name: str
    vst3_index: int
    mutation_class: MutationClass
    capability_key: Optional[str] = None
    surface_class: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "semantic_id": self.semantic_id,
            "vst3_name": self.vst3_name,
            "vst3_index": self.vst3_index,
            "mutation_class": self.mutation_class.value,
            "capability_key": self.capability_key,
            "surface_class": self.surface_class,
        }


@dataclass(frozen=True)
class Representative:
    """A representative control selected for experimental qualification."""

    semantic_id: str
    mutation_class: MutationClass
    route: Optional[MutationRoute] = None
    evidence_id: Optional[str] = None
    reuse_existing: bool = False
    rationale: Optional[str] = None


@dataclass(frozen=True)
class RoutePatternSet:
    """Proven route patterns from representatives."""

    family: str
    patterns: dict[MutationClass, MutationRoute] = field(default_factory=dict)
    behavior_route: Optional[BehaviorRoute] = None

    def get_route_for_class(self, mutation_class: MutationClass) -> Optional[MutationRoute]:
        return self.patterns.get(mutation_class)


@dataclass
class BulkQualificationResult:
    """Result of bulk-qualifying a family."""

    family: str
    discovered: int
    qualified: int
    exceptions: list[FamilyControl]
    results: list[ParameterQualificationRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "discovered": self.discovered,
            "qualified": self.qualified,
            "exception_count": len(self.exceptions),
            "exceptions": [e.to_dict() for e in self.exceptions],
            "results": [r.to_dict() for r in self.results],
        }


@dataclass(frozen=True)
class ParameterQualificationRecord:
    """Evidence record for one parameter qualification attempt."""

    semantic_id: str
    vst3_name: str
    vst3_index: int
    mutation_class: MutationClass
    operation: str  # "set" | "readback" | "restore"
    baseline_value: object
    mutated_value: object
    read_value: object
    success: bool
    error: Optional[str] = None
    route_used: Optional[MutationRoute] = None

    def to_dict(self) -> dict:
        return {
            "semantic_id": self.semantic_id,
            "vst3_name": self.vst3_name,
            "vst3_index": self.vst3_index,
            "mutation_class": self.mutation_class.value,
            "operation": self.operation,
            "baseline_value": str(self.baseline_value),
            "mutated_value": str(self.mutated_value),
            "read_value": str(self.read_value),
            "success": self.success,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_family(
    inventory: list[dict],
    family_name: str,
) -> list[FamilyControl]:
    """Extract all controls in a family from parameter inventory.

    Args:
        inventory: list of parameter dicts from VST3 discovery
        family_name: "Osc1", "Filter1", "Env1", etc.

    Returns:
        list of FamilyControl sorted by vst3_index
    """
    controls = []

    for param in inventory:
        vst3_name = param.get("vst3_name", "")
        vst3_index = param.get("vst3_index", -1)
        mutation_class_str = param.get("mutation_class", "UNKNOWN")
        semantic_id = param.get("semantic_candidate", "UNMAPPED")
        surface_class = param.get("surface_class", "UNKNOWN")

        # Quick family check
        if not _matches_family(vst3_name, family_name):
            continue

        try:
            mutation_class = MutationClass[mutation_class_str]
        except KeyError:
            mutation_class = MutationClass.UNKNOWN

        control = FamilyControl(
            family=family_name,
            semantic_id=semantic_id,
            vst3_name=vst3_name,
            vst3_index=vst3_index,
            mutation_class=mutation_class,
            surface_class=surface_class,
        )
        controls.append(control)

    return sorted(controls, key=lambda c: c.vst3_index)


def _matches_family(vst3_name: str, family_name: str) -> bool:
    """Check if a VST3 parameter name belongs to a family."""
    from serum2.qualification.a3_surface_classifier import _extract_family_name

    extracted = _extract_family_name(vst3_name)
    return extracted == family_name


# ---------------------------------------------------------------------------
# Representative selection
# ---------------------------------------------------------------------------

def select_representatives(
    controls: list[FamilyControl],
    existing_evidence: dict[str, object],
) -> list[Representative]:
    """Select representative controls for route qualification.

    Strategy:
      - Reuse existing evidence for already-qualified controls
      - Pick one exemplar per mutation class
      - Prefer variety (scalar, enum, boolean if available)

    Args:
        controls: list of FamilyControl
        existing_evidence: dict[semantic_id] → evidence

    Returns:
        list of Representative
    """
    reps: list[Representative] = []
    seen_classes: set[MutationClass] = set()

    # First pass: reuse existing evidence
    for control in controls:
        if control.semantic_id in existing_evidence:
            if control.mutation_class not in seen_classes:
                reps.append(
                    Representative(
                        semantic_id=control.semantic_id,
                        mutation_class=control.mutation_class,
                        evidence_id=control.semantic_id,
                        reuse_existing=True,
                        rationale=f"Existing evidence: {control.semantic_id}",
                    )
                )
                seen_classes.add(control.mutation_class)

    # Second pass: select new representatives for uncovered mutation classes
    for control in controls:
        if control.mutation_class in seen_classes:
            continue
        if control.semantic_id in existing_evidence:
            continue

        # Pick this as a representative
        reps.append(
            Representative(
                semantic_id=control.semantic_id,
                mutation_class=control.mutation_class,
                reuse_existing=False,
                rationale=f"New representative for {control.mutation_class.value}",
            )
        )
        seen_classes.add(control.mutation_class)

    return sorted(reps, key=lambda r: r.semantic_id)


# ---------------------------------------------------------------------------
# Bulk qualification
# ---------------------------------------------------------------------------

def bulk_qualify_members(
    controls: list[FamilyControl],
    proven_routes: RoutePatternSet,
    executor: ControlExecutor,
    test_values: Optional[dict[MutationClass, object]] = None,
) -> BulkQualificationResult:
    """Bulk-qualify family members using proven routes.

    Process:
      1. For each member, determine mutation class
      2. Look up proven route for that class
      3. Execute set/readback/restore via executor
      4. Record individual evidence
      5. Separate passes from exceptions

    Args:
        controls: list of FamilyControl to qualify
        proven_routes: RoutePatternSet with patterns per mutation class
        executor: ControlExecutor for parameter operations
        test_values: optional dict[MutationClass] → test_value

    Returns:
        BulkQualificationResult
    """
    if test_values is None:
        test_values = _default_test_values()

    result = BulkQualificationResult(
        family=proven_routes.family,
        discovered=len(controls),
        qualified=0,
        exceptions=[],
    )

    for control in controls:
        route = proven_routes.get_route_for_class(control.mutation_class)
        if route is None:
            result.exceptions.append(control)
            continue

        test_value = test_values.get(control.mutation_class, 0.5)

        try:
            # Baseline read
            baseline = executor.read_parameter(control.semantic_id)

            # Mutation
            executor.set_parameter(control.semantic_id, test_value)

            # Readback
            read_value = executor.read_parameter(control.semantic_id)

            # Restoration
            executor.restore_parameter(control.semantic_id, baseline)

            # Record success
            success = read_value == test_value or _value_close(
                read_value, test_value, control.mutation_class
            )
            record = ParameterQualificationRecord(
                semantic_id=control.semantic_id,
                vst3_name=control.vst3_name,
                vst3_index=control.vst3_index,
                mutation_class=control.mutation_class,
                operation="set/readback/restore",
                baseline_value=baseline,
                mutated_value=test_value,
                read_value=read_value,
                success=success,
                route_used=route,
            )
            result.results.append(record)

            if success:
                result.qualified += 1
            else:
                result.exceptions.append(control)

        except Exception as e:
            result.exceptions.append(control)
            record = ParameterQualificationRecord(
                semantic_id=control.semantic_id,
                vst3_name=control.vst3_name,
                vst3_index=control.vst3_index,
                mutation_class=control.mutation_class,
                operation="set/readback/restore",
                baseline_value=None,
                mutated_value=test_value,
                read_value=None,
                success=False,
                error=str(e),
                route_used=route,
            )
            result.results.append(record)

    return result


def _value_close(a: object, b: object, mutation_class: MutationClass) -> bool:
    """Check if two values are approximately equal for a mutation class."""
    if mutation_class in {MutationClass.BOOLEAN, MutationClass.ENUM, MutationClass.STRING}:
        return a == b

    # SCALAR, INTEGER: allow small numeric tolerance
    try:
        return abs(float(a) - float(b)) < 1e-6  # type: ignore
    except (TypeError, ValueError):
        return a == b


def _default_test_values() -> dict[MutationClass, object]:
    """Default test values for each mutation class."""
    return {
        MutationClass.BOOLEAN: True,
        MutationClass.ENUM: 1,
        MutationClass.INTEGER: 42,
        MutationClass.SCALAR: 0.5,
        MutationClass.STRING: "test",
        MutationClass.UNKNOWN: 0.5,
    }


# ---------------------------------------------------------------------------
# Exception isolation
# ---------------------------------------------------------------------------

def isolate_exceptions(result: BulkQualificationResult) -> list[FamilyControl]:
    """Extract controls that failed bulk qualification.

    These are candidates for deeper investigation or manual classification.

    Args:
        result: BulkQualificationResult

    Returns:
        list of exception FamilyControl objects
    """
    return result.exceptions
