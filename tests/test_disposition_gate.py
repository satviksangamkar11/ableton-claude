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
from serum2.evidence.disposition_gate import (
    EvidenceDispositionGate,
    EvidenceFingerprintMismatch,
    EvidenceNotAdmissible,
    EvidenceNotDispositioned,
)


def make_record(value=0.5, evidence_id="TEST-EVIDENCE"):
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
        experiment_id=evidence_id,
        experiment=experiment,
        causal_measurements=(),
        to_dict=lambda: {
            "experiment_id": evidence_id,
            "experiment": experiment,
        },
    )


def test_valid_is_admissible():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()
        fp = evidence_fingerprint(record)

        ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=fp,
            disposition=VALID,
            reason="valid witness",
            source_refs=("witness.py",),
        )

        decision = EvidenceDispositionGate(
            ledger
        ).require_admissible(record)

        assert decision.admissible is True
        assert decision.disposition == VALID


def test_historical_valid_is_admissible():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()
        fp = evidence_fingerprint(record)

        ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=fp,
            disposition=HISTORICAL_VALID,
            reason="historical witness recovered",
            source_refs=("historical.py",),
        )

        decision = EvidenceDispositionGate(
            ledger
        ).require_admissible(record)

        assert decision.admissible is True
        assert decision.disposition == HISTORICAL_VALID


def test_context_incomplete_is_rejected():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()
        fp = evidence_fingerprint(record)

        ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=fp,
            disposition=CONTEXT_INCOMPLETE,
            reason="no historical witness",
            source_refs=("audit.json",),
        )

        gate = EvidenceDispositionGate(ledger)

        with pytest.raises(EvidenceNotAdmissible):
            gate.require_admissible(record)


def test_invalidated_actuator_is_rejected():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()
        fp = evidence_fingerprint(record)

        ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=fp,
            disposition=INVALIDATED_ACTUATOR,
            reason="explicit actuator contamination",
            source_refs=("contamination.json",),
        )

        gate = EvidenceDispositionGate(ledger)

        with pytest.raises(EvidenceNotAdmissible):
            gate.require_admissible(record)


def test_missing_disposition_is_rejected():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()

        gate = EvidenceDispositionGate(ledger)

        with pytest.raises(EvidenceNotDispositioned):
            gate.require_admissible(record)


def test_fingerprint_mismatch_is_rejected():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record_a = make_record(value=0.5)
        record_b = make_record(value=0.25)

        ledger.append(
            evidence_id=record_a.experiment_id,
            evidence_fingerprint_value=evidence_fingerprint(record_a),
            disposition=VALID,
            reason="valid witness",
            source_refs=("witness.py",),
        )

        gate = EvidenceDispositionGate(ledger)

        with pytest.raises(EvidenceFingerprintMismatch):
            gate.require_admissible(record_b)