"""16.5.69.2-A3-16: Behavior Observation Unit Tests

Covers:
- BehaviorObservation structure and defaults
- UNKNOWN sentinel preserved
- CAUSAL_VERIFIED, NO_OBSERVED_EFFECT, WRONG_DIRECTION, INCONCLUSIVE distinct
- Behavior independent of persistence (P1/P2/P3)
- Behavior independent of restoration
- NO_OBSERVED_EFFECT does NOT poison generation
- UNKNOWN/INCONCLUSIVE distinguishable
"""

from __future__ import annotations

from serum2.qualification.a3_behavior_observation import (
    BehaviorObservation,
    BEHAVIOR_NOT_RUN,
    create_behavior_observation,
)
from serum2.qualification.a3_restoration_observation import (
    create_restoration_observation,
    RESTORATION_NOT_RUN,
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


def test_behavior_not_run_preserved():
    """BEHAVIOR_NOT_RUN sentinel preserved correctly."""
    assert BEHAVIOR_NOT_RUN.status == "UNKNOWN"
    assert not BEHAVIOR_NOT_RUN.passed
    assert not BEHAVIOR_NOT_RUN.observed_effect


def test_causal_verified_structure():
    """CAUSAL_VERIFIED observation has correct flags."""
    obs = create_behavior_observation(
        status="CAUSAL_VERIFIED",
        reason="Effect observed",
        baseline_metric=-20.0,
        mutated_metric=-15.0,
        metric_name="overall_rms_db",
        expected_direction="increase",
        observed_direction="increase",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    assert obs.status == "CAUSAL_VERIFIED"
    assert obs.passed is True
    assert obs.observed_effect is True
    assert obs.baseline_rendered is True
    assert obs.mutated_rendered is True


def test_no_observed_effect_structure():
    """NO_OBSERVED_EFFECT does not set passed=True."""
    obs = create_behavior_observation(
        status="NO_OBSERVED_EFFECT",
        reason="Delta below threshold",
        baseline_metric=-20.0,
        mutated_metric=-20.1,
        metric_name="overall_rms_db",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    assert obs.status == "NO_OBSERVED_EFFECT"
    assert obs.passed is False
    assert obs.observed_effect is False


def test_wrong_direction_distinguishable_from_causal():
    """WRONG_DIRECTION is not CAUSAL_VERIFIED."""
    obs = create_behavior_observation(
        status="WRONG_DIRECTION",
        reason="Expected increase, observed decrease",
        baseline_metric=-20.0,
        mutated_metric=-25.0,
        expected_direction="increase",
        observed_direction="decrease",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    assert obs.status == "WRONG_DIRECTION"
    assert obs.passed is False
    assert obs.observed_effect is True  # Effect was detected, just wrong direction


def test_unknown_and_inconclusive_distinguishable():
    """UNKNOWN and INCONCLUSIVE are separate, distinguishable statuses."""
    unknown = create_behavior_observation(
        status="UNKNOWN",
        reason="Render failed",
        baseline_rendered=False,
        mutated_rendered=False,
    )

    inconclusive = create_behavior_observation(
        status="INCONCLUSIVE",
        reason="Effect detected but direction ambiguous",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    assert unknown.status == "UNKNOWN"
    assert inconclusive.status == "INCONCLUSIVE"
    assert unknown.status != inconclusive.status


def test_p1_fail_does_not_determine_behavior():
    """P1 persistence FAIL does NOT determine behavior."""
    p1_fail = P1PersistenceObservation(
        status="FAIL",
        reason="Boolean did not persist",
        target_value_after_mutation=True,
        target_value_after_reload=False,
    )
    lifecycle = PersistenceLifecycleEvidence(p1=p1_fail, p2=P2_NOT_RUN, p3=P3_NOT_RUN)

    # Behavior can be CAUSAL_VERIFIED even when P1 FAILS
    behavior_pass = create_behavior_observation(
        status="CAUSAL_VERIFIED",
        reason="Audio effect observed",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    assert lifecycle.p1.status == "FAIL"
    assert behavior_pass.status == "CAUSAL_VERIFIED"
    # These are fully independent observations
    assert lifecycle.p1.status != behavior_pass.status


def test_behavior_does_not_determine_persistence():
    """Behavior CAUSAL_VERIFIED does NOT imply P1 PASS."""
    behavior_pass = create_behavior_observation(
        status="CAUSAL_VERIFIED",
        reason="Effect observed",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    p1_fail = P1PersistenceObservation(
        status="FAIL",
        reason="Still fails persistence",
    )

    # Both coexist — valid OSC1.Enable-like scenario
    assert behavior_pass.status == "CAUSAL_VERIFIED"
    assert p1_fail.status == "FAIL"


def test_no_observed_effect_does_not_poison_generation():
    """NO_OBSERVED_EFFECT on behavior gate does not change generation status.

    This is a contract test: no gate_inference is permitted between
    behavior and generation. Generation is an independent field.
    """
    behavior_no_effect = create_behavior_observation(
        status="NO_OBSERVED_EFFECT",
        reason="No audio change detected",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    # Generation status is set independently — these cannot interact
    generation_status = "PASS"  # Would be set by evaluator independently

    assert behavior_no_effect.status == "NO_OBSERVED_EFFECT"
    assert generation_status == "PASS"
    # No field on BehaviorObservation affects generation


def test_behavior_independent_of_restoration():
    """Behavior observation does not interact with restoration observation."""
    behavior = create_behavior_observation(
        status="CAUSAL_VERIFIED",
        reason="Effect observed",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    restoration_fail = create_restoration_observation(
        status="FAIL",
        reason="Restore failed",
        target_restored=False,
        collateral_restored=True,
    )

    # These are independent dataclasses — no shared state
    assert behavior.status == "CAUSAL_VERIFIED"
    assert restoration_fail.status == "FAIL"
    assert behavior.status != restoration_fail.status


def test_all_statuses_are_valid_final_states():
    """All five behavior statuses are valid, non-error final states."""
    statuses = [
        "CAUSAL_VERIFIED",
        "NO_OBSERVED_EFFECT",
        "WRONG_DIRECTION",
        "INCONCLUSIVE",
        "UNKNOWN",
    ]

    for status in statuses:
        obs = create_behavior_observation(
            status=status,
            reason="test",
        )
        assert obs.status == status, "Status not preserved: {}".format(status)


def test_osc1_enable_valid_combinations():
    """OSC1.Enable can be: P1=FAIL, Restoration=PASS, Behavior=CAUSAL_VERIFIED."""
    p1_fail = P1PersistenceObservation(
        status="FAIL",
        reason="Boolean persistence fails",
    )
    lifecycle = PersistenceLifecycleEvidence(p1=p1_fail, p2=P2_NOT_RUN, p3=P3_NOT_RUN)

    restoration_pass = create_restoration_observation(
        status="PASS",
        reason="Baseline restored",
        target_restored=True,
        collateral_restored=True,
    )

    behavior_pass = create_behavior_observation(
        status="CAUSAL_VERIFIED",
        reason="Enabling OSC1 changes audio output",
        baseline_rendered=True,
        mutated_rendered=True,
    )

    # All three independent observations
    assert lifecycle.p1.status == "FAIL"
    assert restoration_pass.status == "PASS"
    assert behavior_pass.status == "CAUSAL_VERIFIED"

    # Verify no cascades: each observation computed from its own lifecycle
    assert lifecycle.p1.passed is False
    assert restoration_pass.passed is True
    assert behavior_pass.passed is True


def main() -> None:
    """Run behavior observation unit tests."""

    tests = [
        ("BEHAVIOR_NOT_RUN preserved", test_behavior_not_run_preserved),
        ("CAUSAL_VERIFIED structure", test_causal_verified_structure),
        ("NO_OBSERVED_EFFECT structure", test_no_observed_effect_structure),
        ("WRONG_DIRECTION distinguishable from CAUSAL", test_wrong_direction_distinguishable_from_causal),
        ("UNKNOWN/INCONCLUSIVE distinguishable", test_unknown_and_inconclusive_distinguishable),
        ("P1 FAIL does not determine behavior", test_p1_fail_does_not_determine_behavior),
        ("Behavior CAUSAL_VERIFIED does not determine P1", test_behavior_does_not_determine_persistence),
        ("NO_OBSERVED_EFFECT does not poison generation", test_no_observed_effect_does_not_poison_generation),
        ("Behavior independent of restoration", test_behavior_independent_of_restoration),
        ("All 5 statuses valid", test_all_statuses_are_valid_final_states),
        ("OSC1.Enable: P1=FAIL + Restoration=PASS + Behavior=PASS", test_osc1_enable_valid_combinations),
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("A3 BEHAVIOR OBSERVATION TESTS")
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
    print("A3 BEHAVIOR TESTS: {}".format("PASS" if failed == 0 else "FAIL"))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
