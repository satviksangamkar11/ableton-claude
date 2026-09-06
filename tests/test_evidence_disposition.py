from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from serum2.evidence.disposition import (
    CONTEXT_INCOMPLETE,
    HISTORICAL_VALID,
    INVALIDATED_ACTUATOR,
    VALID,
    DispositionLedger,
    evidence_fingerprint,
)


def make_record(value=0.5):
    experiment = {
        "mutations": [
            {
                "target_path": "Global0.plainParams.kParamMasterVolume",
                "value": value,
            }
        ],
        "prerequisites": [],
        "mutation_signature": f"mutation-{value}",
        "experiment_condition_signature": "condition",
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

    assert (
        evidence_fingerprint(record)
        == evidence_fingerprint(record)
    )


def test_append_and_current():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.jsonl"
        ledger = DispositionLedger(path)

        record = make_record()

        event = ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=evidence_fingerprint(record),
            disposition=VALID,
            reason="exact historical witness",
            source_refs=("experiment.py",),
        )

        assert event.evidence_id == "TEST-EVIDENCE"
        assert ledger.get("TEST-EVIDENCE").disposition == VALID


def test_ledger_is_append_only():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.jsonl"
        ledger = DispositionLedger(path)

        record = make_record()

        fp = evidence_fingerprint(record)

        ledger.append(
            evidence_id="TEST-EVIDENCE",
            evidence_fingerprint_value=fp,
            disposition=HISTORICAL_VALID,
            reason="historical",
        )

        with pytest.raises(ValueError):
            ledger.append(
                evidence_id="TEST-EVIDENCE",
                evidence_fingerprint_value=fp,
                disposition=VALID,
                reason="silent upgrade",
            )


def test_fingerprint_change_is_rejected():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.jsonl"
        ledger = DispositionLedger(path)

        record_a = make_record(0.5)
        record_b = make_record(0.25)

        ledger.append(
            evidence_id="TEST-EVIDENCE",
            evidence_fingerprint_value=evidence_fingerprint(record_a),
            disposition=HISTORICAL_VALID,
            reason="historical",
        )

        with pytest.raises(ValueError):
            ledger.append(
                evidence_id="TEST-EVIDENCE",
                evidence_fingerprint_value=evidence_fingerprint(record_b),
                disposition=VALID,
                reason="changed evidence",
            )


def test_invalidated_actuator_is_supported():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.jsonl"
        ledger = DispositionLedger(path)

        record = make_record()

        ledger.append(
            evidence_id="TEST-EVIDENCE",
            evidence_fingerprint_value=evidence_fingerprint(record),
            disposition=INVALIDATED_ACTUATOR,
            reason="explicit contamination manifest",
            source_refs=("16.5.40-manifest",),
        )

        assert (
            ledger.get("TEST-EVIDENCE").disposition
            == INVALIDATED_ACTUATOR
        )


def test_integrity_detects_duplicate_event_id():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "ledger.jsonl"
        ledger = DispositionLedger(path)

        record = make_record()

        fp = evidence_fingerprint(record)

        ledger.append(
            evidence_id="TEST-EVIDENCE",
            evidence_fingerprint_value=fp,
            disposition=CONTEXT_INCOMPLETE,
            reason="missing witness",
            event_id="fixed-event-id",
        )

        with pytest.raises(ValueError):
            ledger.append(
                evidence_id="TEST-EVIDENCE",
                evidence_fingerprint_value=fp,
                disposition=CONTEXT_INCOMPLETE,
                reason="duplicate",
                event_id="fixed-event-id",
            )