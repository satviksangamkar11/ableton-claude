"""16.5.69.2-A3-15: Restoration Lifecycle Harness

Runs restoration independently from persistence.

Sequence:
  1. Build baseline state (no mutations)
  2. Apply mutation
  3. Verify mutation succeeded (generation gate)
  4. Restore baseline (rebuild and resave)
  5. Verify target value matches baseline
  6. Verify no collateral changes

Returns RestorationObservation (independent of P1/P2/P3).
"""

from __future__ import annotations

from typing import Any
import copy

from serum2 import pathmerge

from serum2.qualification.a3_restoration_observation import (
    create_restoration_observation,
    RESTORATION_NOT_RUN,
)


def run_restoration_test(
    *,
    experiment_id: str,
    target_path: str,
    mutation_value: Any,
    skeleton: tuple[dict, dict],
    spec: Any,
) -> dict[str, Any]:
    """Run restoration lifecycle test.

    Sequence:
      1. Build baseline (no mutations)
      2. Apply mutation
      3. Verify mutation
      4. Rebuild baseline
      5. Verify target matches baseline
      6. Verify collateral matches baseline

    Returns dict that can be converted to RestorationObservation.
    """

    try:
        from serum2.evidence.harness import build_arm

        # Build baseline and treatment arms
        meta_c, body_c = build_arm(skeleton, spec, apply_mutations=False)
        meta_t, body_t = build_arm(skeleton, spec, apply_mutations=True)

        # Read baseline value
        baseline_value = pathmerge.read_path_value(body_c, target_path)

        # Read mutated value
        value_after_mutation = pathmerge.read_path_value(body_t, target_path)

        # Verify mutation changed the value
        mutation_matched = pathmerge.tolerant_equal(value_after_mutation, mutation_value)
        if not mutation_matched:
            return {
                "status": "FAIL",
                "reason": "Mutation did not match declared value",
                "baseline_value": baseline_value,
                "value_after_mutation": value_after_mutation,
                "target_restored": False,
                "collateral_restored": False,
            }

        # Verify mutation changed from baseline
        mutation_different = not pathmerge.tolerant_equal(value_after_mutation, baseline_value)
        if not mutation_different:
            return {
                "status": "FAIL",
                "reason": "Mutation did not differ from baseline",
                "baseline_value": baseline_value,
                "value_after_mutation": value_after_mutation,
                "target_restored": False,
                "collateral_restored": False,
            }

        # Restore: rebuild baseline state
        meta_restore, body_restore = build_arm(skeleton, spec, apply_mutations=False)

        # Read restored value
        value_after_restore = pathmerge.read_path_value(body_restore, target_path)

        # Verify restoration: target should match baseline
        target_restored = pathmerge.tolerant_equal(value_after_restore, baseline_value)

        # Verify collateral: entire baseline should match
        collateral_restored = (body_restore == body_c)

        # Overall status
        status = "PASS" if (target_restored and collateral_restored) else "FAIL"

        return {
            "status": status,
            "reason": (
                "Restoration successful" if status == "PASS"
                else "Restoration failed (target or collateral mismatch)"
            ),
            "baseline_value": baseline_value,
            "value_after_mutation": value_after_mutation,
            "value_after_restore": value_after_restore,
            "target_restored": target_restored,
            "collateral_restored": collateral_restored,
            "mutation_differed": mutation_different,
            "experiment_id": experiment_id,
            "target_path": target_path,
        }

    except Exception as e:
        import traceback
        return {
            "status": "FAIL",
            "reason": "Restoration lifecycle error: {}".format(str(e)),
            "experiment_id": experiment_id,
            "target_path": target_path,
            "target_restored": False,
            "collateral_restored": False,
            "error_traceback": traceback.format_exc(),
        }


def qualify_with_restoration(
    *,
    experiment_id: str,
    resolved_target: dict[str, Any],
    spec: Any,
    skeleton: tuple[dict, dict],
) -> dict[str, Any]:
    """Run restoration lifecycle test on the specification.

    Args:
        experiment_id: Experiment ID
        resolved_target: Resolved target metadata
        spec: ExperimentSpec
        skeleton: VST3 skeleton (meta, body)

    Returns dict with restoration_observation and details.
    """

    if not spec.mutations:
        return {
            "experiment_id": experiment_id,
            "error": "No mutations in spec",
            "restoration_observation": RESTORATION_NOT_RUN,
        }

    mutation = spec.mutations[0]
    target_path = mutation.target_path
    mutation_value = mutation.value

    # Run restoration test
    result_dict = run_restoration_test(
        experiment_id=experiment_id,
        target_path=target_path,
        mutation_value=mutation_value,
        skeleton=skeleton,
        spec=spec,
    )

    # Convert to observation
    restoration_obs = create_restoration_observation(
        status=result_dict.get("status", "NOT_RUN"),
        reason=result_dict.get("reason"),
        baseline_value=result_dict.get("baseline_value"),
        value_after_mutation=result_dict.get("value_after_mutation"),
        value_after_restore=result_dict.get("value_after_restore"),
        target_restored=result_dict.get("target_restored", False),
        collateral_restored=result_dict.get("collateral_restored", False),
        details={k: v for k, v in result_dict.items()
                if k not in ["status", "reason", "baseline_value",
                            "value_after_mutation", "value_after_restore",
                            "target_restored", "collateral_restored"]},
    )

    return {
        "experiment_id": experiment_id,
        "target_semantic_id": resolved_target.get("semantic_id"),
        "target_path": target_path,
        "restoration_observation": restoration_obs,
        "result_dict": result_dict,
    }
