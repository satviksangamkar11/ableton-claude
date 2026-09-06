from types import SimpleNamespace

from serum2.evidence.replay import (
    CONTEXT_INCOMPLETE,
    REPLAYABLE,
    RECORD_MISSING,
    assess_record,
    audit_contract,
)


def make_record(
    *,
    experiment_id="E1",
    include_baseline=False,
    include_stimulus=False,
):
    experiment = {
        "mutations": [
            {
                "target_path": "Global0.plainParams.kParamMasterVolume",
                "value": 0.5,
            }
        ],
        "prerequisites": [],
        "mutation_signature": "mutation-hash",
        "experiment_condition_signature": {
            "hash": "condition-hash",
        },
        "measurement_condition_signatures": (
            [{"hash": "measurement-condition-hash"}]
            if include_stimulus
            else []
        ),
    }

    if include_baseline:
        experiment["baseline_overrides"] = []

    causal = (
        SimpleNamespace(
            measurement_definition_id="mdef-1",
            measurement_condition_signature={
                "hash": "measurement-condition-hash"
            },
        ),
    )

    return SimpleNamespace(
        experiment_id=experiment_id,
        experiment=experiment,
        causal_measurements=causal,
        epoch={"serum": "serum-hash"},
        state_observation={
            "control_hash": "control",
            "treatment_hash": "treatment",
        },
        to_dict=lambda: {
            "experiment_id": experiment_id,
            "experiment": experiment,
        },
    )


def test_replayable_requires_persisted_replay_ingredients():
    record = make_record(
        include_baseline=True,
        include_stimulus=True,
    )

    assessment = assess_record(record)

    # Stimulus values still aren't stored; condition hash alone isn't enough.
    assert assessment.status == CONTEXT_INCOMPLETE
    assert any("stimulus" in reason for reason in assessment.reasons)


def test_missing_baseline_override_is_context_incomplete():
    record = make_record(include_baseline=False)

    assessment = assess_record(record)

    assert assessment.status == CONTEXT_INCOMPLETE
    assert any(
        "baseline_overrides" in reason
        for reason in assessment.reasons
    )


def test_contract_with_missing_record_is_not_replayable():
    contract = SimpleNamespace(
        target="Global0.kParamMasterVolume",
        provenance={
            "supporting_evidence": ["DOES_NOT_EXIST"],
        },
    )

    result = audit_contract(
        "contract-1",
        contract,
        records={},
    )

    assert result.status == RECORD_MISSING
    assert result.missing_evidence == ("DOES_NOT_EXIST",)


def test_real_fixtures_are_discoverable():
    from serum2.evidence.replay import discover_fixture_records

    records = discover_fixture_records()

    assert {"E0", "E1", "E2a", "E2b", "E3"} <= set(records)