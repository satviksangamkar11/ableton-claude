"""16.5.69.2-A3-13: A3 Evaluator Lifecycle Integration Tests

Verify that the evaluator properly extracts independent P1/P2/P3 results
from persistence_lifecycle observations.
"""

from __future__ import annotations

from serum2.qualification.a3_evaluator import evaluate_persistence
from serum2.qualification.a3_evidence_extension import (
    P1PersistenceObservation,
    PersistenceLifecycleEvidence,
)
from serum2.qualification.a3_persistence_lifecycle import (
    create_p2_observation,
    create_p3_observation,
)


def test_evaluate_persistence_with_p1_pass():
    """Evaluator extracts P1 PASS from persistence_lifecycle."""

    p1 = P1PersistenceObservation(
        status="PASS",
        reason="P1 persisted",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_after_reload=90.0,
    )

    lifecycle = PersistenceLifecycleEvidence(p1=p1)

    result = evaluate_persistence(
        {"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p1_same_engine.status == "PASS"
    assert result.p2_new_instance.status == "NOT_RUN"
    assert result.p3_fresh_process.status == "NOT_RUN"
    assert result.overall.status == "PASS"


def test_evaluate_persistence_with_p1_fail():
    """Evaluator extracts P1 FAIL from persistence_lifecycle."""

    p1 = P1PersistenceObservation(
        status="FAIL",
        reason="P1 did not persist",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_after_reload=0.0,
    )

    lifecycle = PersistenceLifecycleEvidence(p1=p1)

    result = evaluate_persistence(
        {"status": "FAIL"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p1_same_engine.status == "FAIL"
    assert result.p2_new_instance.status == "NOT_RUN"
    assert result.p3_fresh_process.status == "NOT_RUN"


def test_evaluate_persistence_with_p2_pass():
    """Evaluator extracts P2 PASS from persistence_lifecycle."""

    p2 = create_p2_observation(
        status="PASS",
        reason="P2 persisted",
        target_value_after_mutation=90.0,
        target_value_in_fresh_instance=90.0,
        fresh_instance_created=True,
    )

    lifecycle = PersistenceLifecycleEvidence(p2=p2)

    result = evaluate_persistence(
        {"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p1_same_engine.status == "NOT_RUN"
    assert result.p2_new_instance.status == "PASS"
    assert result.p3_fresh_process.status == "NOT_RUN"


def test_evaluate_persistence_with_p2_fail():
    """Evaluator extracts P2 FAIL from persistence_lifecycle."""

    p2 = create_p2_observation(
        status="FAIL",
        reason="P2 did not persist",
        target_value_after_mutation=90.0,
        target_value_in_fresh_instance=0.0,
        fresh_instance_created=True,
    )

    lifecycle = PersistenceLifecycleEvidence(p2=p2)

    result = evaluate_persistence(
        {"status": "FAIL"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p2_new_instance.status == "FAIL"


def test_evaluate_persistence_with_p3_pass():
    """Evaluator extracts P3 PASS from persistence_lifecycle."""

    p3 = create_p3_observation(
        status="PASS",
        reason="P3 persisted",
        target_value_after_mutation=90.0,
        target_value_in_fresh_process=90.0,
        process_boundary_crossed=True,
        process_a_pid=11111,
        process_b_pid=22222,
    )

    lifecycle = PersistenceLifecycleEvidence(p3=p3)

    result = evaluate_persistence(
        {"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p1_same_engine.status == "NOT_RUN"
    assert result.p2_new_instance.status == "NOT_RUN"
    assert result.p3_fresh_process.status == "PASS"


def test_evaluate_persistence_with_p3_fail():
    """Evaluator extracts P3 FAIL from persistence_lifecycle."""

    p3 = create_p3_observation(
        status="FAIL",
        reason="P3 did not persist",
        target_value_after_mutation=90.0,
        target_value_in_fresh_process=0.0,
        process_boundary_crossed=True,
    )

    lifecycle = PersistenceLifecycleEvidence(p3=p3)

    result = evaluate_persistence(
        {"status": "FAIL"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p3_fresh_process.status == "FAIL"


def test_evaluate_persistence_with_mixed_p1_p2_p3():
    """Evaluator handles mixed P1/P2/P3 results independently."""

    p1 = P1PersistenceObservation(status="PASS", reason="P1 ok")
    p2 = create_p2_observation(status="FAIL", reason="P2 failed", fresh_instance_created=True)
    p3 = create_p3_observation(status="PASS", reason="P3 ok", process_boundary_crossed=True)

    lifecycle = PersistenceLifecycleEvidence(p1=p1, p2=p2, p3=p3)

    result = evaluate_persistence(
        {"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert result.p1_same_engine.status == "PASS"
    assert result.p2_new_instance.status == "FAIL"
    assert result.p3_fresh_process.status == "PASS"


def test_evaluate_persistence_without_lifecycle():
    """Evaluator handles None persistence_lifecycle (backward compatibility)."""

    result = evaluate_persistence(
        {"status": "PASS"},
        persistence_lifecycle=None,
    )

    assert result.overall.status == "PASS"
    assert result.p1_same_engine.status == "NOT_RUN"
    assert result.p2_new_instance.status == "NOT_RUN"
    assert result.p3_fresh_process.status == "NOT_RUN"


def test_evaluate_persistence_empty_observation_with_lifecycle():
    """Evaluator with empty persistence_observation but valid lifecycle."""

    p1 = P1PersistenceObservation(status="PASS", reason="P1 ok")
    lifecycle = PersistenceLifecycleEvidence(p1=p1)

    result = evaluate_persistence(
        {},  # Empty observation dict
        persistence_lifecycle=lifecycle,
    )

    # overall should be NOT_RUN (no observation)
    assert result.overall.status == "NOT_RUN"
    # But P1 should be extracted from lifecycle
    assert result.p1_same_engine.status == "PASS"


def main() -> None:
    """Run evaluator lifecycle integration tests."""

    tests = [
        ("P1 PASS extraction", test_evaluate_persistence_with_p1_pass),
        ("P1 FAIL extraction", test_evaluate_persistence_with_p1_fail),
        ("P2 PASS extraction", test_evaluate_persistence_with_p2_pass),
        ("P2 FAIL extraction", test_evaluate_persistence_with_p2_fail),
        ("P3 PASS extraction", test_evaluate_persistence_with_p3_pass),
        ("P3 FAIL extraction", test_evaluate_persistence_with_p3_fail),
        ("Mixed P1/P2/P3 results", test_evaluate_persistence_with_mixed_p1_p2_p3),
        ("Backward compatibility (None)", test_evaluate_persistence_without_lifecycle),
        ("Empty observation with lifecycle", test_evaluate_persistence_empty_observation_with_lifecycle),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 EVALUATOR LIFECYCLE INTEGRATION TESTS")
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
    print("A3 EVALUATOR LIFECYCLE: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
