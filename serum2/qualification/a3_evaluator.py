"""16.5.69.2: A3 EvidenceRecord evaluator.

Pure qualification logic.

This module NEVER executes Serum, loads plugins, mutates state, or performs
new measurements. It interprets already-produced observation dicts.
"""

from __future__ import annotations

from typing import Any, Sequence

from serum2.qualification.a3_receipts import (
    FAIL,
    NOT_RUN,
    PASS,
    GateResult,
    MutationReceipt,
    PersistenceResult,
    gate_fail,
    gate_not_run,
    gate_pass,
)


def evaluate_generation(
    state_observation: dict[str, Any],
) -> GateResult:
    """Evaluate generation from state observation.

    Generation is qualified only when:
      1. declared mutation was reflected in the state diff
      2. fine-grained target changed
    """

    if not state_observation:
        return gate_not_run("No state observation available", details={})

    status = state_observation.get("status")

    if status == PASS and state_observation.get("matches_intent") is True:
        return gate_pass(
            "State observation matches declared mutation intent.",
            details={
                "top_level_ok": state_observation.get("top_level_ok"),
                "fine_grained_ok": state_observation.get("fine_grained_ok"),
                "diff_keys": state_observation.get("diff_keys", []),
            },
        )

    if status == FAIL:
        return gate_fail(
            "State observation did not match declared mutation intent.",
            details=state_observation,
        )

    return gate_not_run("Generation observation unavailable.")


def evaluate_persistence(
    persistence_observation: dict[str, Any],
) -> PersistenceResult:
    """Evaluate currently available persistence evidence conservatively.

    The current evidence harness exposes one persistence observation.
    It does NOT establish P1/P2/P3 separately.

    Therefore:
      P1/P2/P3 remain NOT_RUN.
      overall reflects the observed persistence result only.
    """

    if not persistence_observation:
        persistence_observation = {}

    observed_status = persistence_observation.get("status", NOT_RUN)

    if observed_status == PASS:
        overall = gate_pass(
            "Persistence check passed (resave/load identity match).",
            details=persistence_observation,
        )
    elif observed_status == FAIL:
        overall = gate_fail(
            "Persistence check failed (resave/load identity mismatch).",
            details=persistence_observation,
        )
    else:
        overall = gate_not_run(
            "Persistence observation unavailable.",
            details=persistence_observation,
        )

    not_run = gate_not_run(
        "P1/P2/P3 lifecycle identity is not separately established "
        "by the current EvidenceRecord."
    )

    return PersistenceResult(
        p1_same_engine=not_run,
        p2_new_instance=not_run,
        p3_fresh_process=not_run,
        overall=overall,
    )


def evaluate_behavior(
    causal_measurements: Sequence[dict[str, Any]],
) -> GateResult:
    """Evaluate causal behavior without collapsing NO_OBSERVED_EFFECT.

    Important: NO_OBSERVED_EFFECT is a behavior result, not a generation failure.
    """

    if not causal_measurements:
        return gate_not_run("No causal measurements were recorded.")

    statuses = [m.get("status") for m in causal_measurements]

    if any(status == "WRONG_DIRECTION" for status in statuses):
        return gate_fail(
            "At least one causal measurement moved in the wrong direction.",
            details={"measurement_statuses": statuses},
        )

    if all(status == "EFFECT_OBSERVED" for status in statuses):
        return gate_pass(
            "All causal measurements observed the expected effect.",
            details={"measurement_statuses": statuses},
        )

    if all(status == "NO_OBSERVED_EFFECT" for status in statuses):
        return gate_fail(
            "No expected causal effect was observed.",
            details={"measurement_statuses": statuses},
        )

    return gate_not_run(
        "Causal measurements produced mixed/inconclusive outcomes.",
        details={"measurement_statuses": statuses},
    )


def evaluate_collateral(
    state_observation: dict[str, Any],
) -> GateResult:
    """Evaluate collateral state changes.

    The current evidence schema records whether the declared state diff
    matches the mutation intent. That is the strongest collateral signal
    currently available.
    """

    if not state_observation:
        return gate_not_run("No state observation available for collateral check.")

    if state_observation.get("status") == PASS:
        return gate_pass(
            "Observed state diff contains only the declared mutation target(s).",
            details={
                "diff_keys": state_observation.get("diff_keys", []),
                "intended_targets": state_observation.get("intended_targets", []),
            },
        )

    if state_observation.get("status") == FAIL:
        return gate_fail(
            "State diff did not match the declared mutation target set.",
            details=state_observation,
        )

    return gate_not_run("Collateral state comparison unavailable.")


def evaluate_restoration() -> GateResult:
    """Restoration is intentionally not claimed yet."""

    return gate_not_run(
        "Formal restoration evidence is not implemented yet."
    )


def evaluate_record(
    experiment_id: str,
    resolved_target: dict[str, Any],
    state_observation: dict[str, Any],
    persistence_observation: dict[str, Any],
    causal_measurements: Sequence[dict[str, Any]],
) -> MutationReceipt:
    """Convert qualification observations into one MutationReceipt."""

    generation = evaluate_generation(state_observation)
    persistence = evaluate_persistence(persistence_observation)
    behavior = evaluate_behavior(causal_measurements)
    collateral = evaluate_collateral(state_observation)
    restoration = evaluate_restoration()

    transport_mutable = generation.status == PASS
    generation_verified = generation.status == PASS

    persistent_p1 = persistence.p1_same_engine.status == PASS
    persistent_p2 = persistence.p2_new_instance.status == PASS
    persistent_p3 = persistence.p3_fresh_process.status == PASS

    collateral_safe = collateral.status == PASS
    behavior_verified = behavior.status == PASS

    notes: list[str] = []

    if behavior.status == FAIL and all(
        m.get("status") == "NO_OBSERVED_EFFECT"
        for m in causal_measurements
    ) and causal_measurements:
        notes.append(
            "Behavior gate failed because NO_OBSERVED_EFFECT was observed; "
            "this does not invalidate generation by itself."
        )

    return MutationReceipt(
        experiment_id=experiment_id,
        semantic_id=resolved_target["semantic_id"],
        capability_key=resolved_target["capability_key"],
        vst3_name=resolved_target["vst3_name"],
        vst3_index=resolved_target["vst3_index"],
        generation=generation,
        persistence=persistence,
        behavior=behavior,
        collateral=collateral,
        restoration=restoration,
        evidence_record_id=experiment_id,
        transport_mutable=transport_mutable,
        generation_verified=generation_verified,
        persistent_p1=persistent_p1,
        persistent_p2=persistent_p2,
        persistent_p3=persistent_p3,
        collateral_safe=collateral_safe,
        behavior_verified=behavior_verified,
        notes=tuple(notes),
    )
