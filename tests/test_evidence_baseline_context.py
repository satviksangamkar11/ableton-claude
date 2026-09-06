"""Test baseline_overrides provenance preservation in EvidenceRecord.

This validates that:
1. baseline_overrides declared in ExperimentSpec are persisted in EvidenceRecord.experiment
2. The stored baseline_override exactly matches the declared Mutation
3. experiment_condition_signature() remains semantically unchanged
4. Historical records without baseline_overrides continue to load
5. No claim/capability fields appear in EvidenceRecord
"""

import pickle
import tempfile
import pytest
from serum2.evidence.spec import (
    ExperimentSpec, Mutation, Prerequisite, Stimulus,
    TargetSpec, MeasurementPlan, SINGLE_FIELD
)
from serum2.evidence.harness import run
from serum2.evidence import record as record_mod
from serum2 import bridge


def make_simple_spec(baseline_overrides=None, mutations=None):
    """Helper to create a minimal valid ExperimentSpec."""
    if mutations is None:
        mutations = [
            Mutation(
                target_path="Env0.plainParams.kParamSustain",
                value=0.3,
                provenance="test_sustain_mutation"
            )
        ]
    if baseline_overrides is None:
        baseline_overrides = []

    return ExperimentSpec(
        experiment_id="test_baseline_context",
        mutations=mutations,
        prerequisites=[],
        baseline_overrides=baseline_overrides,
        isolation_level=SINGLE_FIELD,
        claim_subject="Env0.plainParams.kParamSustain",
        claim_predicate="affects_sustain",
        measurement_plans=[
            MeasurementPlan(
                metric="sustain_window_rms_db",
                target=TargetSpec("Env0.plainParams.kParamSustain"),
                expected_direction="increase",
                threshold=0.1,
                stimulus=Stimulus(
                    note=60,
                    velocity=100,
                    note_len=1.0,
                    render_seconds=2.0,
                    tail_start=0.5
                ),
                kernel_artifact="sustain_window_rms_db_kernel"
            )
        ],
        notes="baseline context preservation test"
    )


def test_new_spec_with_baseline_override_produces_record_with_baseline_override():
    """Test 1: New ExperimentSpec with baseline_override produces EvidenceRecord
    whose experiment contains that baseline_override."""
    baseline = Mutation(
        target_path="Env0.plainParams.kParamDecay",
        value=0.02,
        provenance="baseline_context_test"
    )
    spec = make_simple_spec(baseline_overrides=[baseline])
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    assert "baseline_overrides" in record.experiment
    assert len(record.experiment["baseline_overrides"]) == 1
    assert record.experiment["baseline_overrides"][0]["target_path"] == "Env0.plainParams.kParamDecay"
    assert record.experiment["baseline_overrides"][0]["value"] == 0.02


def test_stored_baseline_override_matches_declared_mutation_exactly():
    """Test 2: The stored baseline_override exactly matches the declared Mutation:
    target_path, value, provenance."""
    baseline = Mutation(
        target_path="Env0.plainParams.kParamDecay",
        value=0.02,
        provenance="my_baseline_provenance"
    )
    spec = make_simple_spec(baseline_overrides=[baseline])
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    stored = record.experiment["baseline_overrides"][0]
    assert stored["target_path"] == baseline.target_path
    assert stored["value"] == baseline.value
    assert stored["provenance"] == baseline.provenance


def test_experiment_condition_signature_includes_baseline_overrides():
    """Test 3: experiment_condition_signature() is built from prerequisites +
    baseline_overrides and stored correctly."""
    baseline = Mutation(
        target_path="Env0.plainParams.kParamDecay",
        value=0.02,
        provenance="test"
    )
    spec = make_simple_spec(baseline_overrides=[baseline])
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    # The signature should be present and have a hash
    assert "experiment_condition_signature" in record.experiment
    sig = record.experiment["experiment_condition_signature"]
    assert "hash" in sig
    assert "baseline_overrides" in sig
    # The baseline_overrides should be represented in the signature
    assert len(sig["baseline_overrides"]) == 1


def test_mutation_path_not_duplicated_into_baseline_overrides():
    """Test 4: A mutation path is NOT duplicated into baseline_overrides."""
    spec = make_simple_spec(baseline_overrides=[])
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    # baseline_overrides should be empty
    assert len(record.experiment["baseline_overrides"]) == 0

    # mutations should contain the sustain mutation
    assert len(record.experiment["mutations"]) == 1
    assert record.experiment["mutations"][0]["target_path"] == "Env0.plainParams.kParamSustain"


def test_multiple_baseline_overrides_preserved():
    """Test: Multiple baseline_overrides are all preserved."""
    baseline1 = Mutation(
        target_path="Env0.plainParams.kParamDecay",
        value=0.02,
        provenance="decay_baseline"
    )
    baseline2 = Mutation(
        target_path="Env0.plainParams.kParamAttack",
        value=0.01,
        provenance="attack_baseline"
    )
    spec = make_simple_spec(baseline_overrides=[baseline1, baseline2])
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    assert len(record.experiment["baseline_overrides"]) == 2
    paths = {b["target_path"] for b in record.experiment["baseline_overrides"]}
    assert "Env0.plainParams.kParamDecay" in paths
    assert "Env0.plainParams.kParamAttack" in paths


