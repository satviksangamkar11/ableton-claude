"""16.5.8/16.5.11: Producer-facing result model for single- and multi-target requests.

ProducerResult answers the four questions independently:
  1. Can I set it?          -> structural_status (ACCEPT / REFUSE / UNKNOWN)
  2. Did Serum store it?    -> persistence_status (PASS / FAIL / NOT_RUN)
  3. Did the effect occur?  -> causal_status (from THIS execution's record,
                               never inherited from the witness contract)
  4. How certain?           -> execution_mode (WITNESS_MODE / STRUCTURAL_BIND_MODE)
                               + the full EvidenceRecord for traceability

produce() is the high-level single-target entry point.
Multi-target composition is in produce_goal() (16.5.11). The key honest
constraint: per-field execution_mode is knowable, but load/persistence/causal
come from one shared EvidenceRecord (one construction = one Serum write).
Per-field causal isolation would require N separate renders -- not done here.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ..evidence.record import NOT_RUN
from .targets import (
    SemanticTargetRef, ResolvedTarget, TargetRefusal,
    CONTEXT_NOT_SATISFIED, resolve_semantic_target, resolve_path,
)
from .structural_admission import (
    StructuralAdmissionResult, structural_admit, NOT_CHECKED, REFUSE as SA_REFUSE,
)
from .kernel import (
    dry_run, construct_and_verify,
    WITNESS_MODE, STRUCTURAL_BIND_MODE, REFUSED_CONTEXT_NOT_SATISFIED,
)


@dataclass(frozen=True)
class ProducerResult:
    # ---- identity ----
    requested_name: str           # semantic name, e.g. "FXEQ.Freq1"
    requested_value: Optional[Any]  # None = witness replay (WITNESS_MODE)
    execution_mode: str           # WITNESS_MODE | STRUCTURAL_BIND_MODE

    # ---- resolution ----
    resolved_ref: Optional[SemanticTargetRef]   # None on semantic resolution failure
    resolved_path: Optional[str]  # concrete path in body, None if context unsatisfied

    # ---- structural gate (question 1) ----
    structural_status: str        # ACCEPT | REFUSE | UNKNOWN | NOT_CHECKED
    structural_bounds: Optional[Any]  # StructuralProbeResult or None

    # ---- execution gates (questions 2 & 3) ----
    # From THIS execution's EvidenceRecord -- never from the witness contract.
    load_status: str              # PASS | FAIL | NOT_RUN
    persistence_status: str       # PASS | FAIL | NOT_RUN
    causal_status: str            # EFFECT_OBSERVED | NO_OBSERVED_EFFECT | NOT_RUN | ...
    measurement: Optional[Dict[str, Any]]

    # ---- refusal ----
    refusal_reason: Optional[str]
    refusal_detail: Optional[str]

    # ---- source ----
    record: Optional[Any]         # EvidenceRecord, or None if refused before execution

    def succeeded(self) -> bool:
        return (
            self.load_status == "PASS"
            and self.persistence_status == "PASS"
            and self.refusal_reason is None
        )


def produce(
    name: str,
    contracts: Dict[Tuple[str, str], Any],
    structural_records,
    body: Dict[str, Any],
    *,
    requested_value: Optional[Any] = None,
    experiment_id: str,
    skeleton=None,
    baseline_overrides=None,
    measure_overall_rms: bool = True,
) -> ProducerResult:
    """Single-target producer: resolves name, checks structural admission when
    requested_value is given, compiles, and returns a ProducerResult.

    WITNESS_MODE   : requested_value is None; mutation value comes from contract.
    STRUCTURAL_BIND: requested_value is provided; structural_admit() must ACCEPT
                     before dry_run() proceeds.
    """
    execution_mode = STRUCTURAL_BIND_MODE if requested_value is not None else WITNESS_MODE

    # ---- step 1: semantic resolution ----
    resolved = resolve_semantic_target(name, contracts)
    if isinstance(resolved, TargetRefusal):
        return ProducerResult(
            requested_name=name, requested_value=requested_value,
            execution_mode=execution_mode,
            resolved_ref=None, resolved_path=None,
            structural_status=NOT_CHECKED, structural_bounds=None,
            load_status=NOT_RUN, persistence_status=NOT_RUN, causal_status=NOT_RUN,
            measurement=None,
            refusal_reason=resolved.reason, refusal_detail=resolved.detail,
            record=None,
        )

    # ---- step 2: context-aware path resolution ----
    concrete_path = resolve_path(resolved, body)
    if concrete_path is None:
        return ProducerResult(
            requested_name=name, requested_value=requested_value,
            execution_mode=execution_mode,
            resolved_ref=resolved.ref, resolved_path=None,
            structural_status=NOT_CHECKED, structural_bounds=None,
            load_status=NOT_RUN, persistence_status=NOT_RUN, causal_status=NOT_RUN,
            measurement=None,
            refusal_reason=REFUSED_CONTEXT_NOT_SATISFIED,
            refusal_detail="context not satisfied in supplied body for %r" % name,
            record=None,
        )

    # ---- step 3: structural admission (STRUCTURAL_BIND_MODE only) ----
    struct_result: Optional[StructuralAdmissionResult] = None
    struct_status = NOT_CHECKED

    if execution_mode == STRUCTURAL_BIND_MODE:
        struct_result = structural_admit(resolved, requested_value, structural_records)
        struct_status = struct_result.status
        if struct_status == SA_REFUSE:
            return ProducerResult(
                requested_name=name, requested_value=requested_value,
                execution_mode=execution_mode,
                resolved_ref=resolved.ref, resolved_path=concrete_path,
                structural_status=struct_status,
                structural_bounds=struct_result.bounds,
                load_status=NOT_RUN, persistence_status=NOT_RUN, causal_status=NOT_RUN,
                measurement=None,
                refusal_reason="STRUCTURAL_ADMISSION_REFUSED",
                refusal_detail=struct_result.reason,
                record=None,
            )

    # ---- step 4: compiler dry_run ----
    capability_key = resolved.ref.capability_key
    rvo = {capability_key: requested_value} if execution_mode == STRUCTURAL_BIND_MODE else {}

    dry = dry_run(
        [capability_key], contracts,
        base_body=body,
        requested_value_overrides=rvo,
    )
    if not dry.accepted:
        return ProducerResult(
            requested_name=name, requested_value=requested_value,
            execution_mode=execution_mode,
            resolved_ref=resolved.ref, resolved_path=concrete_path,
            structural_status=struct_status,
            structural_bounds=struct_result.bounds if struct_result else None,
            load_status=NOT_RUN, persistence_status=NOT_RUN, causal_status=NOT_RUN,
            measurement=None,
            refusal_reason=dry.reason, refusal_detail=dry.detail,
            record=None,
        )

    # ---- step 5: construct and verify (touches Serum) ----
    rec = construct_and_verify(
        dry, experiment_id=experiment_id,
        measure_overall_rms=measure_overall_rms,
        skeleton=skeleton,
        baseline_overrides=baseline_overrides,
    )

    # ---- step 6: package result -- causal from THIS record only ----
    gate = rec.gate_completeness()
    causal_status = NOT_RUN
    measurement = None
    if rec.causal_measurements:
        m = rec.causal_measurements[0]
        causal_status = m.status
        measurement = {
            "metric": m.metric,
            "baseline": m.baseline,
            "treatment": m.treatment,
            "delta": m.delta,
            "status": m.status,
        }

    return ProducerResult(
        requested_name=name, requested_value=requested_value,
        execution_mode=execution_mode,
        resolved_ref=resolved.ref, resolved_path=concrete_path,
        structural_status=struct_status,
        structural_bounds=struct_result.bounds if struct_result else None,
        load_status=gate.get("load", NOT_RUN),
        persistence_status=gate.get("persistence", NOT_RUN),
        causal_status=causal_status,
        measurement=measurement,
        refusal_reason=None, refusal_detail=None,
        record=rec,
    )


# ---------------------------------------------------------------------------
# 16.5.11: Multi-field producer goal
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GoalField:
    """One target within a multi-field producer goal.

    requested_value=None means: use the contract's witness value (WITNESS_MODE).
    requested_value=<v>  means: use caller-selected value (STRUCTURAL_BIND_MODE);
                         structural admission must ACCEPT before dry_run proceeds.
    """
    name: str                     # semantic name, e.g. "FXEQ.Freq1"
    requested_value: Optional[Any]  # None = witness replay


@dataclass(frozen=True)
class FieldResult:
    """Per-field outcome from a multi-field goal.

    What IS per-field:
      - semantic resolution (name -> ref -> contract)
      - path resolution (concrete path in the given body)
      - structural admission (for STRUCTURAL_BIND fields)
      - execution_mode (WITNESS or STRUCTURAL_BIND, independently per field)
      - refusal (pre-execution refusals are per-field)

    What is NOT per-field (shared from one construction):
      - load / persistence / causal status
      These come from the single EvidenceRecord produced by one Serum write.
      Per-field causal isolation requires N separate renders -- not done here.
      GoalResult carries the shared gates; FieldResult does not repeat them.
    """
    name: str
    requested_value: Optional[Any]
    execution_mode: str                        # WITNESS_MODE | STRUCTURAL_BIND_MODE
    resolved_ref: Optional[SemanticTargetRef]  # None if semantic resolution failed
    resolved_path: Optional[str]               # None if context not satisfied
    structural_status: str                     # ACCEPT | REFUSE | UNKNOWN | NOT_CHECKED
    structural_bounds: Optional[Any]
    refusal_reason: Optional[str]              # non-None if this field blocked the goal
    refusal_detail: Optional[str]


@dataclass(frozen=True)
class GoalResult:
    """Result of a multi-field producer goal.

    Construction is atomic: all fields compiled into one ExperimentSpec, one
    Serum write, one EvidenceRecord. The per-field outcomes live in `fields`;
    the shared gates (load/persistence/causal) live here.

    overall_execution_mode = STRUCTURAL_BIND_MODE if ANY field has a
    requested_value override; WITNESS_MODE if all fields use witness values.
    This is a coarse label for the whole plan -- inspect FieldResult.execution_mode
    for per-field granularity.
    """
    fields: Tuple[FieldResult, ...]
    overall_accepted: bool         # False if any field caused a pre-execution refusal
    overall_execution_mode: str    # coarse plan-level mode
    # shared gates from the single EvidenceRecord
    load_status: str
    persistence_status: str
    causal_status: str
    measurement: Optional[Dict[str, Any]]
    # refusal (pre-execution, stops construction entirely)
    refusal_reason: Optional[str]
    refusal_detail: Optional[str]
    record: Optional[Any]

    def succeeded(self) -> bool:
        return (
            self.overall_accepted
            and self.load_status == "PASS"
            and self.persistence_status == "PASS"
            and self.refusal_reason is None
        )

    def field(self, name: str) -> Optional[FieldResult]:
        """Look up a FieldResult by semantic name."""
        return next((f for f in self.fields if f.name == name), None)


def produce_goal(
    goal_fields: List[GoalField],
    contracts: Dict[Tuple[str, str], Any],
    structural_records,
    body: Dict[str, Any],
    *,
    experiment_id: str,
    baseline_overrides=None,
    measure_overall_rms: bool = True,
) -> GoalResult:
    """Multi-field producer: resolves N semantic names, runs per-field structural
    admission for any field with a requested_value, compiles all into one
    ExperimentSpec, and returns GoalResult with per-field FieldResults.

    The goal is refused (pre-execution) if ANY field fails semantic resolution,
    context satisfaction, or structural admission (REFUSE). UNKNOWN structural
    status does NOT block execution -- the field proceeds in witness or caller
    mode with the value used as-is.

    Per the honesty constraint: load/persistence/causal come from the single
    shared EvidenceRecord. Per-field causal isolation is not provided.
    """
    field_results = []
    rvo: Dict[str, Any] = {}        # capability_key -> override value
    cap_keys: List[str] = []        # ordered capability keys for dry_run

    # --- Phase 1: per-field resolution and structural admission ---
    for gf in goal_fields:
        exec_mode = STRUCTURAL_BIND_MODE if gf.requested_value is not None else WITNESS_MODE

        resolved = resolve_semantic_target(gf.name, contracts)
        if isinstance(resolved, TargetRefusal):
            fr = FieldResult(
                name=gf.name, requested_value=gf.requested_value,
                execution_mode=exec_mode,
                resolved_ref=None, resolved_path=None,
                structural_status=NOT_CHECKED, structural_bounds=None,
                refusal_reason=resolved.reason, refusal_detail=resolved.detail,
            )
            field_results.append(fr)
            # One failed field refuses the whole goal
            return _refused_goal(field_results, resolved.reason, resolved.detail)

        concrete_path = resolve_path(resolved, body)
        if concrete_path is None:
            fr = FieldResult(
                name=gf.name, requested_value=gf.requested_value,
                execution_mode=exec_mode,
                resolved_ref=resolved.ref, resolved_path=None,
                structural_status=NOT_CHECKED, structural_bounds=None,
                refusal_reason=REFUSED_CONTEXT_NOT_SATISFIED,
                refusal_detail="context not satisfied in body for %r" % gf.name,
            )
            field_results.append(fr)
            return _refused_goal(field_results, REFUSED_CONTEXT_NOT_SATISFIED,
                                 "context not satisfied for field %r" % gf.name)

        struct_result = None
        struct_status = NOT_CHECKED
        if exec_mode == STRUCTURAL_BIND_MODE:
            struct_result = structural_admit(resolved, gf.requested_value, structural_records)
            struct_status = struct_result.status
            if struct_status == SA_REFUSE:
                fr = FieldResult(
                    name=gf.name, requested_value=gf.requested_value,
                    execution_mode=exec_mode,
                    resolved_ref=resolved.ref, resolved_path=concrete_path,
                    structural_status=struct_status,
                    structural_bounds=struct_result.bounds,
                    refusal_reason="STRUCTURAL_ADMISSION_REFUSED",
                    refusal_detail=struct_result.reason,
                )
                field_results.append(fr)
                return _refused_goal(field_results, "STRUCTURAL_ADMISSION_REFUSED",
                                     "field %r refused: %s" % (gf.name, struct_result.reason))

        cap_key = resolved.ref.capability_key
        cap_keys.append(cap_key)
        if gf.requested_value is not None:
            rvo[cap_key] = gf.requested_value

        field_results.append(FieldResult(
            name=gf.name, requested_value=gf.requested_value,
            execution_mode=exec_mode,
            resolved_ref=resolved.ref, resolved_path=concrete_path,
            structural_status=struct_status,
            structural_bounds=struct_result.bounds if struct_result else None,
            refusal_reason=None, refusal_detail=None,
        ))

    # --- Phase 2: single dry_run across all resolved fields ---
    overall_exec_mode = STRUCTURAL_BIND_MODE if rvo else WITNESS_MODE

    dry = dry_run(
        cap_keys, contracts,
        base_body=body,
        requested_value_overrides=rvo if rvo else None,
    )
    if not dry.accepted:
        return GoalResult(
            fields=tuple(field_results),
            overall_accepted=False,
            overall_execution_mode=overall_exec_mode,
            load_status=NOT_RUN, persistence_status=NOT_RUN, causal_status=NOT_RUN,
            measurement=None,
            refusal_reason=dry.reason, refusal_detail=dry.detail,
            record=None,
        )

    # --- Phase 3: one construction for all fields ---
    rec = construct_and_verify(
        dry, experiment_id=experiment_id,
        measure_overall_rms=measure_overall_rms,
        baseline_overrides=baseline_overrides,
    )

    gate = rec.gate_completeness()
    causal_status = NOT_RUN
    measurement = None
    if rec.causal_measurements:
        m = rec.causal_measurements[0]
        causal_status = m.status
        measurement = {
            "metric": m.metric, "baseline": m.baseline,
            "treatment": m.treatment, "delta": m.delta, "status": m.status,
        }

    return GoalResult(
        fields=tuple(field_results),
        overall_accepted=True,
        overall_execution_mode=overall_exec_mode,
        load_status=gate.get("load", NOT_RUN),
        persistence_status=gate.get("persistence", NOT_RUN),
        causal_status=causal_status,
        measurement=measurement,
        refusal_reason=None, refusal_detail=None,
        record=rec,
    )


def _refused_goal(
    field_results: List[FieldResult],
    reason: str,
    detail: str,
) -> GoalResult:
    """Return a refused GoalResult, preserving per-field outcomes accumulated so far."""
    return GoalResult(
        fields=tuple(field_results),
        overall_accepted=False,
        overall_execution_mode=WITNESS_MODE,
        load_status=NOT_RUN, persistence_status=NOT_RUN, causal_status=NOT_RUN,
        measurement=None,
        refusal_reason=reason, refusal_detail=detail,
        record=None,
    )
