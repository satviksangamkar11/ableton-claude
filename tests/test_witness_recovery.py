from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from serum2.evidence.witness_recovery import (
    CONTEXT_INCOMPLETE,
    HISTORICAL_VALID,
    INVALIDATED_ACTUATOR,
    VALID,
    discover_artifacts,
    evidence_fingerprint,
    recover_from_record_and_artifacts,
)


def make_record():
    experiment = {
        "mutations": [
            {
                "target_path": "Global0.plainParams.kParamMasterVolume",
                "value": 0.5,
            }
        ],
        "prerequisites": [],
        "mutation_signature": "mutation-hash",
        "experiment_condition_signature": "condition-hash",
    }

    return SimpleNamespace(
        experiment_id="TEST-EVIDENCE",
        experiment=experiment,
        causal_measurements=(),
        to_dict=lambda: {
            "experiment_id": "TEST-EVIDENCE",
            "experiment": experiment,
        },
    )


def test_fingerprint_is_stable():
    record = make_record()

    assert evidence_fingerprint(record) == evidence_fingerprint(record)


def test_no_witness_is_context_incomplete():
    record = make_record()

    result = recover_from_record_and_artifacts(
        record,
        (),
    )

    assert result.status == CONTEXT_INCOMPLETE


def test_explicit_contamination_wins():
    record = make_record()

    contamination = SimpleNamespace(
        evidence_id="TEST-EVIDENCE",
        reason="known test contamination",
        source_ref="16.5.40b-test",
    )

    result = recover_from_record_and_artifacts(
        record,
        (),
        contamination=contamination,
    )

    assert result.status == INVALIDATED_ACTUATOR


def test_historical_artifact_is_not_silent_reconstruction():
    record = make_record()

    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        artifact = root / "historical_test.py"
        artifact.write_text(
            """
baseline_overrides = {}
measurement_condition = {}
stimulus = {}
TEST-EVIDENCE
""",
            encoding="utf-8",
        )

        refs = discover_artifacts(
            root,
            "TEST-EVIDENCE",
        )

        assert len(refs) == 1

        result = recover_from_record_and_artifacts(
            record,
            refs,
        )

        assert result.status == VALID


def test_historical_reference_without_complete_recipe_is_historical_valid():
    record = make_record()

    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        artifact = root / "historical_test.py"
        artifact.write_text(
            """
TEST-EVIDENCE
# historical witness exists
""",
            encoding="utf-8",
        )

        refs = discover_artifacts(
            root,
            "TEST-EVIDENCE",
        )

        result = recover_from_record_and_artifacts(
            record,
            refs,
        )

        assert result.status == HISTORICAL_VALID