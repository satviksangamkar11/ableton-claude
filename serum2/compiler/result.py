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
    StructuralAdmissionResult, structural_admit, NOT_CHECKED, REFUSE as SA_REFUSE, UNKNOWN as SA_UNKNOWN,
)
from .kernel import (
    dry_run, construct_and_verify,
    WITNESS_MODE, STRUCTURAL_BIND_MODE, REFUSED_CONTEXT_NOT_SATISFIED,
)


@dataclass(frozen=True)
class ProducerResult:
    """Single-field producer result answering six independent questions.

    CRITICAL SEMANTIC DISTINCTIONS (from AUDIT_16_5_54_SEMANTICS.md):

    1. Admission success (refusal_reason is None) ≠ causality proof
       Checks resolution, context, bounds. Doesn't prove field effect.

    2. Load success (load_status == PASS) ≠ field works
       Serum accepted the spec. Doesn't mean field causes effect.

    3. Persistence success (persistence_status == PASS) ≠ field is causal
       Mutation was stored. May be structural-only or require context.

    4. Execution-level effect (causal_status == EFFECT_OBSERVED) ≠ field caused it
       Overall_rms changed. Could be this field or interaction. Field causality
       requires CapabilityContract evidence (CAUSAL_VERIFIED) from knowledge loop.

    5. Measurement dict (this execution) ≠ capability claim
       Observation of this specific context. Capability claims live at contract layer.

    6. succeeded() == True (gates passed) ≠ field is proven effective
       Means: resolved+admitted+loaded+persisted+not refused.
       Actual field causality verified by producer loop (form_prediction grounding).

    Per honesty constraint: multi-field goals share ONE EvidenceRecord from one
    construction. Per-field causal isolation would require N separate renders.
    """
    # ---- identity ----
    requested_name: str
        # Semantic name, e.g. "FXEQ.Freq1" or "OSC1.Volume"
    requested_value: Optional[Any]
        # Value to set (STRUCTURAL_BIND_MODE) or None (WITNESS_MODE).
    execution_mode: str
        # WITNESS_MODE (value from contract) or STRUCTURAL_BIND_MODE (caller-provided).

    # ---- resolution gates (can I find this semantic target in this body?) ----
    resolved_ref: Optional[SemanticTargetRef]
        # SemanticTargetRef if found in SEMANTIC_TARGETS; None if semantic resolution failed.
        # Prerequisite: must be non-None for all downstream execution.
    resolved_path: Optional[str]
        # Concrete path in supplied body (e.g., "Oscillator0.plainParams.kParamVolume").
        # None means context not satisfied (required container/list element missing in body).
        # Prerequisite: must be non-None for structural admission and construct_and_verify.

    # ---- structural gate (can I set this value?) ----
    structural_status: str
        # ACCEPT: value is within provable bounds.
        # REFUSE: value violates provable bounds (may clamp, may reject).
        # UNKNOWN: no structural records available to validate (data-driven lower bound).
        # NOT_CHECKED: WITNESS_MODE (no validation needed; using contract value).
        # Policy: In STRUCTURAL_BIND_MODE, REFUSE or UNKNOWN → refusal before dry_run/construct.
    structural_bounds: Optional[Any]
        # StructuralProbeResult with min/max/observed (STRUCTURAL_BIND_MODE only).
        # None if WITNESS_MODE or structural admission not run.

    # ---- execution gates (did I actually run Serum and what happened?) ----
    # Source: From THIS execution's EvidenceRecord only. Never inherited from witness contract.
    # Honesty: one produce() = one ExperimentSpec = one EvidenceRecord.
    # Multi-field goals: all fields share ONE EvidenceRecord (one overall measurement, no per-field isolation).
    load_status: str
        # PASS: Both control and treatment arms rendered without error.
        # FAIL: At least one arm failed to load/render (plugin error, invalid spec).
        # NOT_RUN: construct_and_verify was not called (pre-execution refusal).
        # Semantic: PASS = Serum accepted the spec. Does NOT prove field effect.
    persistence_status: str
        # PASS: All mutations stored exactly (per tolerant_equal) in resaved state.
        # FAIL: At least one mutation differed (clamped, rejected, or not set).
        # NOT_RUN: construct_and_verify not called or persistence not checked.
        # Semantic: PASS = value was stored. Does NOT prove field has intended effect.
        # Example: persistence PASS + causal NO_OBSERVED_EFFECT = mutation applied, no measured delta.
    causal_status: str
        # EFFECT_OBSERVED: delta ≥ threshold, direction matches expected (measurement gate PASS).
        # NO_OBSERVED_EFFECT: absolute delta < threshold (measurement gate FAIL).
        # WRONG_DIRECTION: delta ≥ threshold but opposite direction (measurement gate FAIL).
        # NOT_RUN: measurement not taken (construct_and_verify not called).
        # Semantic: This is OVERALL effect (usually overall_rms_db), not field-specific causality.
        # Danger: EFFECT_OBSERVED does NOT prove THIS field caused it.
        # Field causality requires CapabilityContract.status == CAUSAL_VERIFIED from knowledge loop.
    measurement: Optional[Dict[str, Any]]
        # Execution snapshot: {"metric": str, "baseline": float, "treatment": float, "delta": float, "status": str}.
        # None if NOT_RUN (construct_and_verify not called or measurement not taken).
        # This is EXECUTION OBSERVATION, not a capability claim.
        # Never automatically launders overall_rms change into field-specific causality.

    # ---- pre-execution refusal gates ----
    refusal_reason: Optional[str]
        # Structured key if any pre-execution gate failed (e.g., "unknown_no_contract", "CONTEXT_NOT_SATISFIED").
        # None means: resolved_ref and resolved_path non-None, structural status acceptable, admission passed.
        # Non-None → construct_and_verify was NOT called, record is None.
    refusal_detail: Optional[str]
        # Human-readable explanation of refusal_reason.

    # ---- source of truth ----
    record: Optional[Any]
        # EvidenceRecord from construct_and_verify, or None if refused before execution.
        # None means: pre-execution refusal (construct_and_verify never called).
        # Presence of EvidenceRecord does NOT mean field is causal -- it's execution observation only.
        # Carries measurement_condition_signature and measurement_definition_id for provenance.

    def succeeded(self) -> bool:
        """Did all required execution gates pass?

        Criteria: load_status == PASS AND persistence_status == PASS AND refusal_reason is None.

        CRITICAL: succeeded() == True does NOT mean the field is causal.
        It means: mutation was resolved, admitted, applied, and stored.
        Whether that mutation CAUSED the measured effect requires:
        1. CapabilityContract.status == CAUSAL_VERIFIED (from knowledge loop)
        2. Producer loop form_prediction() check (grounding logic)
        3. Matching measurement conditions and definition IDs

        Danger zone: Never assume measurement["delta"] > 0 → field is causal.
        That requires independent CapabilityContract evidence.
        """
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
        if struct_status in (SA_REFUSE, SA_UNKNOWN):
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
    """Result of a multi-field producer goal (2+ targets in one execution).

    ATOMIC CONSTRUCTION: All fields compiled into ONE ExperimentSpec, ONE Serum write,
    ONE EvidenceRecord. Per-field pre-execution outcomes live in `fields`; shared
    execution gates (load/persistence/causal) live here.

    Semantic separation:
    - Per-field: semantic resolution, path resolution, structural admission, execution_mode.
    - Shared: load_status, persistence_status, causal_status (from one EvidenceRecord).

    Per the honesty constraint: goal measurement is OVERALL (usually overall_rms_db),
    not per-field isolated. Field-level causality claims require CapabilityContract
    evidence from the knowledge loop, not result measurement alone.

    overall_execution_mode = STRUCTURAL_BIND_MODE if ANY field has a requested_value;
    WITNESS_MODE if all use witness values. Coarse plan label; inspect
    FieldResult.execution_mode for per-field granularity.
    """
    fields: Tuple[FieldResult, ...]
        # Per-field outcomes (semantic, path, structural, execution_mode, refusal).
    overall_accepted: bool
        # False if ANY field caused a pre-execution refusal (goal refused entirely).
    overall_execution_mode: str
        # STRUCTURAL_BIND_MODE if any field has requested_value; WITNESS_MODE otherwise.
    # Shared gates from the single EvidenceRecord:
    load_status: str
        # PASS/FAIL/NOT_RUN: did Serum render both control and treatment arms?
    persistence_status: str
        # PASS/FAIL/NOT_RUN: did Serum persist the mutations to state?
    causal_status: str
        # EFFECT_OBSERVED/NO_OBSERVED_EFFECT/WRONG_DIRECTION/NOT_RUN: overall measurement result.
    measurement: Optional[Dict[str, Any]]
        # Overall measurement snapshot (one per goal, not per field).
    # Pre-execution refusal (stops entire goal):
    refusal_reason: Optional[str]
        # Structured key if goal refused before construction (any field refusal refuses goal).
    refusal_detail: Optional[str]
        # Human-readable explanation.
    record: Optional[Any]
        # EvidenceRecord from construct_and_verify, or None if goal refused pre-execution.

    def succeeded(self) -> bool:
        """Did all fields and gates pass?

        Criteria: overall_accepted AND load == PASS AND persistence == PASS AND no refusal.

        CRITICAL: succeeded() == True means all gates passed and fields were compiled.
        It does NOT mean fields are causal -- that requires per-field CapabilityContract
        evidence evaluation in the producer loop (form_prediction grounding).

        Shared measurement is OVERALL effect, not per-field proof.
        """
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
