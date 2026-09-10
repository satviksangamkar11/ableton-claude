"""16.5.69.2: A3 H1 experiment test plans.

Design-only module.

This module:
    - creates ExperimentSpec objects
    - defines H1 pilot mutation vectors
    - does not execute Serum
    - does not resolve VST3 indices
    - does not evaluate EvidenceRecords

H1 deliberately covers three different mutation classes:
    BOOLEAN (OSC1.Enable)
    ENUM (Filter.Type)
    SCALAR (Filter.Resonance)

Concrete state paths follow existing evidence harness conventions.
"""

from __future__ import annotations

from typing import Any

# Imports match existing evidence experiments
from serum2.evidence.spec import ExperimentSpec, Mutation, Prerequisite, SINGLE_FIELD


# ---------------------------------------------------------------------------
# Canonical H1 pilot semantic identities
# ---------------------------------------------------------------------------

H1_BOOLEAN = "OSC1.Enable"
H1_ENUM = "Filter.Type"
H1_SCALAR = "Filter.Cutoff"

# Concrete Serum state paths (derived from phase 1 + existing experiments)
H1_BOOLEAN_PATH = "VoiceOsc0.plainParams.kParamEnable"
H1_ENUM_PATH = "VoiceFilter0.plainParams.kParamType"
H1_SCALAR_PATH = "VoiceFilter0.plainParams.kParamCutoff"


# ---------------------------------------------------------------------------
# Small helper
# ---------------------------------------------------------------------------

def _build_h1_spec(
    experiment_id: str,
    semantic_id: str,
    target_path: str,
    value: Any,
) -> ExperimentSpec:
    """Build and validate a one-mutation H1 ExperimentSpec."""

    spec = ExperimentSpec(
        experiment_id=experiment_id,
        mutations=[
            Mutation(
                target_path=target_path,
                value=value,
                provenance="A3_H1_PILOT",
            )
        ],
        prerequisites=[],
        isolation_level=SINGLE_FIELD,
        claim_subject=semantic_id,
        claim_predicate="mutation_generation",
    )

    return spec


# ---------------------------------------------------------------------------
# BOOLEAN
# ---------------------------------------------------------------------------

def build_boolean_plan() -> ExperimentSpec:
    """H1 BOOLEAN pilot: OSC1.Enable (VoiceOsc0.plainParams.kParamEnable).

    The semantic target is OSC1.Enable.
    The concrete state path is VoiceOsc0.plainParams.kParamEnable.
    """

    return _build_h1_spec(
        experiment_id="A3-H1-BOOLEAN-OSC1-ENABLE",
        semantic_id=H1_BOOLEAN,
        target_path=H1_BOOLEAN_PATH,
        value=True,
    )


# ---------------------------------------------------------------------------
# ENUM
# ---------------------------------------------------------------------------

def build_enum_plan() -> ExperimentSpec:
    """H1 ENUM pilot: Filter.Type (VoiceFilter0.plainParams.kParamType).

    The semantic target is Filter.Type.
    The concrete state path is VoiceFilter0.plainParams.kParamType.

    Value "BP12" is a real enum value from evidence corpus.
    """

    return _build_h1_spec(
        experiment_id="A3-H1-ENUM-FILTER-TYPE",
        semantic_id=H1_ENUM,
        target_path=H1_ENUM_PATH,
        value="BP12",
    )


# ---------------------------------------------------------------------------
# SCALAR
# ---------------------------------------------------------------------------

def build_scalar_plan() -> ExperimentSpec:
    """H1 SCALAR pilot: Filter.Cutoff (VoiceFilter0.plainParams.kParamCutoff).

    The semantic target is Filter.Cutoff.
    The concrete state path is VoiceFilter0.plainParams.kParamCutoff.

    Value 5000.0 is mid-high cutoff frequency for clarity.
    """

    return _build_h1_spec(
        experiment_id="A3-H1-SCALAR-FILTER-CUTOFF",
        semantic_id=H1_SCALAR,
        target_path=H1_SCALAR_PATH,
        value=5000.0,
    )


# ---------------------------------------------------------------------------
# Pilot collection
# ---------------------------------------------------------------------------

def build_h1_pilot_plans() -> list[ExperimentSpec]:
    """Return the fixed three-experiment H1 pilot set.

    Ordering is intentional:
        1. BOOLEAN
        2. ENUM
        3. SCALAR
    """

    plans = [
        build_boolean_plan(),
        build_enum_plan(),
        build_scalar_plan(),
    ]

    experiment_ids = [p.experiment_id for p in plans]

    if len(set(experiment_ids)) != len(experiment_ids):
        raise AssertionError(
            "H1 pilot experiment IDs must be unique: %r" % experiment_ids
        )

    return plans


# ---------------------------------------------------------------------------
# Design-only self-test
# ---------------------------------------------------------------------------

def self_test() -> None:
    """Validate H1 plan construction without executing anything."""

    plans = build_h1_pilot_plans()

    assert len(plans) == 3, "Expected exactly three H1 pilot plans."

    assert plans[0].claim_subject == H1_BOOLEAN
    assert plans[1].claim_subject == H1_ENUM
    assert plans[2].claim_subject == H1_SCALAR

    for plan in plans:
        assert len(plan.mutations) == 1
        assert plan.mutations[0].provenance == "A3_H1_PILOT"


def main() -> None:
    self_test()
    print("A3 TEST PLANS: PASS (3 H1 pilot plans)")


if __name__ == "__main__":
    main()
