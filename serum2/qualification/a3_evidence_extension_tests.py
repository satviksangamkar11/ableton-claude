"""16.5.69.2-A3-13: Evidence Extension Integration Tests

Verify P1/P2/P3 lifecycle evidence integrates correctly and independently
into EvidenceRecord while preserving backward compatibility.
"""

from __future__ import annotations

from serum2.qualification.a3_evidence_extension import (
    P1PersistenceObservation,
    P1_NOT_RUN,
    PersistenceLifecycleEvidence,
    create_evidence_record_extension,
)
from serum2.qualification.a3_persistence_lifecycle import (
    P2_NOT_RUN,
    P3_NOT_RUN,
    create_p2_observation,
    create_p3_observation,
)


def test_p1_observation_structure():
    """P1 observation carries correct fields."""
    p1 = P1PersistenceObservation(
        status="PASS",
        reason="Reloaded successfully",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_after_reload=90.0,
    )

    assert p1.status == "PASS"
    assert p1.passed is True
    assert p1.target_value_before == 0.0
    assert p1.target_value_after_reload == 90.0


def test_p1_not_run_preserved():
    """P1 NOT_RUN sentinel is properly constructed."""
    assert P1_NOT_RUN.status == "NOT_RUN"
    assert not P1_NOT_RUN.passed
    assert P1_NOT_RUN.target_value_before is None


def test_persistence_lifecycle_evidence_independence():
    """P1/P2/P3 within PersistenceLifecycleEvidence are independent."""

    p1_pass = P1PersistenceObservation(
        status="PASS",
        reason="P1 passed",
        target_value_after_reload=90.0,
    )

    p2_fail = create_p2_observation(
        status="FAIL",
        reason="P2 failed",
        fresh_instance_created=True,
    )

    p3_not_run = P3_NOT_RUN

    lifecycle = PersistenceLifecycleEvidence(
        p1=p1_pass,
        p2=p2_fail,
        p3=p3_not_run,
    )

    assert lifecycle.p1.status == "PASS"
    assert lifecycle.p2.status == "FAIL"
    assert lifecycle.p3.status == "NOT_RUN"

    # No inference between lifecycle stages
    assert lifecycle.p1.passed is True
    assert lifecycle.p2.passed is False
    assert lifecycle.p3.passed is False


def test_persistence_lifecycle_defaults():
    """Default PersistenceLifecycleEvidence uses NOT_RUN sentinels."""

    lifecycle = PersistenceLifecycleEvidence()

    assert lifecycle.p1.status == "NOT_RUN"
    assert lifecycle.p2.status == "NOT_RUN"
    assert lifecycle.p3.status == "NOT_RUN"


def test_create_evidence_record_extension():
    """Factory creates correct lifecycle evidence structure."""

    p1_custom = P1PersistenceObservation(status="PASS", reason="custom P1")
    p2_custom = create_p2_observation(status="PASS", reason="custom P2")

    lifecycle = create_evidence_record_extension(
        p1_observation=p1_custom,
        p2_observation=p2_custom,
    )

    assert lifecycle.p1.status == "PASS"
    assert lifecycle.p2.status == "PASS"
    assert lifecycle.p3.status == "NOT_RUN"  # Defaults to NOT_RUN


def test_no_lifecycle_to_lifecycle_inference():
    """P1 result does not change P2/P3 results."""

    # P1 FAIL scenario
    p1_fail = P1PersistenceObservation(
        status="FAIL",
        reason="P1 failed",
        target_value_after_reload=0.0,
    )

    # P2 can still PASS even if P1 failed
    p2_pass = create_p2_observation(
        status="PASS",
        reason="P2 passed (independent from P1)",
        fresh_instance_created=True,
    )

    lifecycle = PersistenceLifecycleEvidence(p1=p1_fail, p2=p2_pass)

    assert lifecycle.p1.status == "FAIL"
    assert lifecycle.p2.status == "PASS"  # Not inferred from P1


def test_to_dict_serialization():
    """PersistenceLifecycleEvidence serializes correctly."""

    p1 = P1PersistenceObservation(
        status="PASS",
        reason="P1 passed",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_after_reload=90.0,
    )

    lifecycle = PersistenceLifecycleEvidence(p1=p1)
    data = lifecycle.to_dict()

    assert data["p1"]["status"] == "PASS"
    assert data["p1"]["reason"] == "P1 passed"
    assert data["p2"]["status"] == "NOT_RUN"
    assert data["p3"]["status"] == "NOT_RUN"


def main() -> None:
    """Run evidence extension tests."""

    tests = [
        ("P1 observation structure", test_p1_observation_structure),
        ("P1 NOT_RUN preserved", test_p1_not_run_preserved),
        ("P1/P2/P3 independence", test_persistence_lifecycle_evidence_independence),
        ("Lifecycle defaults", test_persistence_lifecycle_defaults),
        ("Factory creation", test_create_evidence_record_extension),
        ("No lifecycle inference", test_no_lifecycle_to_lifecycle_inference),
        ("Serialization", test_to_dict_serialization),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 EVIDENCE EXTENSION INTEGRATION TESTS")
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
    print("A3 EVIDENCE EXTENSION: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
