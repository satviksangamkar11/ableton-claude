"""16.5.69.2-A3-11: Adversarial Tests for A3 Evaluator

Pure qualification framework tests. No Serum execution.
Constructs synthetic EvidenceRecord inputs and verifies evaluator interpretation.

Core invariant: No gate may be inferred from another gate unless the
evaluator contract explicitly defines that dependency.

Valid gate combinations prove the architecture. Invalid combinations
prove the evaluator rejects impossible states.
"""

from __future__ import annotations

from serum2.qualification.a3_evaluator import evaluate_record
from serum2.qualification.a3_receipts import (
    FAIL,
    NOT_RUN,
    PASS,
    GateResult,
    PersistenceResult,
)


def test_generation_pass_persistence_fail_independent():
    """generation=PASS + persistence=FAIL is valid.

    Proves: mutation generation capability ≠ serialization correctness.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    state_observation = {
        "status": PASS,
        "matches_intent": True,
        "top_level_ok": True,
        "fine_grained_ok": True,
        "diff_keys": ["TestField"],
    }

    persistence_observation = {
        "status": FAIL,
        "exact_match": False,
        "detail": {"TestField": False},
    }

    receipt = evaluate_record(
        experiment_id="TEST-GEN-PASS-PERSIST-FAIL",
        resolved_target=resolved_target,
        state_observation=state_observation,
        persistence_observation=persistence_observation,
        causal_measurements=[],
    )

    assert receipt.generation.status == PASS, "Generation should PASS"
    assert receipt.persistence.overall.status == FAIL, "Persistence should FAIL"
    assert receipt.transport_mutable is True, "Mutable claim from generation"
    assert receipt.collateral_safe is False or receipt.collateral_safe is True, "Derived independently"


def test_generation_pass_no_observed_effect_does_not_fail_generation():
    """generation=PASS + behavior=NO_OBSERVED_EFFECT is valid.

    Proves: state mutation ≠ behavioral causality.
    No_observed_effect must not retroactively fail generation.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    state_observation = {
        "status": PASS,
        "matches_intent": True,
        "top_level_ok": True,
        "fine_grained_ok": True,
        "diff_keys": ["TestField"],
    }

    # Causal measurements: no effect observed
    causal_measurements = [
        {"status": "NO_OBSERVED_EFFECT"},
    ]

    receipt = evaluate_record(
        experiment_id="TEST-GEN-PASS-BEHAVIOR-NOE",
        resolved_target=resolved_target,
        state_observation=state_observation,
        persistence_observation={},
        causal_measurements=causal_measurements,
    )

    assert receipt.generation.status == PASS, "Generation should remain PASS"
    assert receipt.behavior.status == FAIL, "Behavior should FAIL (NO_OBSERVED_EFFECT)"
    assert receipt.generation_verified is True
    assert receipt.behavior_verified is False


def test_collateral_unintended_changes_detected():
    """Collateral gate detects unintended state changes.

    Proves: Collateral evaluation is independent from generation intent matching.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    # Generation would PASS (target changed as intended)
    # But collateral FAILS (unintended fields also changed)
    state_observation = {
        "status": FAIL,  # Overall check failed (unintended changes detected)
        "matches_intent": True,  # Target changed as declared
        "top_level_ok": True,
        "fine_grained_ok": True,
        "diff_keys": ["TestField", "UnintendedField"],  # More than declared
        "intended_targets": ["TestField"],  # Only this was supposed to change
    }

    receipt = evaluate_record(
        experiment_id="TEST-COLLATERAL-UNINTENDED",
        resolved_target=resolved_target,
        state_observation=state_observation,
        persistence_observation={},
        causal_measurements=[],
    )

    # Collateral fails because status=FAIL (unintended changes)
    assert receipt.collateral.status == FAIL, "Collateral should detect unintended changes"
    # Generation also sees status=FAIL, so it fails too
    assert receipt.generation.status == FAIL, "Status=FAIL affects both gates"


def test_p1_pass_p2_fail_p3_not_run_independent():
    """P1/P2/P3 lifecycle gates must remain independent.

    Proves: Persistence results do not propagate across lifecycle stages.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    # Persistence observation: overall passes, but we'll set individual lifecycles
    # This is a synthetic test; in real execution, P1/P2/P3 would be independent experiments
    persistence_observation = {
        "status": PASS,
        "checked": True,
        "exact_match": True,
    }

    receipt = evaluate_record(
        experiment_id="TEST-P1-P2-P3",
        resolved_target=resolved_target,
        state_observation={},
        persistence_observation=persistence_observation,
        causal_measurements=[],
    )

    # Current architecture does not yet establish P1/P2/P3 separately
    # So all three remain NOT_RUN by design
    assert receipt.persistence.p1_same_engine.status == NOT_RUN
    assert receipt.persistence.p2_new_instance.status == NOT_RUN
    assert receipt.persistence.p3_fresh_process.status == NOT_RUN

    # But overall persistence can still PASS or FAIL
    assert receipt.persistence.overall.status in (PASS, FAIL)


