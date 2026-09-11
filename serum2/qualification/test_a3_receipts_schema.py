#!/usr/bin/env python3
"""Schema validation for a3_receipts.py

Tests that:
- GateResult can be constructed with valid statuses
- PersistenceResult enforces P1/P2/P3 independence
- MutationReceipt validates target identity
- Serialization works
"""

import json
from a3_receipts import (
    GateResult,
    PersistenceResult,
    MutationReceipt,
    PASS,
    NOT_RUN,
    gate_pass,
    gate_not_run,
)


def test_gate_result_valid():
    """Valid GateResult construction."""
    result = GateResult(
        status=PASS,
        reason="test reason",
    )
    assert result.status == PASS
    print("PASS GateResult with valid status")


def test_gate_result_invalid():
    """Invalid GateResult status raises."""
    try:
        GateResult(status="INVALID_STATUS")
        print("FAIL GateResult should reject invalid status")
        return False
    except ValueError:
        print("PASS GateResult rejects invalid status")
        return True


def test_gate_helpers():
    """Helper functions work."""
    p = gate_pass("test passed")
    n = gate_not_run("test not run")

    assert p.status == PASS
    assert n.status == NOT_RUN
    print("PASS Gate helper functions")


def test_persistence_independence():
    """P1/P2/P3 are separately represented."""
    persistence = PersistenceResult(
        p1_same_engine=gate_pass("P1 passed"),
        p2_new_instance=gate_not_run("P2 not tested"),
        p3_fresh_process=gate_not_run("P3 not tested"),
        overall=gate_not_run("no overall persistence observation"),
    )

    assert persistence.p1_same_engine.status == PASS
    assert persistence.p2_new_instance.status == NOT_RUN
    assert persistence.p3_fresh_process.status == NOT_RUN
    print("PASS PersistenceResult keeps P1/P2/P3 independent")


def test_mutation_receipt_construction():
    """Valid MutationReceipt."""
    receipt = MutationReceipt(
        experiment_id="H0",
        semantic_id="synthetic.target",
        capability_key="synthetic_capability",
        vst3_name="Synthetic Parameter",
        vst3_index=123,
        generation=gate_pass("synthetic generation passed"),
        persistence=PersistenceResult(
            p1_same_engine=gate_not_run("P1 not tested"),
            p2_new_instance=gate_not_run("P2 not tested"),
            p3_fresh_process=gate_not_run("P3 not tested"),
            overall=gate_not_run("no persistence observation"),
        ),
        behavior=gate_not_run("no behavior measurement"),
        collateral=gate_pass("no unexpected changes"),
        restoration=gate_not_run("restoration not implemented"),
        evidence_record_id="H0",
        generation_verified=True,
        transport_mutable=True,
    )

    assert receipt.semantic_id == "synthetic.target"
    assert receipt.generation_verified is True
    assert receipt.persistent_p1 is False
    print("PASS MutationReceipt construction")


def test_mutation_receipt_validation():
    """MutationReceipt rejects invalid inputs."""
    try:
        MutationReceipt(
            experiment_id="",  # Invalid: empty
            semantic_id="test",
            capability_key="test",
            vst3_name="test",
            vst3_index=0,
            generation=gate_pass("test"),
            persistence=PersistenceResult(
                p1_same_engine=gate_not_run("test"),
                p2_new_instance=gate_not_run("test"),
                p3_fresh_process=gate_not_run("test"),
                overall=gate_not_run("test"),
            ),
            behavior=gate_not_run("test"),
            collateral=gate_not_run("test"),
            restoration=gate_not_run("test"),
        )
        print("FAIL MutationReceipt should reject empty experiment_id")
        return False
    except ValueError:
        print("PASS MutationReceipt validates experiment_id")
        return True


def test_serialization():
    """Receipt serializes to JSON-compatible dict."""
    receipt = MutationReceipt(
        experiment_id="H0",
        semantic_id="test.target",
        capability_key="test_cap",
        vst3_name="Test Param",
        vst3_index=99,
        generation=gate_pass("test"),
        persistence=PersistenceResult(
            p1_same_engine=gate_not_run("P1"),
            p2_new_instance=gate_not_run("P2"),
            p3_fresh_process=gate_not_run("P3"),
            overall=gate_not_run("overall"),
        ),
        behavior=gate_not_run("behavior"),
        collateral=gate_pass("collateral"),
        restoration=gate_not_run("restoration"),
    )

    data = receipt.to_dict()

    # Verify it's JSON-serializable
    json_str = json.dumps(data)
    parsed = json.loads(json_str)

    assert parsed["semantic_id"] == "test.target"
    assert parsed["generation"]["status"] == PASS
    assert parsed["persistence"]["p1_same_engine"]["status"] == NOT_RUN
    assert parsed["restoration"]["status"] == NOT_RUN

    print("PASS MutationReceipt serializes to JSON")


def main():
    print("\n=== A3 Receipt Schema Validation ===\n")

    tests = [
        test_gate_result_valid,
        test_gate_result_invalid,
        test_gate_helpers,
        test_persistence_independence,
        test_mutation_receipt_construction,
        test_mutation_receipt_validation,
        test_serialization,
    ]

    passed = 0
    for test in tests:
        try:
            result = test()
            if result is not False:
                passed += 1
        except Exception as e:
            print(f"FAIL {test.__name__}: {e}")

    print(f"\n{passed}/{len(tests)} tests passed")
    print("\n{'='*50}")
    print(f"A3 Receipt Schema: {'PASS' if passed == len(tests) else 'FAIL'}")
    print(f"{'='*50}\n")

    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    raise SystemExit(main())
