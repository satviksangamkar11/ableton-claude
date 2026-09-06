"""
16.5.40c — External Evidence Disposition Ledger.

The ledger is deliberately outside EvidenceRecord.

Properties
----------
- EvidenceRecord remains immutable.
- Ledger is append-only event history.
- Every event carries an EvidenceRecord content fingerprint.
- A changed EvidenceRecord cannot silently inherit an old disposition.
- No capability state is modified here.
- No ClaimGroup is modified here.
- No promotion occurs here.

Disposition meanings
--------------------
VALID
    Evidence has an exact/recoverable historical witness.

HISTORICAL_VALID
    Historical witness exists, but exact replay is incomplete.

CONTEXT_INCOMPLETE
    Required historical context could not be recovered.

INVALIDATED_ACTUATOR
    Explicit external adjudication says the actuator path was contaminated.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Tuple


VALID = "VALID"
HISTORICAL_VALID = "HISTORICAL_VALID"
CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"
INVALIDATED_ACTUATOR = "INVALIDATED_ACTUATOR"

ALL_STATUSES = frozenset(
    {
        VALID,
        HISTORICAL_VALID,
        CONTEXT_INCOMPLETE,
        INVALIDATED_ACTUATOR,
    }
)

SCHEMA_VERSION = "16.5.40c.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, (set, frozenset)):
        return sorted(value)

    return repr(value)


def stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def evidence_fingerprint(record: Any) -> str:
    """
    Fingerprint the immutable EvidenceRecord representation.
    """
    if hasattr(record, "to_dict"):
        payload = record.to_dict()
    elif hasattr(record, "__dict__"):
        payload = dict(record.__dict__)
    else:
        payload = repr(record)

    return hashlib.sha256(
        stable_json(payload)
    ).hexdigest()


@dataclass(frozen=True)
class DispositionEvent:
    schema_version: str
    event_id: str
    recorded_at: str
    evidence_id: str
    evidence_fingerprint: str
    disposition: str
    reason: str
    source_refs: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DispositionLedger:
    """
    Append-only JSONL ledger.

    Each line is an independent immutable event.

    Latest disposition for an evidence ID is the latest event in file order.
    A fingerprint change for an already-known evidence ID is rejected unless
    the caller explicitly starts a new evidence identity.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def _read_events(self) -> list[DispositionEvent]:
        if not self.path.exists():
            return []

        events: list[DispositionEvent] = []

        with self.path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()

                if not line:
                    continue

                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid JSON at {self.path}:{line_number}"
                    ) from exc

                event = self._parse_event(payload)
                events.append(event)

        return events

    @staticmethod
    def _parse_event(
        payload: Mapping[str, Any],
    ) -> DispositionEvent:
        required = {
            "schema_version",
            "event_id",
            "recorded_at",
            "evidence_id",
            "evidence_fingerprint",
            "disposition",
            "reason",
            "source_refs",
        }

        missing = sorted(
            required - set(payload.keys())
        )

        if missing:
            raise ValueError(
                f"disposition event missing fields: {missing}"
            )

        disposition = str(payload["disposition"])

        if disposition not in ALL_STATUSES:
            raise ValueError(
                f"unknown disposition: {disposition}"
            )

        source_refs = payload["source_refs"]

        if not isinstance(source_refs, list):
            raise ValueError(
                "source_refs must be a list"
            )

        return DispositionEvent(
            schema_version=str(payload["schema_version"]),
            event_id=str(payload["event_id"]),
            recorded_at=str(payload["recorded_at"]),
            evidence_id=str(payload["evidence_id"]),
            evidence_fingerprint=str(
                payload["evidence_fingerprint"]
            ),
            disposition=disposition,
            reason=str(payload["reason"]),
            source_refs=tuple(
                str(x) for x in source_refs
            ),
        )

    def events(self) -> Tuple[DispositionEvent, ...]:
        return tuple(self._read_events())

    def current(self) -> dict[str, DispositionEvent]:
        """
        Return latest event per evidence ID.
        """
        latest: dict[str, DispositionEvent] = {}

        for event in self._read_events():
            latest[event.evidence_id] = event

        return latest

    def get(
        self,
        evidence_id: str,
    ) -> Optional[DispositionEvent]:
        return self.current().get(str(evidence_id))

    def append(
        self,
        *,
        evidence_id: str,
        evidence_fingerprint_value: str,
        disposition: str,
        reason: str,
        source_refs: Iterable[str] = (),
        event_id: Optional[str] = None,
        recorded_at: Optional[str] = None,
    ) -> DispositionEvent:
        """
        Append a new event.

        Safety rules:
        1. Unknown dispositions are rejected.
        2. An existing evidence ID cannot silently switch fingerprints.
        3. Duplicate event IDs are rejected.
        4. Existing lines are never edited.
        """
        evidence_id = str(evidence_id)
        evidence_fingerprint_value = str(
            evidence_fingerprint_value
        )
        disposition = str(disposition)

        if disposition not in ALL_STATUSES:
            raise ValueError(
                f"unknown disposition: {disposition}"
            )

        existing_events = self._read_events()

        if event_id is None:
            event_id = self._make_event_id(
                evidence_id=evidence_id,
                evidence_fingerprint_value=evidence_fingerprint_value,
                disposition=disposition,
                reason=reason,
                source_refs=tuple(
                    str(x) for x in source_refs
                ),
            )

        event_id = str(event_id)

        source_refs_tuple = tuple(
            sorted(set(str(x) for x in source_refs))
        )

        for existing in existing_events:
            if existing.event_id == event_id:
                raise ValueError(
                    f"duplicate disposition event_id: {event_id}"
                )

            if (
                existing.evidence_id == evidence_id
                and existing.evidence_fingerprint
                != evidence_fingerprint_value
            ):
                raise ValueError(
                    "evidence fingerprint changed for existing "
                    f"evidence ID {evidence_id}: "
                    f"{existing.evidence_fingerprint} != "
                    f"{evidence_fingerprint_value}"
                )

            if existing.evidence_id == evidence_id:
                if not source_refs_tuple:
                    raise ValueError(
                        "re-disposition requires non-empty source_refs "
                        f"for evidence ID {evidence_id}"
                    )

                if (
                    existing.disposition == disposition
                    and set(source_refs_tuple) <= set(existing.source_refs)
                ):
                    raise ValueError(
                        "re-disposition does not contain new supporting "
                        f"source_refs for evidence ID {evidence_id}"
                    )

        event = DispositionEvent(
            schema_version=SCHEMA_VERSION,
            event_id=event_id,
            recorded_at=recorded_at or utc_now(),
            evidence_id=evidence_id,
            evidence_fingerprint=evidence_fingerprint_value,
            disposition=disposition,
            reason=str(reason),
            source_refs=source_refs_tuple,
        )

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as f:
            f.write(
                json.dumps(
                    event.to_dict(),
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )

        return event

    @staticmethod
    def _make_event_id(
        *,
        evidence_id: str,
        evidence_fingerprint_value: str,
        disposition: str,
        reason: str,
        source_refs: Tuple[str, ...],
    ) -> str:
        payload = {
            "evidence_id": evidence_id,
            "evidence_fingerprint": evidence_fingerprint_value,
            "disposition": disposition,
            "reason": reason,
            "source_refs": source_refs,
        }

        digest = hashlib.sha256(
            stable_json(payload)
        ).hexdigest()

        return f"disp-{digest[:24]}"

    def verify_integrity(self) -> None:
        """
        Validate the entire append-only event stream.
        """
        events = self._read_events()

        seen_event_ids: set[str] = set()
        fingerprints: dict[str, str] = {}

        for event in events:
            if event.event_id in seen_event_ids:
                raise ValueError(
                    f"duplicate event ID: {event.event_id}"
                )

            seen_event_ids.add(event.event_id)

            prior = fingerprints.get(event.evidence_id)

            if prior is None:
                fingerprints[event.evidence_id] = (
                    event.evidence_fingerprint
                )
            elif prior != event.evidence_fingerprint:
                raise ValueError(
                    "fingerprint changed within ledger for "
                    f"{event.evidence_id}"
                )

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}

        for event in self.current().values():
            counts[event.disposition] = (
                counts.get(event.disposition, 0) + 1
            )

        return counts

    def assert_fingerprint(
        self,
        record: Any,
    ) -> None:
        """
        Verify that the current ledger entry for the record still refers to
        the same EvidenceRecord content.
        """
        evidence_id = str(record.experiment_id)
        current = self.get(evidence_id)

        if current is None:
            return

        actual = evidence_fingerprint(record)

        if actual != current.evidence_fingerprint:
            raise ValueError(
                f"EvidenceRecord fingerprint mismatch for {evidence_id}: "
                f"ledger={current.evidence_fingerprint}, "
                f"actual={actual}"
            )