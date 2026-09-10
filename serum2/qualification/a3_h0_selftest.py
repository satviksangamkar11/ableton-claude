#!/usr/bin/env python3
"""16.5.69.2: A3 evaluator H0 self-test.

No DawDreamer.
No Serum.
No VST3.
No file mutation.

Only synthetic observation dicts prove that the A3 evaluator
interprets evidence correctly.
"""

from __future__ import annotations

from a3_evaluator import evaluate_record
from a3_receipts import PASS, FAIL, NOT_RUN


TARGET = {
    "semantic_id": "test.semantic.target",
    "capability_key": "test_capability",
    "vst3_name": "Test Parameter",
    "vst3_index": 123,
}


def test_valid_record() -> None:
    """H0-1: Valid observations produce PASS receipt."""

    receipt = evaluate_record(
        experiment_id="H0-1",
        resolved_target=TARGET,
        state_observation={
            "status": PASS,
            "matches_intent": True,
            "top_level_ok": True,
            "fine_grained_ok": True,
            "diff_keys": ["TestParameter"],
            "intended_targets": ["TestParameter"],
        },
        persistence_observation={
            "status": PASS,
            "checked": True,
            "exact_match": True,
        },
        causal_measurements=[
            {
                "status": "EFFECT_OBSERVED",
                "metric": "rms",
                "baseline": 1.0,
                "treatment": 2.0,
                "delta": 1.0,
                "expected_direction": "increase",
            }
        ],
    )

    assert receipt.generation.status == PASS, f"generation={receipt.generation.status}"
    assert receipt.collateral.status == PASS, f"collateral={receipt.collateral.status}"
    assert receipt.behavior.status == PASS, f"behavior={receipt.behavior.status}"
    assert receipt.transport_mutable is True
    assert receipt.persistence.overall.status == PASS


def test_wrong_target_observation() -> None:
    """H0-2: State observation mismatch causes generation FAIL."""

    receipt = evaluate_record(
        experiment_id="H0-2",
        resolved_target=TARGET,
        state_observation={
            "status": FAIL,
            "matches_intent": False,
            "top_level_ok": False,
            "fine_grained_ok": False,
            "diff_keys": ["WrongParameter"],
            "intended_targets": ["TestParameter"],
        },
        persistence_observation={},
        causal_measurements=[],
    )

    assert receipt.generation.status == FAIL
    assert receipt.collateral.status == FAIL
    assert receipt.transport_mutable is False


def test_no_observed_effect_is_not_generation_failure() -> None:
    """H0-3: NO_OBSERVED_EFFECT fails behavior, not generation."""

    receipt = evaluate_record(
        experiment_id="H0-3",
        resolved_target=TARGET,
        state_observation={
            "status": PASS,
            "matches_intent": True,
            "top_level_ok": True,
            "fine_grained_ok": True,
            "diff_keys": ["TestParameter"],
            "intended_targets": ["TestParameter"],
        },
        persistence_observation={
            "status": PASS,
            "checked": True,
            "exact_match": True,
        },
        causal_measurements=[
            {
                "status": "NO_OBSERVED_EFFECT",
                "metric": "rms",
                "baseline": 1.0,
                "treatment": 1.0,
                "delta": 0.0,
                "expected_direction": "increase",
            }
        ],
    )

    assert receipt.generation.status == PASS, \
        "Generation PASS (state changed correctly)"
    assert receipt.behavior.status == FAIL, \
        "Behavior FAIL (no effect observed)"
    assert receipt.transport_mutable is True, \
        "transport_mutable still True (state mutation succeeded)"


def test_partial_persistence_preserved() -> None:
    """H0-4: Partial persistence results are preserved separately."""

    receipt = evaluate_record(
        experiment_id="H0-4",
        resolved_target=TARGET,
        state_observation={
            "status": PASS,
            "matches_intent": True,
            "top_level_ok": True,
            "fine_grained_ok": True,
            "diff_keys": ["TestParameter"],
            "intended_targets": ["TestParameter"],
        },
        persistence_observation={
            "status": FAIL,
            "checked": True,
            "exact_match": False,
        },
        causal_measurements=[
            {
                "status": "EFFECT_OBSERVED",
                "metric": "rms",
                "baseline": 1.0,
                "treatment": 2.0,
            }
        ],
    )

    assert receipt.persistence.overall.status == FAIL
    assert receipt.persistence.p1_same_engine.status == NOT_RUN, \
        "P1 stays NOT_RUN (not separately tested)"
    assert receipt.persistence.p2_new_instance.status == NOT_RUN, \
        "P2 stays NOT_RUN (not separately tested)"
    assert receipt.persistence.p3_fresh_process.status == NOT_RUN, \
        "P3 stays NOT_RUN (not separately tested)"


def test_collateral_detects_unexpected_changes() -> None:
    """H0-5: Collateral gate catches unexpected state diffs."""

    receipt = evaluate_record(
        experiment_id="H0-5",
        resolved_target=TARGET,
        state_observation={
            "status": FAIL,
            "matches_intent": False,
            "diff_keys": ["TestParameter", "UnexpectedParameter"],
            "intended_targets": ["TestParameter"],
        },
        persistence_observation={},
        causal_measurements=[],
    )

    assert receipt.collateral.status == FAIL, \
        "Collateral FAIL (unexpected parameters changed)"


def test_no_observations_available() -> None:
    """H0-6: Missing observations produce NOT_RUN results."""

    receipt = evaluate_record(
        experiment_id="H0-6",
        resolved_target=TARGET,
        state_observation={},
        persistence_observation={},
        causal_measurements=[],
    )

    assert receipt.generation.status == NOT_RUN
    assert receipt.behavior.status == NOT_RUN
    assert receipt.collateral.status == NOT_RUN
    assert receipt.restoration.status == NOT_RUN


def run_h0() -> int:
    """Run all H0 self-tests."""

    tests = [
        ("H0-1", test_valid_record),
        ("H0-2", test_wrong_target_observation),
        ("H0-3", test_no_observed_effect_is_not_generation_failure),
        ("H0-4", test_partial_persistence_preserved),
        ("H0-5", test_collateral_detects_unexpected_changes),
        ("H0-6", test_no_observations_available),
    ]

    passed = 0
    failed = 0

    print("\n=== A3 H0 Self-Test ===\n")

    for name, test in tests:
        try:
            test()
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as exc:
            print(f"FAIL: {name}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"ERROR: {name}: {exc}")
            failed += 1

    print(f"\n{passed}/{len(tests)} tests passed")
    print("\n" + "=" * 50)
    print(f"H0 GATE: {'PASS' if failed == 0 else 'FAIL'}")
    print("=" * 50 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(run_h0())