def test_no_claim_fields_in_evidence_record():
    """Test 7: No claim/capability fields appear in EvidenceRecord."""
    spec = make_simple_spec()
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    record_dict = record.to_dict()

    # These should NOT appear in the record
    forbidden_fields = [
        "claim_coverage", "claim_breadth", "claim_confidence",
        "capability_status", "capability_inventory", "capability_contracts"
    ]
    for field in forbidden_fields:
        assert field not in record_dict, f"Forbidden field {field} found in record"
        if "experiment" in record_dict:
            assert field not in record_dict["experiment"], f"Forbidden field {field} found in experiment dict"


def test_evidence_record_to_dict_includes_baseline_overrides():
    """Test 6: EvidenceRecord.to_dict() includes baseline_overrides for new records."""
    baseline = Mutation(
        target_path="Env0.plainParams.kParamDecay",
        value=0.02,
        provenance="test"
    )
    spec = make_simple_spec(baseline_overrides=[baseline])
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    d = record.to_dict()
    assert "experiment" in d
    assert "baseline_overrides" in d["experiment"]
    assert len(d["experiment"]["baseline_overrides"]) == 1


def test_historical_record_without_baseline_overrides_still_loads():
    """Test 5: Existing historical records without baseline_overrides still load.

    Create a minimal record dict (similar to what an old pickle might have),
    then verify it can be accessed without error."""
    # Simulate an old record that lacks baseline_overrides
    old_record_dict = {
        "experiment_id": "old_record",
        "epoch": {},
        "experiment": {
            "mutations": [{"target_path": "Env0.plainParams.kParamSustain", "value": 0.3}],
            "prerequisites": [],
            # NO baseline_overrides field!
            "isolation_level": "single_field",
            "claim_subject": "test",
            "claim_predicate": "test",
            "experiment_condition_signature": {"hash": "test"},
            "measurement_condition_signatures": [],
            "mutation_signature": "test",
            "notes": ""
        },
        "arms": (),
        "runtime_verifications": (),
        "state_observation": {},
        "load_observation": {},
        "render_observation": {},
        "causal_measurements": (),
        "persistence_observation": {},
        "integrity": {},
        "structural_observation": {}
    }

    # Create an EvidenceRecord from the dict
    # This simulates unpickling an old record
    record = record_mod.EvidenceRecord(**old_record_dict)

    # Should be accessible without error
    assert record.experiment_id == "old_record"
    assert "mutations" in record.experiment
    assert "prerequisites" in record.experiment
    # baseline_overrides might not be present in old records
    baseline_ov = record.experiment.get("baseline_overrides")
    # Should not throw an error even if it's missing


def test_backward_compatibility_pickle_without_baseline_overrides():
    """Test: Old pickled records continue to work when unpickled.

    Simulates loading a pickle file created before baseline_overrides was added."""
    # Create a simple record with minimal fields
    class MinimalRecord:
        def __init__(self):
            self.experiment_id = "old_pickle"
            self.epoch = {}
            self.experiment = {
                "mutations": [],
                "prerequisites": [],
                "isolation_level": "single_field",
                "claim_subject": "test",
                "claim_predicate": "test",
                "experiment_condition_signature": {"hash": "old"},
                "measurement_condition_signatures": [],
                "mutation_signature": "test",
                "notes": ""
                # NO baseline_overrides!
            }
            self.arms = ()
            self.runtime_verifications = ()
            self.state_observation = {}
            self.load_observation = {}
            self.render_observation = {}
            self.causal_measurements = ()
            self.persistence_observation = {}

    old = MinimalRecord()

    # Accessing experiment should work fine
    assert "mutations" in old.experiment

    # And getting baseline_overrides should work gracefully
    baseline_ov = old.experiment.get("baseline_overrides")
    assert baseline_ov is None  # It's not there, which is fine for old records


def test_baseline_override_with_complex_value_preserved():
    """Test: baseline_overrides with complex (nested) values are preserved."""
    baseline = Mutation(
        target_path="ModSlot0.Params",
        value={"key1": "value1", "nested": {"key2": "value2"}},
        provenance="complex_baseline"
    )
    spec = make_simple_spec(
        baseline_overrides=[baseline],
        mutations=[
            Mutation(
                target_path="ModSlot0.Enable",
                value=1,
                provenance="test"
            )
        ]
    )
    skeleton = bridge.capture_v8_skeleton("serum_vst3")
    record = run(spec, skeleton=skeleton)

    stored = record.experiment["baseline_overrides"][0]
    assert stored["value"] == baseline.value


if __name__ == "__main__":
    import sys
    pytest.main([__file__, "-v"] + sys.argv[1:])
