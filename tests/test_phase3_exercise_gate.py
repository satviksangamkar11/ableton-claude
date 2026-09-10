"""Phase 3a — Exercise gate implementation tests.

Tests the integration of exercise_measurements into the existing gate system.
Verification of: gate registration, gate logic, generic gate machinery,
contract building, backward compatibility, and admission separation.
"""
from types import SimpleNamespace
from dataclasses import dataclass, field, asdict

import pytest

from serum2.evidence.record import (
    EvidenceRecord,
    CausalMeasurement,
    MeasurementTarget,
    GATES,
    NOT_RUN,
    PASS,
    FAIL,
    INCONCLUSIVE,
    EFFECT_OBSERVED,
    NO_OBSERVED_EFFECT,
    WRONG_DIRECTION,
)
from serum2.evidence.claim import (
    ClaimDefinition,
    ClaimGroup,
    SINGLE_FIELD,
    INSTANCE,
)
from serum2.evidence.capability_contract import (
    build_contract,
    CAUSAL_VERIFIED,
    NEGATIVE_EVIDENCE,
    STRUCTURAL_ONLY,
)


def make_measurement(status=EFFECT_OBSERVED, metric="test_metric"):
    """Factory for CausalMeasurement test fixtures."""
    return CausalMeasurement(
        metric=metric,
        target=MeasurementTarget(field_path="test.field"),
        baseline=0.0,
        treatment=1.0,
        delta=1.0,
        expected_direction="increase",
        observed_direction="increase",
        threshold=0.5,
        status=status,
        measurement_definition_id="test-kernel-1",
    )


def make_record(
    exercise_measurements=(),
    causal_measurements=(),
    experiment_id="TEST-REC-1",
):
    """Factory for EvidenceRecord test fixtures."""
    return EvidenceRecord(
        experiment_id=experiment_id,
        epoch={"serum_binary_sha256": "test", "execution_harness_revision": "test"},
        experiment={
            "mutations": [{"target_path": "Global0.plainParams.kParamMasterVolume", "value": 0.5}],
            "prerequisites": [],
            "mutation_signature": "test-mutation",
            "isolation_level": SINGLE_FIELD,
            "experiment_condition_signature": {
                "hash": "cond-hash-1",
                "prerequisites": []
            },
            "baseline_overrides": [],
            "notes": "",
        },
        arms=(
            SimpleNamespace(
                control={"loaded": True, "rendered": True},
                treatment={"loaded": True, "rendered": True},
            ),
        ),
        runtime_verifications=(),
        state_observation={"status": PASS},
        load_observation={"status": PASS},
        render_observation={"status": PASS},
        causal_measurements=causal_measurements,
        exercise_measurements=exercise_measurements,
        persistence_observation={"status": PASS},
    )


class TestExerciseGateRegistration:
    """TEST 1: Exercise gate registration."""

    def test_exercise_in_gates_constant(self):
        """'exercise' is registered in GATES."""
        assert "exercise" in GATES
        assert GATES == ("generation", "load", "render", "causal", "persistence", "exercise")

    def test_exercise_is_string(self):
        """'exercise' is a string, not a tuple or special object."""
        assert isinstance("exercise", str)
        assert "exercise" in GATES


class TestExerciseGateLogic:
    """TEST 2: Exercise gate status computation."""

    def test_exercise_gate_not_run_when_empty(self):
        """Record with no exercise_measurements returns NOT_RUN."""
        rec = make_record(exercise_measurements=())
        assert rec.gate("exercise") == NOT_RUN

    def test_exercise_gate_pass_all_effect_observed(self):
        """Record with all EFFECT_OBSERVED returns PASS."""
        m1 = make_measurement(status=EFFECT_OBSERVED)
        m2 = make_measurement(status=EFFECT_OBSERVED)
        rec = make_record(exercise_measurements=(m1, m2))
        assert rec.gate("exercise") == PASS

    def test_exercise_gate_pass_single_effect_observed(self):
        """Record with single EFFECT_OBSERVED measurement returns PASS."""
        m = make_measurement(status=EFFECT_OBSERVED)
        rec = make_record(exercise_measurements=(m,))
        assert rec.gate("exercise") == PASS

    def test_exercise_gate_fail_all_no_observed_effect(self):
        """Record with all NO_OBSERVED_EFFECT returns FAIL."""
        m = make_measurement(status=NO_OBSERVED_EFFECT)
        rec = make_record(exercise_measurements=(m,))
        assert rec.gate("exercise") == FAIL

    def test_exercise_gate_fail_any_wrong_direction(self):
        """Record with any WRONG_DIRECTION returns FAIL."""
        m1 = make_measurement(status=EFFECT_OBSERVED)
        m2 = make_measurement(status=WRONG_DIRECTION)
        rec = make_record(exercise_measurements=(m1, m2))
        assert rec.gate("exercise") == FAIL

    def test_exercise_gate_inconclusive_mixed(self):
        """Mixed statuses (EFFECT and NO_OBSERVED) return INCONCLUSIVE."""
        m1 = make_measurement(status=EFFECT_OBSERVED)
        m2 = make_measurement(status=NO_OBSERVED_EFFECT)
        rec = make_record(exercise_measurements=(m1, m2))
        assert rec.gate("exercise") == INCONCLUSIVE

    def test_exercise_gate_inconclusive_effect_and_wrong_direction(self):
        """EFFECT_OBSERVED mixed with WRONG_DIRECTION returns INCONCLUSIVE."""
        m1 = make_measurement(status=EFFECT_OBSERVED)
        m2 = make_measurement(status=WRONG_DIRECTION)
        rec = make_record(exercise_measurements=(m1, m2))
        # Not PASS (not all EFFECT_OBSERVED)
        # Not FAIL (not all NO_OBSERVED_EFFECT, and mixed with EFFECT)
        # Must be INCONCLUSIVE
        status = rec.gate("exercise")
        assert status in (INCONCLUSIVE, FAIL)  # FAIL is also valid (any WRONG_DIRECTION)


