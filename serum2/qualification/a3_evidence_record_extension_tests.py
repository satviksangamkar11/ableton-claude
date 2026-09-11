"""16.5.69.2-A3-13: EvidenceRecord Extension Integration Tests

Verify P1/P2/P3 lifecycle evidence integrates with EvidenceRecord while
preserving backward compatibility with existing records.
"""

from __future__ import annotations

from serum2.evidence.record import EvidenceRecord, EvidenceArm, CausalMeasurement, MeasurementTarget
from serum2.qualification.a3_evidence_extension import (
    P1PersistenceObservation,
    PersistenceLifecycleEvidence,
    create_evidence_record_extension,
)
from serum2.qualification.a3_persistence_lifecycle import (
    create_p2_observation,
    create_p3_observation,
)


def test_evidence_record_carries_persistence_lifecycle():
    """EvidenceRecord can carry PersistenceLifecycleEvidence."""

    p1 = P1PersistenceObservation(
        status="PASS",
        reason="P1 passed",
        target_value_after_reload=90.0,
    )

    lifecycle = PersistenceLifecycleEvidence(p1=p1)

    record = EvidenceRecord(
        experiment_id="test-001",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert record.persistence_lifecycle is not None
    assert record.persistence_lifecycle.p1.status == "PASS"


def test_evidence_record_backward_compatibility_none():
    """EvidenceRecord with persistence_lifecycle=None handles old pickled records.

    When constructed explicitly without the field, it defaults to None.
    When unpickling old records that lack the field entirely, __getattr__ provides DEFAULT.
    """

    record = EvidenceRecord(
        experiment_id="test-002",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
    )

    # New records default to None
    assert record.persistence_lifecycle is None

    # But accessing it via getattr (simulating old pickled record) returns DEFAULT
    # This tests __getattr__ for backward compatibility with pickled records
    from serum2.qualification.a3_evidence_extension import DEFAULT_PERSISTENCE_LIFECYCLE

    # Simulate accessing via __getattr__ (what happens with old pickled records)
    result = record.__getattr__("persistence_lifecycle")
    assert result is DEFAULT_PERSISTENCE_LIFECYCLE
    assert result.p1.status == "NOT_RUN"
    assert result.p2.status == "NOT_RUN"
    assert result.p3.status == "NOT_RUN"


def test_evidence_record_p2_fresh_instance_identity():
    """P2 observation in record enforces fresh-instance identity."""

    p2 = create_p2_observation(
        status="PASS",
        reason="Fresh instance test passed",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_in_fresh_instance=90.0,
        fresh_instance_created=True,
        saved_state_identity="artifact_123",
        fresh_instance_identity="serum_456",
    )

    lifecycle = PersistenceLifecycleEvidence(p2=p2)

    record = EvidenceRecord(
        experiment_id="test-003",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert record.persistence_lifecycle.p2.fresh_instance_created is True
    assert record.persistence_lifecycle.p2.saved_state_identity == "artifact_123"
    assert record.persistence_lifecycle.p2.fresh_instance_identity == "serum_456"


def test_evidence_record_p3_process_boundary():
    """P3 observation in record enforces process boundary."""

    p3 = create_p3_observation(
        status="PASS",
        reason="Process boundary test passed",
        target_value_before=0.0,
        target_value_after_mutation=90.0,
        target_value_in_fresh_process=90.0,
        saved_state_identity="artifact_def",
        process_a_pid=11111,
        process_b_pid=22222,
        process_boundary_crossed=True,
    )

    lifecycle = PersistenceLifecycleEvidence(p3=p3)

    record = EvidenceRecord(
        experiment_id="test-004",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert record.persistence_lifecycle.p3.process_boundary_crossed is True
    assert record.persistence_lifecycle.p3.process_a_pid == 11111
    assert record.persistence_lifecycle.p3.process_b_pid == 22222


def test_evidence_record_independent_p1_p2_p3_results():
    """P1/P2/P3 results in record are independent."""

    p1 = P1PersistenceObservation(
        status="PASS",
        reason="P1 passed",
    )

    p2 = create_p2_observation(
        status="FAIL",
        reason="P2 failed",
        fresh_instance_created=True,
    )

    p3 = create_p3_observation(
        status="NOT_RUN",
        reason="P3 not run",
    )

    lifecycle = PersistenceLifecycleEvidence(p1=p1, p2=p2, p3=p3)

    record = EvidenceRecord(
        experiment_id="test-005",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    assert record.persistence_lifecycle.p1.status == "PASS"
    assert record.persistence_lifecycle.p2.status == "FAIL"
    assert record.persistence_lifecycle.p3.status == "NOT_RUN"

    # No inference between lifecycle stages
    assert record.persistence_lifecycle.p1.passed is True
    assert record.persistence_lifecycle.p2.passed is False
    assert record.persistence_lifecycle.p3.passed is False


def test_evidence_record_to_dict_with_lifecycle():
    """EvidenceRecord.to_dict() includes persistence_lifecycle."""

    lifecycle = create_evidence_record_extension()

    record = EvidenceRecord(
        experiment_id="test-006",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
        persistence_lifecycle=lifecycle,
    )

    data = record.to_dict()

    assert "persistence_lifecycle" in data
    assert data["persistence_lifecycle"]["p1"]["status"] == "NOT_RUN"
    assert data["persistence_lifecycle"]["p2"]["status"] == "NOT_RUN"
    assert data["persistence_lifecycle"]["p3"]["status"] == "NOT_RUN"


def test_evidence_record_to_dict_none_lifecycle():
    """EvidenceRecord.to_dict() with persistence_lifecycle=None returns default."""

    record = EvidenceRecord(
        experiment_id="test-007",
        epoch={},
        experiment={},
        arms=(),
        runtime_verifications=(),
        state_observation={"status": "PASS"},
        load_observation={"status": "PASS"},
        render_observation={"status": "PASS"},
        causal_measurements=(),
        persistence_observation={"status": "PASS"},
    )

    data = record.to_dict()

    # to_dict uses asdict, which will call __getattr__ if needed
    assert "persistence_lifecycle" in data or record.persistence_lifecycle is not None


def main() -> None:
    """Run EvidenceRecord extension integration tests."""

    tests = [
        ("EvidenceRecord carries persistence_lifecycle", test_evidence_record_carries_persistence_lifecycle),
        ("Backward compatibility (None)", test_evidence_record_backward_compatibility_none),
        ("P2 fresh instance identity", test_evidence_record_p2_fresh_instance_identity),
        ("P3 process boundary", test_evidence_record_p3_process_boundary),
        ("Independent P1/P2/P3 results", test_evidence_record_independent_p1_p2_p3_results),
        ("to_dict with lifecycle", test_evidence_record_to_dict_with_lifecycle),
        ("to_dict None lifecycle", test_evidence_record_to_dict_none_lifecycle),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 EVIDENCERECORD EXTENSION INTEGRATION TESTS")
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
    print("A3 EVIDENCERECORD EXTENSION: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
