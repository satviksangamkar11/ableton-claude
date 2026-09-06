"""
16.5.40d — Evidence disposition admission gate.

The gate sits immediately before ClaimEngine.add().

Policy:
    VALID              -> admissible
    HISTORICAL_VALID   -> admissible
    CONTEXT_INCOMPLETE -> rejected
    INVALIDATED_ACTUATOR -> rejected

This module does not:
- mutate EvidenceRecords
- mutate ClaimGroups
- change CapabilityContract status
- reinterpret measurements
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet

from serum2.evidence.disposition import (
    CONTEXT_INCOMPLETE,
    HISTORICAL_VALID,
    INVALIDATED_ACTUATOR,
    VALID,
    DispositionLedger,
    evidence_fingerprint,
)


ADMISSIBLE_DISPOSITIONS: FrozenSet[str] = frozenset(
    {
        VALID,
        HISTORICAL_VALID,
    }
)

INADMISSIBLE_DISPOSITIONS: FrozenSet[str] = frozenset(
    {
        CONTEXT_INCOMPLETE,
        INVALIDATED_ACTUATOR,
    }
)


class EvidenceDispositionError(RuntimeError):
    """Base class for disposition-gate failures."""


class EvidenceNotDispositioned(EvidenceDispositionError):
    """Evidence has no ledger entry."""


class EvidenceFingerprintMismatch(EvidenceDispositionError):
    """Ledger fingerprint does not match the actual EvidenceRecord."""


class EvidenceNotAdmissible(EvidenceDispositionError):
    """Ledger disposition is explicitly inadmissible."""


@dataclass(frozen=True)
class AdmissionDecision:
    evidence_id: str
    disposition: str
    admissible: bool
    fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "disposition": self.disposition,
            "admissible": self.admissible,
            "fingerprint": self.fingerprint,
        }


class EvidenceDispositionGate:
    """
    Authoritative current-promotion gate.

    No fuzzy matching, family matching, or fallback behavior is permitted.
    Evidence ID and fingerprint must match exactly.
    """

    def __init__(self, ledger: DispositionLedger):
        self.ledger = ledger

    def decide(self, record: Any) -> AdmissionDecision:
        evidence_id = str(record.experiment_id)
        actual_fingerprint = evidence_fingerprint(record)

        event = self.ledger.get(evidence_id)

        if event is None:
            raise EvidenceNotDispositioned(
                f"EvidenceRecord {evidence_id} has no disposition entry"
            )

        if event.evidence_fingerprint != actual_fingerprint:
            raise EvidenceFingerprintMismatch(
                f"EvidenceRecord fingerprint mismatch for {evidence_id}: "
                f"ledger={event.evidence_fingerprint}, "
                f"actual={actual_fingerprint}"
            )

        admissible = event.disposition in ADMISSIBLE_DISPOSITIONS

        return AdmissionDecision(
            evidence_id=evidence_id,
            disposition=event.disposition,
            admissible=admissible,
            fingerprint=actual_fingerprint,
        )

    def require_admissible(self, record: Any) -> AdmissionDecision:
        decision = self.decide(record)

        if not decision.admissible:
            raise EvidenceNotAdmissible(
                f"EvidenceRecord {decision.evidence_id} is not admissible: "
                f"{decision.disposition}"
            )

        return decision