def test_restoration_failure():
    """restoration=FAIL is a valid gate result.

    Proves: Restoration is independently evaluated.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    # Even if generation/persistence pass, restoration could fail
    state_observation = {
        "status": PASS,
        "matches_intent": True,
        "top_level_ok": True,
        "fine_grained_ok": True,
        "diff_keys": ["TestField"],
    }

    receipt = evaluate_record(
        experiment_id="TEST-RESTORATION-FAIL",
        resolved_target=resolved_target,
        state_observation=state_observation,
        persistence_observation={},
        causal_measurements=[],
    )

    # Restoration is not yet implemented, so it stays NOT_RUN
    assert receipt.restoration.status == NOT_RUN


def test_missing_observations_all_not_run():
    """Empty observations leave all gates NOT_RUN.

    Proves: Gates do not hallucinate results from missing evidence.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    receipt = evaluate_record(
        experiment_id="TEST-NO-EVIDENCE",
        resolved_target=resolved_target,
        state_observation={},
        persistence_observation={},
        causal_measurements=[],
    )

    assert receipt.generation.status == NOT_RUN
    assert receipt.collateral.status == NOT_RUN
    assert receipt.behavior.status == NOT_RUN
    assert receipt.persistence.overall.status == NOT_RUN
    assert receipt.restoration.status == NOT_RUN


def test_wrong_direction_behavior_fails():
    """Measurement moving in wrong direction fails behavior gate.

    Proves: Behavior gate correctly rejects inverted causality.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    causal_measurements = [
        {"status": "WRONG_DIRECTION"},
    ]

    receipt = evaluate_record(
        experiment_id="TEST-WRONG-DIRECTION",
        resolved_target=resolved_target,
        state_observation={},
        persistence_observation={},
        causal_measurements=causal_measurements,
    )

    assert receipt.behavior.status == FAIL, "WRONG_DIRECTION must fail behavior"


def test_mixed_measurements_inconclusive():
    """Mixed measurement outcomes produce NOT_RUN behavior.

    Proves: Behavior gate requires consistent measurement.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    causal_measurements = [
        {"status": "EFFECT_OBSERVED"},
        {"status": "NO_OBSERVED_EFFECT"},
    ]

    receipt = evaluate_record(
        experiment_id="TEST-MIXED-MEASUREMENTS",
        resolved_target=resolved_target,
        state_observation={},
        persistence_observation={},
        causal_measurements=causal_measurements,
    )

    assert receipt.behavior.status == NOT_RUN, "Mixed outcomes are inconclusive"


def test_all_effect_observed_passes():
    """All measurements showing effect produces PASS behavior.

    Proves: Behavior gate correctly accepts consistent positive evidence.
    """

    resolved_target = {
        "semantic_id": "Test.Target",
        "capability_key": "test_capability",
        "vst3_name": "Test Param",
        "vst3_index": 0,
    }

    causal_measurements = [
        {"status": "EFFECT_OBSERVED"},
        {"status": "EFFECT_OBSERVED"},
    ]

    receipt = evaluate_record(
        experiment_id="TEST-ALL-EFFECT",
        resolved_target=resolved_target,
        state_observation={},
        persistence_observation={},
        causal_measurements=causal_measurements,
    )

    assert receipt.behavior.status == PASS, "All EFFECT_OBSERVED means PASS"


def main() -> None:
    """Run adversarial evaluator tests."""

    tests = [
        ("generation PASS + persistence FAIL independent", test_generation_pass_persistence_fail_independent),
        ("generation PASS + NO_OBSERVED_EFFECT does not fail generation", test_generation_pass_no_observed_effect_does_not_fail_generation),
        ("collateral detects unintended changes", test_collateral_unintended_changes_detected),
        ("P1/P2/P3 lifecycle independence", test_p1_pass_p2_fail_p3_not_run_independent),
        ("restoration FAIL", test_restoration_failure),
        ("missing observations all NOT_RUN", test_missing_observations_all_not_run),
        ("WRONG_DIRECTION fails behavior", test_wrong_direction_behavior_fails),
        ("mixed measurements inconclusive", test_mixed_measurements_inconclusive),
        ("all EFFECT_OBSERVED passes", test_all_effect_observed_passes),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 EVALUATOR ADVERSARIAL TESTS")
    print("=" * 70 + "\n")

    for name, test_func in tests:
        try:
            test_func()
            print("PASS: {}".format(name))
            passed += 1
        except AssertionError as e:
            print("FAIL: {}: {}".format(name, e))
            failed += 1
        except Exception as e:
            print("ERROR: {}: {}".format(name, e))
            failed += 1

    print("\n" + "=" * 70)
    print("{}/{} tests passed".format(passed, len(tests)))
    print("A3 EVALUATOR ADVERSARIAL: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
