"""
16.5.40 — Evidence replayability and contract-completeness audit.

This module is intentionally READ-ONLY over EvidenceRecords and contracts.

It answers:

    "Can this supporting evidence record be reconstructed from persisted
     information alone strongly enough to replay the same experiment?"

It does NOT:
- modify EvidenceRecords
- modify ClaimGroups
- modify CapabilityContracts
- infer missing stimulus/context from prose
- promote or demote capabilities

Missing replay ingredients produce CONTEXT_INCOMPLETE rather than guesses.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


REPLAYABLE = "REPLAYABLE"
CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"
RECORD_MISSING = "RECORD_MISSING"


@dataclass(frozen=True)
class ReplayAssessment:
    evidence_id: str
    status: str
    reasons: Tuple[str, ...]
    persisted: Dict[str, bool]
    fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContractReplayAssessment:
    contract_key: str
    target: str
    status: str
    supporting_evidence: Tuple[str, ...]
    replayable_evidence: Tuple[str, ...]
    incomplete_evidence: Tuple[str, ...]
    missing_evidence: Tuple[str, ...]
    reasons: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, (set, frozenset)):
        return sorted(value)

    return repr(value)


def _stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def record_fingerprint(record: Any) -> str:
    """
    Stable fingerprint of the observable EvidenceRecord representation.
    """
    if hasattr(record, "to_dict"):
        payload = record.to_dict()
    else:
        payload = repr(record)

    return hashlib.sha256(_stable_json(payload)).hexdigest()


def _causal_measurements(record: Any) -> Sequence[Any]:
    return tuple(getattr(record, "causal_measurements", ()) or ())


def _experiment(record: Any) -> Mapping[str, Any]:
    return getattr(record, "experiment", {}) or {}


def assess_record(record: Any) -> ReplayAssessment:
    """
    Audit only persisted ingredients that are actually present in the
    EvidenceRecord schema.

    A measurement-condition HASH is not treated as a persisted stimulus.
    It fingerprints the condition; it does not reconstruct it.
    """
    evidence_id = str(getattr(record, "experiment_id", "<unknown>"))
    exp = _experiment(record)

    mutations = exp.get("mutations")
    prerequisites = exp.get("prerequisites")
    baseline_overrides = exp.get("baseline_overrides")
    measurement_condition_signatures = exp.get(
        "measurement_condition_signatures"
    )

    causal = _causal_measurements(record)

    persisted = {
        "experiment_id": bool(evidence_id and evidence_id != "<unknown>"),
        "mutations": bool(mutations),
        "prerequisites": prerequisites is not None,
        "baseline_overrides": baseline_overrides is not None,
        "mutation_signature": bool(exp.get("mutation_signature")),
        "experiment_condition_signature": bool(
            exp.get("experiment_condition_signature")
        ),
        "measurement_condition_signatures": bool(
            measurement_condition_signatures
        ),
        "measurement_definition_ids": bool(
            causal
            and all(
                getattr(m, "measurement_definition_id", None)
                for m in causal
            )
        ),
        "measurement_stimulus": False,
        "runtime_epoch": bool(getattr(record, "epoch", None)),
        "state_hashes": bool(
            getattr(getattr(record, "state_observation", {}), "get", lambda *_: None)(
                "control_hash"
            )
            and getattr(getattr(record, "state_observation", {}), "get", lambda *_: None)(
                "treatment_hash"
            )
        ),
    }

    reasons = []

    if not persisted["mutations"]:
        reasons.append("mutations not persisted")

    if not persisted["prerequisites"]:
        reasons.append("prerequisites not persisted")

    if not persisted["baseline_overrides"]:
        reasons.append(
            "baseline_overrides not persisted in EvidenceRecord.experiment"
        )

    if not persisted["measurement_condition_signatures"]:
        reasons.append(
            "measurement condition signatures not persisted"
        )

    if causal and not persisted["measurement_definition_ids"]:
        reasons.append(
            "one or more causal measurements lacks measurement_definition_id"
        )

    # A condition hash is not enough to reproduce the stimulus.
    if causal or measurement_condition_signatures:
        reasons.append(
            "measurement stimulus values are not persisted; "
            "condition hash is only an identity fingerprint"
        )

    if not persisted["runtime_epoch"]:
        reasons.append("execution epoch is missing")

    if not persisted["state_hashes"]:
        reasons.append("control/treatment state hashes are incomplete")

    status = REPLAYABLE if not reasons else CONTEXT_INCOMPLETE

    return ReplayAssessment(
        evidence_id=evidence_id,
        status=status,
        reasons=tuple(reasons),
        persisted=persisted,
        fingerprint=record_fingerprint(record),
    )


def audit_contract(
    contract_key: str,
    contract: Any,
    records: Mapping[str, Any],
) -> ContractReplayAssessment:
    provenance = getattr(contract, "provenance", {}) or {}
    supporting = tuple(
        str(x) for x in provenance.get("supporting_evidence", ())
    )

    replayable = []
    incomplete = []
    missing = []
    reasons = []

    for evidence_id in supporting:
        record = records.get(evidence_id)

        if record is None:
            missing.append(evidence_id)
            continue

        assessment = assess_record(record)

        if assessment.status == REPLAYABLE:
            replayable.append(evidence_id)
        else:
            incomplete.append(evidence_id)
            reasons.extend(
                f"{evidence_id}: {reason}"
                for reason in assessment.reasons
            )

    if missing:
        reasons.extend(
            f"{evidence_id}: EvidenceRecord not available in discovered store"
            for evidence_id in missing
        )

    if missing:
        status = RECORD_MISSING
    elif incomplete:
        status = CONTEXT_INCOMPLETE
    elif supporting:
        status = REPLAYABLE
    else:
        status = RECORD_MISSING

    return ContractReplayAssessment(
        contract_key=str(contract_key),
        target=str(getattr(contract, "target", "<unknown>")),
        status=status,
        supporting_evidence=supporting,
        replayable_evidence=tuple(replayable),
        incomplete_evidence=tuple(incomplete),
        missing_evidence=tuple(missing),
        reasons=tuple(sorted(set(reasons))),
    )


def discover_evidence_records(
    paths: Iterable[Path],
) -> Tuple[Dict[str, Any], Tuple[str, ...]]:
    """
    Discover pickled EvidenceRecords from explicitly supplied files.

    We intentionally do not treat arbitrary pickle contents as evidence.
    Only objects exposing EvidenceRecord-like fields are accepted.
    """
    import pickle

    records: Dict[str, Any] = {}
    sources = []

    for path in paths:
        if path.suffix.lower() != ".pkl":
            continue

        try:
            with path.open("rb") as f:
                obj = pickle.load(f)
        except Exception:
            continue

        candidates = []

        if isinstance(obj, dict):
            candidates.extend(obj.values())
        elif isinstance(obj, (list, tuple, set)):
            candidates.extend(obj)
        else:
            candidates.append(obj)

        for candidate in candidates:
            evidence_id = getattr(candidate, "experiment_id", None)
            causal = getattr(candidate, "causal_measurements", None)

            # Conservative EvidenceRecord shape check.
            if evidence_id and causal is not None and hasattr(candidate, "experiment"):
                evidence_id = str(evidence_id)

                # Preserve first occurrence; duplicate IDs from separate
                # artifacts are a data-quality problem, not silently merged.
                if evidence_id in records and records[evidence_id] is not candidate:
                    raise ValueError(
                        f"duplicate EvidenceRecord ID discovered: {evidence_id}"
                    )

                records[evidence_id] = candidate
                sources.append(str(path))

    return records, tuple(sorted(set(sources)))


def audit_contracts(
    contracts: Mapping[Any, Any],
    records: Mapping[str, Any],
) -> Dict[str, Any]:
    contract_results = {}

    for key, contract in contracts.items():
        key_str = str(key)
        contract_results[key_str] = audit_contract(
            key_str,
            contract,
            records,
        )

    counts: Dict[str, int] = {}
    for result in contract_results.values():
        counts[result.status] = counts.get(result.status, 0) + 1

    return {
        "schema_version": "16.5.40.1",
        "contract_count": len(contract_results),
        "status_counts": counts,
        "contracts": {
            key: result.to_dict()
            for key, result in sorted(contract_results.items())
        },
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=_json_default,
        ),
        encoding="utf-8",
    )

def discover_fixture_records() -> Dict[str, Any]:
    """
    Discover the canonical real-host fixture EvidenceRecords used by the
    historical promotion pipeline.

    These are legitimate EvidenceRecords but are not persisted as *.pkl
    artifacts, so filesystem-only discovery must not classify them as missing.
    """
    from serum2.evidence import fixtures

    records = {}

    for record in fixtures.all_real():
        evidence_id = getattr(record, "experiment_id", None)

        if not evidence_id:
            raise ValueError(
                "fixture EvidenceRecord has no experiment_id"
            )

        evidence_id = str(evidence_id)

        if evidence_id in records:
            raise ValueError(
                f"duplicate fixture EvidenceRecord ID: {evidence_id}"
            )

        records[evidence_id] = record

    return records