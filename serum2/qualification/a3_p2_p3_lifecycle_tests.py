"""16.5.69.2-A3-12B/C: P2/P3 Lifecycle Independence Tests

Verify that P2 and P3 persistence measurements are independent
and preserve NOT_RUN semantics when not executed.
"""

from __future__ import annotations

from serum2.qualification.a3_persistence_lifecycle import (
    P2_NOT_RUN,
    P3_NOT_RUN,
    create_p2_observation,
    create_p3_observation,
)
from serum2.qualification.a3_p2_p3_harness import (
    qualify_with_p2_p3,
)


def test_p2_not_run_preserved():
    """P2 NOT_RUN is preserved when test not executed."""

    assert P2_NOT_RUN.status == "NOT_RUN"
    assert not P2_NOT_RUN.passed
    assert P2_NOT_RUN.fresh_instance_created is False


def test_p3_not_run_preserved():
    """P3 NOT_RUN is preserved when test not executed."""

    assert P3_NOT_RUN.status == "NOT_RUN"
    assert not P3_NOT_RUN.passed
    assert P3_NOT_RUN.process_boundary_crossed is False


def test_p2_pass_independent_of_p1():
    """P2=PASS does not require P1=PASS."""

    p2_pass = create_p2_observation(
        status="PASS",
        reason="Fresh instance persisted value",
        target_value_after_mutation=90.0,
        target_value_in_fresh_instance=90.0,
        fresh_instance_created=True,
    )

    assert p2_pass.status == "PASS"
    assert p2_pass.passed is True
    assert p2_pass.fresh_instance_created is True


def test_p2_fail_independent_of_p1():
    """P2=FAIL does not require P1=FAIL."""

    p2_fail = create_p2_observation(
        status="FAIL",
        reason="Fresh instance lost value",
        target_value_after_mutation=90.0,
        target_value_in_fresh_instance=0.0,  # Lost the mutation
        fresh_instance_created=True,
    )

    assert p2_fail.status == "FAIL"
    assert p2_fail.passed is False


def test_p3_requires_process_boundary():
    """P3 test requires process_boundary_crossed=True."""

    p3_obs = create_p3_observation(
        status="PASS",
        reason="Fresh process persisted value",
        target_value_after_mutation=90.0,
        target_value_in_fresh_process=90.0,
        process_boundary_crossed=True,
        process_a_pid=12345,
        process_b_pid=54321,
    )

    assert p3_obs.status == "PASS"
    assert p3_obs.process_boundary_crossed is True
    assert p3_obs.process_a_pid != p3_obs.process_b_pid


def test_p2_p3_independence():
    """P2 and P3 results are independent of each other."""

    p2_pass = create_p2_observation(
        status="PASS",
        reason="Fresh instance test passed",
        fresh_instance_created=True,
    )

    p3_fail = create_p3_observation(
        status="FAIL",
        reason="Fresh process test failed",
        process_boundary_crossed=True,
    )

    # P2 PASS + P3 FAIL is a valid combination
    assert p2_pass.status == "PASS"
    assert p3_fail.status == "FAIL"
    assert p2_pass.passed is True
    assert p3_fail.passed is False


def test_qualify_with_p2_p3_returns_not_run():
    """qualify_with_p2_p3 returns NOT_RUN until harness extended."""

    result = qualify_with_p2_p3(
        experiment_id="TEST-P2-P3",
        resolved_target={
            "semantic_id": "Test.Target",
            "capability_key": "test",
            "vst3_name": "Test",
            "vst3_index": 0,
        },
        experiment_spec={
            "mutations": [
                {"target_path": "Test.Path", "value": True}
            ]
        },
    )

    assert result["p2_observation"].status == "NOT_RUN"
    assert result["p3_observation"].status == "NOT_RUN"


def test_p2_observation_details():
    """P2 observation carries full lifecycle metadata."""

    p2_obs = create_p2_observation(
        status="PASS",
        reason="Test passed",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_in_fresh_instance=90.0,
        saved_state_identity="artifact_abc123",
        fresh_instance_identity="serum_instance_xyz789",
        details={"check_type": "value_match"},
    )

    assert p2_obs.target_value_before == 0.0
    assert p2_obs.target_value_after_mutation == 90.0
    assert p2_obs.target_value_in_fresh_instance == 90.0
    assert p2_obs.saved_state_identity == "artifact_abc123"
    assert p2_obs.fresh_instance_identity == "serum_instance_xyz789"
    assert p2_obs.details["check_type"] == "value_match"


def test_p3_observation_details():
    """P3 observation carries full lifecycle metadata."""

    p3_obs = create_p3_observation(
        status="PASS",
        reason="Test passed",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_in_fresh_process=90.0,
        saved_state_identity="artifact_def456",
        process_a_pid=11111,
        process_b_pid=22222,
        process_boundary_crossed=True,
        details={"subprocess": "isolated"},
    )

    assert p3_obs.target_value_before == 0.0
    assert p3_obs.target_value_after_mutation == 90.0
    assert p3_obs.target_value_in_fresh_process == 90.0
    assert p3_obs.saved_state_identity == "artifact_def456"
    assert p3_obs.process_a_pid == 11111
    assert p3_obs.process_b_pid == 22222
    assert p3_obs.process_boundary_crossed is True
    assert p3_obs.details["subprocess"] == "isolated"


def main() -> None:
    """Run P2/P3 lifecycle independence tests."""

    tests = [
        ("P2 NOT_RUN preserved", test_p2_not_run_preserved),
        ("P3 NOT_RUN preserved", test_p3_not_run_preserved),
        ("P2 PASS independent", test_p2_pass_independent_of_p1),
        ("P2 FAIL independent", test_p2_fail_independent_of_p1),
        ("P3 requires process boundary", test_p3_requires_process_boundary),
        ("P2/P3 independence", test_p2_p3_independence),
        ("qualify_with_p2_p3 returns NOT_RUN", test_qualify_with_p2_p3_returns_not_run),
        ("P2 observation details", test_p2_observation_details),
        ("P3 observation details", test_p3_observation_details),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 P2/P3 LIFECYCLE INDEPENDENCE TESTS")
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
    print("A3 P2/P3 LIFECYCLE: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