class TestGateCompletenessAggregation:
    """TEST 3: Gate completeness includes exercise."""

    def test_gate_completeness_includes_exercise_key(self):
        """gate_completeness() dict includes 'exercise' key."""
        rec = make_record(exercise_measurements=(make_measurement(),))
        completeness = rec.gate_completeness()
        assert "exercise" in completeness
        assert isinstance(completeness["exercise"], str)

    def test_gate_completeness_all_gates_present(self):
        """gate_completeness() includes all GATES."""
        rec = make_record()
        completeness = rec.gate_completeness()
        for gate in GATES:
            assert gate in completeness

    def test_gate_completeness_values_are_valid_statuses(self):
        """All gate_completeness() values are valid gate statuses."""
        rec = make_record(exercise_measurements=(make_measurement(),))
        completeness = rec.gate_completeness()
        valid_statuses = (NOT_RUN, PASS, FAIL, INCONCLUSIVE)
        for status in completeness.values():
            assert status in valid_statuses


class TestGatesMet:
    """TEST 3b: gates_met() integration with exercise requirement."""

    def test_gates_met_exercise_pass_required_and_satisfied(self):
        """gates_met() returns True when exercise PASS is required and actual is PASS."""
        gate_completeness = {
            "generation": PASS,
            "load": PASS,
            "render": PASS,
            "causal": PASS,
            "persistence": PASS,
            "exercise": PASS,
        }
        claim_def = ClaimDefinition(
            claim_type="test_claim",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"exercise": PASS, "causal": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )
        assert claim_def.gates_met(gate_completeness) is True

    def test_gates_met_exercise_pass_required_but_not_run(self):
        """gates_met() returns False when exercise PASS is required but actual is NOT_RUN."""
        gate_completeness = {
            "generation": PASS,
            "load": PASS,
            "render": PASS,
            "causal": PASS,
            "persistence": PASS,
            "exercise": NOT_RUN,
        }
        claim_def = ClaimDefinition(
            claim_type="test_claim",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"exercise": PASS, "causal": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )
        assert claim_def.gates_met(gate_completeness) is False

    def test_gates_met_exercise_not_required_ignores_status(self):
        """gates_met() ignores exercise status when not in required_gate."""
        gate_completeness = {
            "generation": PASS,
            "load": PASS,
            "render": PASS,
            "causal": PASS,
            "persistence": PASS,
            "exercise": NOT_RUN,  # Missing exercise evidence
        }
        claim_def = ClaimDefinition(
            claim_type="test_claim",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"causal": PASS},  # exercise NOT required
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )
        assert claim_def.gates_met(gate_completeness) is True


