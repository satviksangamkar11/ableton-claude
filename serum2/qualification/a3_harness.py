"""16.5.69.2: A3 qualification harness.

Thin orchestration layer.

Pipeline:

    ResolvedTarget + ExperimentSpec
        -> validate
        -> existing evidence.harness.run()
        -> EvidenceRecord
        -> a3_evaluator.evaluate_record()
        -> MutationReceipt

This module does NOT:
    - execute Serum directly
    - implement a second execution engine
    - mutate state independently
    - perform measurements independently
    - infer VST3 identity from state paths
    - interpret semantic meaning
"""

from __future__ import annotations

from typing import Any

from serum2.evidence import harness as evidence_harness
from serum2.evidence.spec import ExperimentSpec, validate

from serum2.qualification.a3_evaluator import evaluate_record
from serum2.qualification.a3_receipts import MutationReceipt


def qualify_plan(
    spec: ExperimentSpec,
    resolved_target: dict[str, Any],
) -> MutationReceipt:
    """Execute one validated experiment and qualify its EvidenceRecord.

    Args:
        spec: Experiment specification (design layer).
        resolved_target: Qualified target identity from Phase 1 registry.
                        REQUIRED: do not infer from state paths.
    """

    # Design gate.
    validate(spec)

    # Verify resolved target has required fields.
    required_fields = {"semantic_id", "capability_key", "vst3_name", "vst3_index"}
    if not all(field in resolved_target for field in required_fields):
        missing = required_fields - set(resolved_target.keys())
        raise ValueError(
            f"resolved_target missing required fields: {missing}"
        )

    # Single execution authority: the existing evidence harness.
    record = evidence_harness.run(spec)

    # Extract observations from EvidenceRecord.
    state_observation = getattr(record, "state_observation", None) or {}
    persistence_observation = getattr(record, "persistence_observation", None) or {}
    causal_measurements = list(getattr(record, "causal_measurements", []))

    # Evaluate through A3 interpretation layer.
    return evaluate_record(
        experiment_id=record.experiment_id,
        resolved_target=resolved_target,
        state_observation=state_observation,
        persistence_observation=persistence_observation,
        causal_measurements=causal_measurements,
    )


def qualify_plans(
    plans: list[ExperimentSpec],
    resolved_target: dict[str, Any],
) -> list[MutationReceipt]:
    """Execute a sequence of validated experiments with a single resolved target.

    This is a batch runner for multiple plans sharing the same semantic target.
    """

    receipts = []
    for plan in plans:
        receipt = qualify_plan(plan, resolved_target)
        receipts.append(receipt)

    return receipts


def run_h1_pilot(resolved_targets_dict: dict[str, dict[str, Any]]) -> None:
    """Execute H1 pilot with resolved targets from Phase 1 registry."""

    from serum2.qualification.a3_test_plans import build_h1_pilot_plans

    plans = build_h1_pilot_plans()

    for plan in plans:
        semantic_id = plan.claim_subject
        if semantic_id not in resolved_targets_dict:
            raise ValueError(
                f"No resolved target for {semantic_id}. "
                f"Available: {sorted(resolved_targets_dict.keys())}"
            )

        resolved_target = resolved_targets_dict[semantic_id]
        receipt = qualify_plan(plan, resolved_target)

        print(f"\n{semantic_id}:")
        print(f"  Generation: {receipt.generation.status}")
        print(f"  Behavior: {receipt.behavior.status}")
        print(f"  Collateral: {receipt.collateral.status}")
        print(f"  Persistence: {receipt.persistence.overall.status}")
        print(f"  Restoration: {receipt.restoration.status}")


def main() -> None:
    """Entry point intentionally disabled until orchestration is verified."""

    raise RuntimeError(
        "H1 execution is blocked pending a3_harness_selftest verification. "
        "Run the orchestration boundary tests before real Serum execution."
    )


if __name__ == "__main__":
    main()
