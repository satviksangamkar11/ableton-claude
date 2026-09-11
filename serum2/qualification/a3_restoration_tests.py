"""16.5.69.2-A3-15: Restoration Qualification Tests

Covers:
- RestorationObservation structure and defaults
- NOT_RUN sentinel preserved
- target_restored independent of collateral_restored
- Persistence failure (P1/P2/P3) does NOT determine restoration
- Restoration failure does NOT determine persistence
"""

from __future__ import annotations

from serum2.qualification.a3_restoration_observation import (
    RestorationObservation,
    RESTORATION_NOT_RUN,
    create_restoration_observation,
)
from serum2.qualification.a3_evidence_extension import (
    P1PersistenceObservation,
    PersistenceLifecycleEvidence,
    P1_NOT_RUN,
)
from serum2.qualification.a3_persistence_lifecycle import (
    P2_NOT_RUN,
    P3_NOT_RUN,
)


def test_restoration_not_run_preserved():
    """NOT_RUN sentinel preserves correct values."""
    assert RESTORATION_NOT_RUN.status == "NOT_RUN"
    assert RESTORATION_NOT_RUN.target_restored is False
    assert RESTORATION_NOT_RUN.collateral_restored is False
    assert not RESTORATION_NOT_RUN.passed


def test_restoration_pass_structure():
    """PASS observation carries correct target/collateral flags."""
    obs = create_restoration_observation(
        status="PASS",
        reason="Restoration successful",
        baseline_value=0.0,
        value_after_mutation=90.0,
        value_after_restore=0.0,
        target_restored=True,
        collateral_restored=True,
    )

    assert obs.status == "PASS"
    assert obs.passed is True
    assert obs.target_restored is True
    assert obs.collateral_restored is True
    assert obs.baseline_value == 0.0
    assert obs.value_after_restore == 0.0


def test_restoration_fail_structure():
    """FAIL observation when target did not restore."""
    obs = create_restoration_observation(
        status="FAIL",
        reason="Target value not restored",
        baseline_value=0.0,
        value_after_mutation=90.0,
        value_after_restore=90.0,  # Not restored
        target_restored=False,
        collateral_restored=True,
    )

    assert obs.status == "FAIL"
    assert obs.passed is False
    assert obs.target_restored is False
    assert obs.collateral_restored is True  # Independent


def test_target_restored_independent_of_collateral():
    """target_restored and collateral_restored are independent flags."""
    # Scenario: target restored but collateral not
    obs_a = create_restoration_observation(
        status="FAIL",
        reason="Collateral changed",
        target_restored=True,
        collateral_restored=False,
    )
    assert obs_a.target_restored is True
    assert obs_a.collateral_restored is False

    # Scenario: collateral restored but target not
    obs_b = create_restoration_observation(
        status="FAIL",
        reason="Target not restored",
        target_restored=False,
        collateral_restored=True,
    )
    assert obs_b.target_restored is False
    assert obs_b.collateral_restored is True


def test_p1_fail_does_not_determine_restoration():
    """P1 persistence FAIL does NOT make restoration FAIL."""
    # OSC1.Enable scenario: P1 FAIL + restoration PASS
    p1_fail = P1PersistenceObservation(
        status="FAIL",
        reason="Boolean did not survive reload",
        target_value_after_mutation=True,
        target_value_after_reload=False,
    )
    lifecycle = PersistenceLifecycleEvidence(p1=p1_fail, p2=P2_NOT_RUN, p3=P3_NOT_RUN)

    restoration_pass = create_restoration_observation(
        status="PASS",
        reason="Baseline restored successfully",
        target_restored=True,
        collateral_restored=True,
    )

    # P1 is FAIL
    assert lifecycle.p1.status == "FAIL"
    assert lifecycle.p1.passed is False

    # Restoration is independently PASS
    assert restoration_pass.status == "PASS"
    assert restoration_pass.passed is True

    # These are separate observations — no inference
    assert lifecycle.p1.status != restoration_pass.status


def test_restoration_fail_does_not_determine_p1():
    """Restoration FAIL does NOT imply P1 FAIL."""
    p1_pass = P1PersistenceObservation(
        status="PASS",
        reason="Persisted successfully",
    )

    restoration_fail = create_restoration_observation(
        status="FAIL",
        reason="Baseline restore failed due to mutation side-effect",
        target_restored=False,
        collateral_restored=True,
    )

    # P1 PASS, restoration FAIL — valid independent combination
    assert p1_pass.status == "PASS"
    assert restoration_fail.status == "FAIL"


def test_restoration_not_run_does_not_affect_persistence():
    """RESTORATION_NOT_RUN must not affect persistence lifecycle."""
    obs = RESTORATION_NOT_RUN

    # NOT_RUN never contaminates other gates
    assert obs.target_restored is False
    assert obs.collateral_restored is False
    assert obs.passed is False


def test_collateral_restoration_verifies_full_baseline():
    """collateral_restored tracks whether entire baseline is restored."""
    obs_ok = create_restoration_observation(
        status="PASS",
        reason="All baseline matched",
        target_restored=True,
        collateral_restored=True,
    )

    obs_partial = create_restoration_observation(
        status="FAIL",
        reason="Only target restored; other fields drifted",
        target_restored=True,
        collateral_restored=False,
    )

    assert obs_ok.collateral_restored is True
    assert obs_partial.collateral_restored is False


def main() -> None:
    """Run restoration observation unit tests."""

    tests = [
        ("NOT_RUN preserved", test_restoration_not_run_preserved),
        ("PASS structure", test_restoration_pass_structure),
        ("FAIL structure", test_restoration_fail_structure),
        ("target/collateral independent", test_target_restored_independent_of_collateral),
        ("P1 FAIL does not determine restoration", test_p1_fail_does_not_determine_restoration),
        ("Restoration FAIL does not determine P1", test_restoration_fail_does_not_determine_p1),
        ("NOT_RUN does not affect persistence", test_restoration_not_run_does_not_affect_persistence),
        ("Collateral verifies full baseline", test_collateral_restoration_verifies_full_baseline),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 RESTORATION OBSERVATION TESTS")
    print("=" * 70 + "\n")

    for name, fn in tests:
        try:
            fn()
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
    print("A3 RESTORATION TESTS: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