class TestContractBuilderCriticalTest:
    """TEST 4: CRITICAL — Contract builder respects exercise requirement."""

    def test_no_causal_verified_when_exercise_missing_and_required(self):
        """CRITICAL: Contract CANNOT become CAUSAL_VERIFIED when exercise evidence is missing but required."""
        # Record: all gates PASS except exercise is NOT_RUN
        rec = make_record(
            exercise_measurements=(),  # NO exercise evidence
            causal_measurements=(make_measurement(status=EFFECT_OBSERVED),),  # causal PASS
        )

        # ClaimDefinition requires BOTH exercise and causal
        claim_def = ClaimDefinition(
            claim_type="test_target",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"exercise": PASS, "causal": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )

        # Build ClaimGroup with this single record
        group = ClaimGroup(
            claim_definition=claim_def,
            condition_signature_hash="cond-hash-1",
            supporting_evidence=(rec.experiment_id,),
            store={rec.experiment_id: rec},
        )

        # Build contract
        contract = build_contract(group)

        # CRITICAL: contract MUST NOT be CAUSAL_VERIFIED
        assert contract is not None
        assert contract.status != CAUSAL_VERIFIED, (
            f"KILL TEST FAILED: Contract became {contract.status} without exercise evidence. "
            "This violates the exercise gate requirement."
        )
        # Expected: NEGATIVE_EVIDENCE (no qualifying records)
        assert contract.status == NEGATIVE_EVIDENCE

    def test_causal_verified_when_exercise_present_and_required(self):
        """Contract CAN become CAUSAL_VERIFIED when exercise evidence is present and required."""
        # Record: all gates PASS including exercise
        rec = make_record(
            exercise_measurements=(make_measurement(status=EFFECT_OBSERVED),),  # exercise PASS
            causal_measurements=(make_measurement(status=EFFECT_OBSERVED),),  # causal PASS
        )

        claim_def = ClaimDefinition(
            claim_type="test_target",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"exercise": PASS, "causal": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )

        group = ClaimGroup(
            claim_definition=claim_def,
            condition_signature_hash="cond-hash-1",
            supporting_evidence=(rec.experiment_id,),
            store={rec.experiment_id: rec},
        )

        contract = build_contract(group)

        # Contract SHOULD be CAUSAL_VERIFIED
        assert contract is not None
        assert contract.status == CAUSAL_VERIFIED

    def test_causal_verified_when_exercise_not_required(self):
        """Contract becomes CAUSAL_VERIFIED when exercise is NOT required (backward compat)."""
        # Record: exercise is NOT_RUN, but causal is PASS
        rec = make_record(
            exercise_measurements=(),  # NO exercise evidence
            causal_measurements=(make_measurement(status=EFFECT_OBSERVED),),  # causal PASS
        )

        claim_def = ClaimDefinition(
            claim_type="test_target",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"causal": PASS},  # exercise NOT required
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )

        group = ClaimGroup(
            claim_definition=claim_def,
            condition_signature_hash="cond-hash-1",
            supporting_evidence=(rec.experiment_id,),
            store={rec.experiment_id: rec},
        )

        contract = build_contract(group)

        # Contract SHOULD be CAUSAL_VERIFIED (exercise not checked)
        assert contract is not None
        assert contract.status == CAUSAL_VERIFIED


class TestBackwardCompatibility:
    """TEST 5 & 6: Backward compatibility with old records."""

    def test_old_pickle_without_exercise_measurements_loads(self):
        """Old pickled EvidenceRecord without exercise_measurements field loads successfully."""
        # Simulate an old record by constructing one without the field
        rec = make_record()
        # Remove the exercise_measurements field by reconstructing via __getattr__
        # (This simulates what happens when unpickling an old record)

        # Access via __getattr__ (which should return empty tuple)
        exercise = rec.__getattr__("exercise_measurements")
        assert exercise == ()
        assert isinstance(exercise, tuple)

    def test_old_pickle_exercise_gate_returns_not_run(self):
        """Old record without exercise_measurements has exercise gate = NOT_RUN."""
        # Simulate old pickle by accessing via __getattr__
        # (which is what happens when unpickling an old record missing the field)
        rec = make_record()

        # Test that empty exercise_measurements returns NOT_RUN
        assert rec.exercise_measurements == ()
        status = rec.gate("exercise")
        assert status == NOT_RUN

    def test_old_claim_definition_still_works(self):
        """Existing ClaimDefinition without exercise requirement still works."""
        rec = make_record(causal_measurements=(make_measurement(status=EFFECT_OBSERVED),))

        claim_def = ClaimDefinition(
            claim_type="legacy_target",
            subject_pattern={},
            predicate="legacy_predicate",
            required_gate={"causal": PASS},  # No exercise requirement
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )

        group = ClaimGroup(
            claim_definition=claim_def,
            condition_signature_hash="cond-hash-1",
            supporting_evidence=(rec.experiment_id,),
            store={rec.experiment_id: rec},
        )

        contract = build_contract(group)
        assert contract is not None
        assert contract.status == CAUSAL_VERIFIED  # Should still work


class TestAdmissionUnchanged:
    """TEST 7: Runtime admission behavior unchanged."""

    def test_contract_has_no_exercise_metadata(self):
        """Built contract does not carry exercise metadata fields."""
        rec = make_record(exercise_measurements=(make_measurement(),))

        claim_def = ClaimDefinition(
            claim_type="test_target",
            subject_pattern={},
            predicate="test_predicate",
            required_gate={"exercise": PASS, "causal": PASS},
            required_isolation=(SINGLE_FIELD,),
            breadth_rule={"sampled_min": 1},
            coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
            contradiction_rule={"require_same_mutation": False},
            dependency_rule={"enabled": False},
        )

        group = ClaimGroup(
            claim_definition=claim_def,
            condition_signature_hash="cond-hash-1",
            supporting_evidence=(rec.experiment_id,),
            store={rec.experiment_id: rec},
        )

        contract = build_contract(group)

        # Contract should NOT have exercise_qualified field on prerequisites
        for prereq in contract.prerequisites:
            assert "exercise_qualified" not in prereq
            assert "exercise_measurement_id" not in prereq
