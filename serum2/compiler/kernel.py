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
    """16.1.1-16.1.4, plus 16.3.4 (context admission). Touches nothing outside
    pure Python -- no Serum interaction happens in this function; base_body is
    a plain dict the caller supplies (typically the raw skeleton, or a
    caller-constructed context) purely for structural inspection.

    16.5.7: requested_value_overrides maps capability_key -> caller-requested value.
    When a key is present, its value replaces the witness value in the mutation plan
    (STRUCTURAL_BIND_MODE). The caller is responsible for running structural_admit()
    BEFORE calling dry_run; this function only records the override in the plan.
    DryRunResult.execution_mode reports which mode was used.
    """
    required_causal_map = required_causal_map or {}
    admissions = []

    # 16.1.1: contract admission -- exact, per-target, no fuzzy matching
    # (inherits admission.py's scope guard: an unadmitted target refuses here,
    # it does not fall through to "try it anyway").
    for t in targets:
        r = adm.admit(contracts, t, required_causal=required_causal_map.get(t, False),
                      proposed_prerequisites_verified=proposed_prerequisites_verified)
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
    """16.1.6/16.1.7. Builds exactly ONE ExperimentSpec from the accepted plan
    and hands it to the EXISTING harness.run() -- construction (build_arm's
    pathmerge.apply_path_value, which already carries 16.1.5's sparse/list
    semantics) and verification (load/runtime/persistence/measurement gates)
    both come from that single call. This function adds no epistemic logic of
    its own; it only assembles the spec and reports the result.

    control = skeleton (raw, unmutated). treatment = skeleton + full plan.
    Refuses (raises) rather than silently proceeding if called on a REFUSED
    dry run -- construction must never happen without a prior ACCEPT.
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
