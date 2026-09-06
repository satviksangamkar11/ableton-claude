from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest

from serum2.evidence.claim import ClaimEngine
from serum2.evidence.disposition import (
    CONTEXT_INCOMPLETE,
    VALID,
    DispositionLedger,
    evidence_fingerprint,
)
from serum2.evidence.disposition_gate import (
    EvidenceDispositionGate,
    EvidenceNotAdmissible,
)


def make_record(evidence_id="TEST-EVIDENCE"):
    experiment = {
        "mutations": [
            {
                "target_path": "Global0.plainParams.kParamMasterVolume",
                "value": 0.5,
            }
        ],
        "prerequisites": [],
        "mutation_signature": "mutation",
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


def make_adder(eng, gate):
    def admit_add(record, claim_type):
        gate.require_admissible(record)
        return eng.add(record, claim_type)

    return admit_add


def test_inadmissible_evidence_never_reaches_claim_engine():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()

        ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=evidence_fingerprint(record),
            disposition=CONTEXT_INCOMPLETE,
            reason="context incomplete",
            source_refs=("audit.json",),
        )

        gate = EvidenceDispositionGate(ledger)

        # Empty definition set is enough to prove the gate is before add().
        eng = ClaimEngine({})

        admit_add = make_adder(eng, gate)

        with pytest.raises(EvidenceNotAdmissible):
            admit_add(record, "does_not_matter")

        assert record.experiment_id not in eng.records


def test_admissible_evidence_reaches_claim_engine():
    with TemporaryDirectory() as tmp:
        ledger = DispositionLedger(
            Path(tmp) / "ledger.jsonl"
        )

        record = make_record()

        ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=evidence_fingerprint(record),
            disposition=VALID,
            reason="valid",
            source_refs=("witness.py",),
        )

        gate = EvidenceDispositionGate(ledger)

        # Deliberately fake the minimum ClaimEngine insertion boundary.
        # The test is about the disposition gate, not claim qualification.
        class RecordingEngine:
            def __init__(self):
                self.records = {}

            def add(self, record, claim_type):
                self.records[record.experiment_id] = record

        eng = RecordingEngine()

        admit_add = make_adder(eng, gate)

        admit_add(record, "test_claim")

        assert record.experiment_id in eng.records
