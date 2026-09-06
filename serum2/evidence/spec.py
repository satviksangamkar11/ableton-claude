"""ExperimentSpec: a test specification, not a result.

Two separate protections, deliberately NOT collapsed into one:

  DESIGN VALIDATION    (here)          -- was this experiment designed correctly?
  RUNTIME VERIFICATION (harness)       -- did execution match the specification?

A spec declaring `must_hold_identical` is a claim about intent. Only the harness,
by reading actual values back from both arms, can establish it actually held.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .canonical import (experiment_condition_signature,
                        measurement_condition_signature,
                        digest, is_canonically_serializable)
from ..pathmerge import path_relationship_conflicts, MUTATION, SHARED_CONTEXT

SINGLE_FIELD = "single_field"
CONTROLLED_MULTI_FIELD = "controlled_multi_field"
PRODUCER_UNCONTROLLED = "producer_uncontrolled"

ISOLATION_LEVELS = (SINGLE_FIELD, CONTROLLED_MULTI_FIELD, PRODUCER_UNCONTROLLED)


@dataclass(frozen=True)
class Mutation:
    target_path: str
    value: Any
    provenance: str


@dataclass(frozen=True)
class Prerequisite:
    """DECLARED intent only. `must_hold_identical` says the experiment intends
    this condition to be applied identically to both arms; whether it actually
    did is established at runtime, not here."""
    field_path: str
    declared_value: Any
    must_hold_identical: bool = True


@dataclass(frozen=True)
class Stimulus:
    note: int
    velocity: int
    note_len: float
    render_seconds: float
    tail_start: Optional[float] = None

    def as_dict(self):
        return {
            "note": self.note,
            "velocity": self.velocity,
            "note_len": self.note_len,
            "render_seconds": self.render_seconds,
            "tail_start": self.tail_start,
        }


@dataclass(frozen=True)
class TargetSpec:
    """Structured measurement target. A flat string cannot express module and
    parameter, and identity built from it silently differs from a structured
    one -- which is exactly how a same-kernel comparison was refused."""
    field_path: str
    module: Optional[str] = None
    parameter: Optional[str] = None


@dataclass(frozen=True)
class MeasurementPlan:
    """An assay criterion, with its OWN stimulus.

    E3 proved measurements within one experiment can legitimately need
    different stimuli (sustained note for centroid, pluck for delay tail).
    `threshold` is a measurement decision rule -- never itself a fact about
    Serum. The observed delta belongs to the record."""
    metric: str
    target: TargetSpec
    expected_direction: str      # "increase" | "decrease" | "none"
    threshold: float
    stimulus: Stimulus
    # Archived kernel artifact under evidence/kernels/. Identity of HOW the
    # scalar is derived; None falls back to the measure.py registry.
    kernel_artifact: Optional[str] = None


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_id: str
    mutations: List[Mutation]
    prerequisites: List[Prerequisite]
    isolation_level: str
    claim_subject: str
    claim_predicate: str
    # Applied to BOTH arms, identically, BEFORE mutations. NOT mutations: they
    # define the shared starting state, so they do not count toward the
    # isolation-level mutation-count constraint. Use dotted target_path
    # ("Env0.plainParams.kParamSustain") so an override and a mutation can
    # share a body key without either clobbering the other's sibling field.
    baseline_overrides: List[Mutation] = field(default_factory=list)
    measurement_plans: List[MeasurementPlan] = field(default_factory=list)
    notes: str = ""
    # "NUMERIC_CLAMP_RANGE": this experiment probes a structural boundary.
    # Only when set does the harness populate structural_observation on the record.
    # A plain persistence failure on a non-clamp experiment NEVER becomes a bound.
    probe_semantics: Optional[str] = None

    def experiment_condition_signature(self):
        """Shared context: prerequisites AND baseline_overrides -- both define
        what both arms have in common, so both belong in condition identity.
        Stable when measurements change."""
        return experiment_condition_signature(self.prerequisites, self.baseline_overrides)

    def measurement_condition_signatures(self):
        exp_sig = self.experiment_condition_signature()
        return [measurement_condition_signature(exp_sig, mp.stimulus.as_dict())
                for mp in self.measurement_plans]

    def mutation_signature(self):
        return digest(sorted([m.target_path, m.value] for m in self.mutations))


class ValidityError(Exception):
    pass


def validate(spec: ExperimentSpec):
    """DESIGN validation only. Does not and cannot establish that execution
    matched the design -- see harness runtime verification for that."""
    problems = []

    if spec.isolation_level not in ISOLATION_LEVELS:
        problems.append("unknown isolation_level %r" % (spec.isolation_level,))

    n = len(spec.mutations)
    if n == 0:
        problems.append("no mutations declared")
    if spec.isolation_level == SINGLE_FIELD and n != 1:
        problems.append(
            "isolation_level=single_field permits exactly 1 mutation, %d declared "
            "(use controlled_multi_field for interaction experiments)" % n
        )

    targets = [m.target_path for m in spec.mutations]
    if len(set(targets)) != len(targets):
        problems.append("duplicate mutation targets: %r" % (targets,))
    for m in spec.mutations:
        if not m.target_path or not m.target_path.strip():
            problems.append("mutation with empty target_path")
        if not is_canonically_serializable(m.value):
            problems.append(
                "mutation %r has a non-canonically-serializable value" % (m.target_path,)
            )

    # baseline_overrides: shared context, NOT mutations, NOT counted toward
    # isolation. But a path collision with a mutation would make the
    # control/treatment diff ambiguous -- exactly what single_field promises
    # NOT to be. Checked structurally here, not left to a comment.
    override_targets = [m.target_path for m in spec.baseline_overrides]
    if len(set(override_targets)) != len(override_targets):
        problems.append("duplicate baseline_override targets: %r" % (override_targets,))
    for m in spec.baseline_overrides:
        if not m.target_path or not m.target_path.strip():
            problems.append("baseline_override with empty target_path")
        if not is_canonically_serializable(m.value):
            problems.append(
                "baseline_override %r has a non-canonically-serializable value" % (m.target_path,)
            )
    # Directional, operation-aware conflict rule (NOT a blanket prefix
    # exception): shared-context ops (baseline_override / body: prerequisite)
    # execute before mutations, so a shared-context path may be a strict
    # PREFIX of a mutation path safely -- the mutation resolves within the
    # already-built structure. Every other same-key relationship still
    # conflicts. See pathmerge.path_relationship_conflicts for the full rule.
    for mo in spec.baseline_overrides:
        for mm in spec.mutations:
            if path_relationship_conflicts(mo.target_path, SHARED_CONTEXT,
                                           mm.target_path, MUTATION):
                problems.append(
                    "baseline_override %r conflicts with mutation %r -- the "
                    "control/treatment diff would not be provably one field"
                    % (mo.target_path, mm.target_path)
                )
    for pr in spec.prerequisites:
        if not pr.field_path.startswith("body:"):
            continue
        pr_path = pr.field_path.split("body:", 1)[1]
        for mm in spec.mutations:
            if path_relationship_conflicts(pr_path, SHARED_CONTEXT,
                                           mm.target_path, MUTATION):
                problems.append(
                    "prerequisite %r conflicts with mutation %r -- same latent "
                    "clobbering risk as a baseline_override/mutation collision"
                    % (pr.field_path, mm.target_path)
                )
        for mo in spec.baseline_overrides:
            if path_relationship_conflicts(pr_path, SHARED_CONTEXT,
                                           mo.target_path, SHARED_CONTEXT):
                problems.append(
                    "prerequisite %r conflicts with baseline_override %r -- "
                    "two shared-context operations may not overlap"
                    % (pr.field_path, mo.target_path)
                )

    for p in spec.prerequisites:
        if not p.field_path or not p.field_path.strip():
            problems.append("prerequisite with empty field_path")
        if not is_canonically_serializable(p.declared_value):
            problems.append(
                "prerequisite %r has a non-canonically-serializable value" % (p.field_path,)
            )

    # Measurement plans are OPTIONAL: structural/persistence-only assays are
    # legitimate. What evidence a CLAIM requires is ClaimDefinition's business,
    # not the spec's. A spec with no plans yields causal = NOT_RUN.
    for mp in spec.measurement_plans:
        if mp.expected_direction not in ("increase", "decrease", "none"):
            problems.append("invalid expected_direction %r" % (mp.expected_direction,))
        if mp.threshold < 0:
            problems.append("negative threshold for metric %r" % (mp.metric,))
    for mp in spec.measurement_plans:
        if mp.stimulus is None:
            problems.append("measurement plan %r has no stimulus" % (mp.metric,))
        if not mp.kernel_artifact:
            problems.append(
                "measurement plan %r has no kernel_artifact -- a live measurement "
                "must carry explicit identity; falling back to METRICS[metric] "
                "silently produces evidence with measurement_definition_id=None, "
                "which cannot be admitted into any comparability cohort" % (mp.metric,)
            )

    if problems:
        raise ValidityError("; ".join(problems))
    return True


def field_attribution_allowed(spec: ExperimentSpec) -> bool:
    """Only single_field evidence attributes an effect to one specific field.
    controlled_multi_field supports INTERACTION claims only; producer_uncontrolled
    supports no attribution at all."""
    return spec.isolation_level == SINGLE_FIELD


def interaction_attribution_allowed(spec: ExperimentSpec) -> bool:
    return spec.isolation_level in (SINGLE_FIELD, CONTROLLED_MULTI_FIELD)
