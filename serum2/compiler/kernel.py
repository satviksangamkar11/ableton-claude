"""16.1: Minimum Executable Compiler Kernel.

Composes already-admitted CapabilityContracts into one Serum patch. Deliberately
minimal: no new epistemic logic anywhere in this file. Every step reuses Step
15/15.4 machinery directly --

  16.1.1 contract admission        -> evidence.admission.admit()
  16.1.2 cross-contract conflicts  -> pathmerge.path_relationship_conflicts()
                                       applied pairwise across contracts (NOT
                                       the same thing as one experiment's
                                       internal path validation -- that check
                                       only ever compared paths WITHIN a
                                       single ExperimentSpec)
  16.1.3 prerequisite composition  -> merge declared prerequisites, refuse on
                                       incompatible values for the same field
  16.1.4 mutation planning         -> deterministic (sorted) ordering, no plan
                                       construction touches Serum
  16.1.5 canonicalization          -> NOT reinvented: harness.run() already
                                       applies pathmerge sparse/list semantics
                                       and tolerant_equal persistence
                                       comparison; this module never duplicates
                                       that
  16.1.6/16.1.7 construction+verify -> ONE ExperimentSpec built from the
                                       accepted plan, executed by the EXISTING
                                       harness.run() -- load, runtime
                                       verification, persistence, and
                                       measurement all come from that single
                                       call, not from compiler-specific logic
  16.1.8 structured refusal        -> DryRunResult always carries the
                                       underlying reason/detail

Dry-run first (plan -> prove internally safe), execute second: nothing in
dry_run() touches Serum. Only construct_and_verify() does, and only after a
dry run has ACCEPTed.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..pathmerge import path_relationship_conflicts, MUTATION
from ..evidence import admission as adm
from ..evidence import harness
from ..evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                             MeasurementPlan, TargetSpec, CONTROLLED_MULTI_FIELD)
from . import context as ctx_mod

REFUSED_ADMISSION = "admission_refused"
REFUSED_NOT_COMPOSABLE = "capability_not_single_field_composable"
REFUSED_CROSS_CONTRACT_CONFLICT = "cross_contract_conflict"
REFUSED_PREREQUISITE_INCOMPATIBLE = "incompatible_prerequisites"
REFUSED_CONTEXT_NOT_SATISFIED = "CONTEXT_NOT_SATISFIED"  # 16.3.4
ACCEPT = "ACCEPT"

# 16.5.6: Execution mode -- declared before any construction, carried in result.
# WITNESS_MODE    : mutation values come from the CapabilityContract's own evidence
#                   (the witness experiment's stored value). Zero caller input.
# STRUCTURAL_BIND : mutation values come from the CALLER, validated by structural
#                   admission before entering the plan. The resulting EvidenceRecord
#                   is a fresh observation; causal status is NEVER inherited from
#                   the witness contract (they measured a different value).
WITNESS_MODE = "WITNESS_MODE"
STRUCTURAL_BIND_MODE = "STRUCTURAL_BIND_MODE"


@dataclass(frozen=True)
class DryRunResult:
    accepted: bool
    reason: str
    detail: str
    admissions: Tuple[Any, ...] = ()
    mutation_plan: Tuple[Tuple[str, Any], ...] = ()
    merged_prerequisites: Tuple[Dict[str, Any], ...] = ()
    predicted_paths: Tuple[str, ...] = ()
    execution_mode: str = WITNESS_MODE  # 16.5.6: always declared in result

    def __bool__(self):
        return self.accepted


def dry_run(targets: List[str], contracts: Dict[Tuple[str, str], Any], *,
           required_causal_map: Optional[Dict[str, bool]] = None,
           proposed_prerequisites_verified: Optional[Dict[str, bool]] = None,
           base_body: Optional[Dict[str, Any]] = None,
           requested_value_overrides: Optional[Dict[str, Any]] = None) -> DryRunResult:
    """Pre-execution validation: admission, context, composition (16.1.1-16.1.4, 16.3.4).

    Pure Python operation; NO Serum interaction. Touches nothing outside in-memory
    data structures. Only construct_and_verify() actually executes Serum.

    Validation pipeline (in order; first failure returns REFUSED result):
    1. Exact semantic target admission (16.1.1): must be EXACT capability_key.
       No fuzzy/family matching. Unknown targets are refused with reason "unknown_no_contract".
    2. Context satisfaction (16.3.4): mutation paths must have required containers.
       base_body is inspected only; not mutated.
    3. Cross-contract conflicts (16.1.2): pairwise path relationship checks.
       Same conflicts() logic used inside ExperimentSpec.validate() but applied across
       N separate contracts here (not just within one spec).
    4. Prerequisite composition (16.1.3): union with conflict detection.
       If two contracts require the same field at different values, refused.
    5. Mutation plan (16.1.4): deterministic sorted ordering.

    Execution mode (16.5.7):
    - WITNESS_MODE: all values come from contract.witness_value (caller-supplied overrides).
    - STRUCTURAL_BIND_MODE: values come from requested_value_overrides (STRUCTURAL_BIND_MODE).
      The resulting plan's values will differ from witness values; the EvidenceRecord
      from construct_and_verify will be a FRESH observation, not causal claim inheritance.

    Args:
        targets: exact semantic capability keys (e.g., "oscillator_field_OSC-VOLUME").
        contracts: dict of (defid, condition) -> CapabilityContract.
        required_causal_map: optional {target: bool} to enforce CAUSAL_VERIFIED.
        proposed_prerequisites_verified: optional {field_path: bool/value} for prerequisite
          checking. If None and base_body supplied, extracted value-aware from base_body.
        base_body: optional plain dict to inspect for context satisfaction.
        requested_value_overrides: optional {capability_key: value} for STRUCTURAL_BIND_MODE.
          Caller must run structural_admit() BEFORE calling dry_run; this function only
          records the override in the plan (no validation here).

    Returns:
        DryRunResult.accepted == True if all gates pass (ready for construct_and_verify).
        DryRunResult.accepted == False + reason/detail if any gate fails (refuse execution).
        Even on REFUSED result, all intermediate data (admissions, predicted_paths)
        is carried for error diagnostics.
    """
    required_causal_map = required_causal_map or {}

    # 16.5.51: Value-aware prerequisite verification. If base_body is supplied,
    # extract ACTUAL values for all prerequisites (value-sensitive or not) and
    # build a value-bearing dict. If proposed_prerequisites_verified is already
    # supplied by caller, use it as-is (backward compatible). Otherwise, derive
    # from base_body.
    value_bearing_prerequisites_verified: Optional[Dict[str, Any]] = None
    if base_body is not None and proposed_prerequisites_verified is None:
        value_bearing_prerequisites_verified = {}
        # Collect all unique prerequisite field_paths across all contracts
        for contract in contracts.values():
            if contract.prerequisites:
                for p in contract.prerequisites:
                    field_path = p["field_path"]
                    if field_path not in value_bearing_prerequisites_verified:
                        # Extract actual value from base_body
                        actual_value = ctx_mod.extract_prerequisite_value(base_body, field_path)
                        value_bearing_prerequisites_verified[field_path] = actual_value

    # Use value-bearing dict if derived; fall back to caller-supplied or None
    pp_verified = value_bearing_prerequisites_verified if value_bearing_prerequisites_verified is not None else proposed_prerequisites_verified

    admissions = []

    # 16.1.1: contract admission -- exact, per-target, no fuzzy matching
    # (inherits admission.py's scope guard: an unadmitted target refuses here,
    # it does not fall through to "try it anyway").
    for t in targets:
        r = adm.admit(contracts, t, required_causal=required_causal_map.get(t, False),
                      proposed_prerequisites_verified=pp_verified)
        admissions.append(r)
        if not r.admitted:
            return DryRunResult(False, REFUSED_ADMISSION,
                                "target %r refused at admission: reason=%s detail=%s"
                                % (t, r.reason, r.detail), admissions=tuple(admissions))

    entries = []  # (target, mutation_path, mutation_value)
    for r in admissions:
        c = r.contract
        path = c.scope.get("mutation_target_path")
        value = c.scope.get("mutation_value_used")
        if path is None:
            return DryRunResult(False, REFUSED_NOT_COMPOSABLE,
                                "target %r has no single recorded mutation path in its contract "
                                "(e.g. a controlled_multi_field or route-shaped capability) -- "
                                "the minimal kernel only composes single-field contracts"
                                % c.target, admissions=tuple(admissions))
        entries.append((c.target, path, value))

    # 16.3.4: context admission -- checked BEFORE any conflict/mutation-plan
    # work, and entirely against base_body (no Serum touch). A capability
    # whose mutation path structurally requires a container that base_body
    # doesn't have refuses here with the exact missing container/key, never
    # as a runtime PathError during construction.
    resolved_entries = []  # (target, resolved_path, value)
    if base_body is not None:
        for target, path, value in entries:
            contract = next(r.contract for r in admissions if r.contract.target == target)
            required_ctx = ctx_mod.derive_required_context(path, contract.status, base_body)
            if required_ctx is None:
                resolved_entries.append((target, path, value))
                continue
            if not required_ctx.satisfied_by(base_body):
                return DryRunResult(False, REFUSED_CONTEXT_NOT_SATISFIED,
                                    "target %r requires container %r to contain an element with "
                                    "key %r, which base_body does not have -- refusing before any "
                                    "Serum interaction" % (target, required_ctx.container_path,
                                                           required_ctx.element_key),
                                    admissions=tuple(admissions))
            resolved_path = required_ctx.resolve_path(path, base_body)
            resolved_entries.append((target, resolved_path, value))
    else:
        resolved_entries = entries
    entries = resolved_entries

    # 16.1.2: cross-contract conflict analysis. Deliberately reuses the SAME
    # path_relationship_conflicts() used inside ExperimentSpec.validate() for
    # one spec's own paths -- but applied pairwise ACROSS N separate
    # contracts, which validate() never does (it only ever saw one spec).
    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            t1, p1, _ = entries[i]
            t2, p2, _ = entries[j]
            if path_relationship_conflicts(p1, MUTATION, p2, MUTATION):
                return DryRunResult(False, REFUSED_CROSS_CONTRACT_CONFLICT,
                                    "contracts %r and %r have conflicting mutation paths "
                                    "(%r vs %r) -- cannot safely compose into one patch"
                                    % (t1, t2, p1, p2), admissions=tuple(admissions))

    # 16.1.3: prerequisite composition -- union, refuse on same-field disagreement
    merged: Dict[str, Any] = {}
    for r in admissions:
        for p in r.contract.prerequisites:
            fp, dv = p["field_path"], p["declared_value"]
            if fp in merged and merged[fp] != dv:
                return DryRunResult(False, REFUSED_PREREQUISITE_INCOMPATIBLE,
                                    "prerequisite %r is required as %r by one contract and "
                                    "%r by another in this composition -- incompatible"
                                    % (fp, merged[fp], dv), admissions=tuple(admissions))
            merged[fp] = dv

    # 16.1.4 / 16.5.7: deterministic mutation plan -- sorted so the same target
    # set always produces the same plan, independent of caller-supplied ordering.
    # When requested_value_overrides provides a value for a capability_key, that
    # value replaces the witness value (STRUCTURAL_BIND_MODE). The caller must
    # have run structural_admit() and confirmed ACCEPT before supplying overrides.
    rvo = requested_value_overrides or {}
    plan = tuple(sorted(
        ((path, rvo.get(target, value)) for target, path, value in entries),
        key=lambda kv: kv[0],
    ))
    predicted_paths = tuple(p for p, _ in plan)
    execution_mode = (
        STRUCTURAL_BIND_MODE
        if rvo and any(target in rvo for target, _, _ in entries)
        else WITNESS_MODE
    )

    return DryRunResult(True, ACCEPT,
                        "dry run accepted: %d contracts, %d mutations, no cross-contract "
                        "conflicts, no incompatible prerequisites [mode=%s]"
                        % (len(entries), len(plan), execution_mode),
                        admissions=tuple(admissions), mutation_plan=plan,
                        merged_prerequisites=tuple(
                            {"field_path": k, "declared_value": v, "must_hold_identical": True}
                            for k, v in sorted(merged.items())),
                        predicted_paths=predicted_paths,
                        execution_mode=execution_mode)


def construct_and_verify(dry_run_result: DryRunResult, *, experiment_id: str,
                         measure_overall_rms: bool = True, skeleton=None,
                         baseline_overrides: Optional[List] = None):
    """Execution: build ExperimentSpec from accepted plan and run harness (16.1.6/16.1.7).

    This is the ONLY function in the compiler that touches Serum. Calls harness.run()
    which produces an EvidenceRecord with execution observation (load/persistence/causal gates).

    Precondition: dry_run_result.accepted == True. Raises ValueError if not.
    This enforces "dry_run BEFORE execute" discipline: no construction happens without
    a prior ACCEPT, making failures auditable and repeatable.

    Execution flow:
    1. Assemble ONE ExperimentSpec from dry_run_result.mutation_plan (+ prerequisites, overrides).
    2. Call harness.run(spec, skeleton=skeleton).
       - harness builds two arms (control=skeleton, treatment=skeleton+mutations).
       - renders both with DawDreamer (audio output).
       - measures gates: load_status (did render), persistence_status (did store),
         causal_measurements (did we observe effect via measurement).
    3. Return EvidenceRecord carrying all gates and measurement snapshots.

    Gate semantics (from returned EvidenceRecord):
    - load_status (PASS/FAIL/NOT_RUN): Did Serum render the spec and produce audio?
    - persistence_status (PASS/FAIL/NOT_RUN): Did mutations persist to saved state?
    - causal_status (EFFECT_OBSERVED | NO_OBSERVED_EFFECT | WRONG_DIRECTION | NOT_RUN):
      Did overall_rms_db (or other measurement) change in the expected direction?
    - measurement: causal_measurements[0] carries the observation
      (baseline, treatment, delta, expected_direction, observed_direction, threshold).

    CRITICAL SEMANTIC NOTES:
    - These gates observe THIS EXECUTION ONLY. They do NOT constitute capability claims.
    - load_status PASS = Serum accepted the spec. Does NOT prove field works.
    - persistence_status PASS = value was stored. Does NOT prove field has effect.
    - causal_status EFFECT_OBSERVED = overall_rms changed. Does NOT prove field caused it.
      Field causality requires CapabilityContract evidence + producer grounding logic.
    - measurement dict is execution snapshot, not capability claim.
      Carries measurement_condition_signature and measurement_definition_id for reproducibility.

    Control vs Treatment:
    - control: skeleton (baseline state, no mutations applied).
    - treatment: skeleton + all mutations from mutation_plan (test state).
    Both arms have prerequisites applied identically, so mutations are the ONLY difference.
    This isolation is why harness.run() can attribute measurement differences to mutations.

    Args:
        dry_run_result: DryRunResult from dry_run() with accepted==True.
        experiment_id: unique identifier for this execution (for EvidenceRecord).
        measure_overall_rms: if True, add one MeasurementPlan for overall_rms_db metric.
        skeleton: raw VST3 processor state [meta, body]. If None, captured from live Serum.
        baseline_overrides: list of path->value overrides applied to BOTH control and treatment.

    Returns:
        EvidenceRecord: complete observation of this execution, including all gates and
        measurement snapshots. Carries no interpretation (success/failure verdict is at
        producer/knowledge loop layer, not here).

    Raises:
        ValueError: if dry_run_result.accepted == False (construction forbidden without ACCEPT).
    """
    if not dry_run_result.accepted:
        raise ValueError("construct_and_verify called on a REFUSED dry run "
                         "(reason=%s): %s" % (dry_run_result.reason, dry_run_result.detail))

    mutations = [Mutation(path, value, "compiler: composed from an admitted CapabilityContract")
                for path, value in dry_run_result.mutation_plan]
    prerequisites = [Prerequisite(p["field_path"], p["declared_value"], p["must_hold_identical"])
                     for p in dry_run_result.merged_prerequisites]

    measurement_plans = []
    if measure_overall_rms:
        measurement_plans.append(MeasurementPlan(
            metric="overall_rms_db", target=TargetSpec("compiled_patch", None, None),
            expected_direction="none", threshold=0.5,
            stimulus=Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0),
            kernel_artifact="overall_rms_db.py"))

    spec = ExperimentSpec(
        experiment_id=experiment_id, mutations=mutations, prerequisites=prerequisites,
        isolation_level=CONTROLLED_MULTI_FIELD,
        claim_subject="compiled_patch:%s" % experiment_id, claim_predicate="constructible",
        baseline_overrides=list(baseline_overrides or []),
        measurement_plans=measurement_plans,
        notes="compiler-constructed patch composed of %d admitted capabilities" % len(mutations),
    )
    return harness.run(spec, skeleton=skeleton)


def evaluate_construction_goal(rec) -> Dict[str, Any]:
    """16.2's falsifiable acceptance criteria, read directly off the
    EvidenceRecord the unified verification path already produced -- no
    separate pass/fail logic invented beyond what the gates already say."""
    gate = rec.gate_completeness()
    load_pass = gate.get("load") == "PASS"
    persistence_pass = rec.persistence_observation.get("status") == "PASS"
    measurable_diff = any(m.status == "EFFECT_OBSERVED" for m in rec.causal_measurements)
    return {
        "load_pass": load_pass,
        "persistence_pass": persistence_pass,
        "measurable_difference_from_skeleton": measurable_diff,
        "state_matches_intent": rec.state_observation.get("matches_intent"),
        "overall_pass": load_pass and persistence_pass and measurable_diff
                        and bool(rec.state_observation.get("matches_intent")),
    }
