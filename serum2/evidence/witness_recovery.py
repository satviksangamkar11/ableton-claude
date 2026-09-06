"""
16.5.40b — Historical witness recovery.

Purpose
-------
Recover the historical experiment recipe behind EvidenceRecords using only
artifacts that actually exist in the repository / experiments directory.

This module is intentionally conservative.

It does NOT:
- mutate EvidenceRecords
- mutate ClaimGroups
- mutate CapabilityContracts
- promote evidence
- infer missing values from hashes
- infer actuator contamination from experiment numbering alone

Classification
--------------
VALID
    Historical recipe is sufficiently reconstructible from persisted
    artifacts and is internally coherent.

HISTORICAL_VALID
    Historical evidence is identifiable and supported by an archived witness,
    but the current persisted record is not sufficient for exact replay.

CONTEXT_INCOMPLETE
    Required historical witness information could not be recovered from the
    discovered artifacts.

INVALIDATED_ACTUATOR
    Explicitly marked invalid by an external contamination manifest.
"""

from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple


VALID = "VALID"
HISTORICAL_VALID = "HISTORICAL_VALID"
CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"
INVALIDATED_ACTUATOR = "INVALIDATED_ACTUATOR"


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

    if isinstance(value, Path):
        return str(value)

    return repr(value)


def stable_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(stable_json(value)).hexdigest()


def record_to_dict(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict"):
        data = record.to_dict()
        if isinstance(data, dict):
            return data

    if hasattr(record, "__dict__"):
        return dict(record.__dict__)

    raise TypeError(
        f"unsupported EvidenceRecord representation: {type(record)!r}"
    )


def evidence_fingerprint(record: Any) -> str:
    return sha256_json(record_to_dict(record))


@dataclass(frozen=True)
class WitnessReference:
    evidence_id: str
    experiment_id: str
    artifact_path: Optional[str]
    artifact_kind: str
    artifact_hash: Optional[str]
    found: bool
    notes: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WitnessRecovery:
    evidence_id: str
    fingerprint: str
    status: str
    artifact_refs: Tuple[WitnessReference, ...]
    recovered_fields: Tuple[str, ...]
    missing_fields: Tuple[str, ...]
    reasons: Tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContaminationManifestEntry:
    evidence_id: str
    reason: str
    source_ref: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_evidence_records(paths: Iterable[Path]) -> dict[str, Any]:
    """
    Load EvidenceRecord-like objects from explicit pickle artifacts.

    Duplicate experiment IDs are a hard failure. Silent merging is forbidden.
    """
    records: dict[str, Any] = {}

    for path in paths:
        if path.suffix.lower() != ".pkl":
            continue

        try:
            with path.open("rb") as f:
                obj = pickle.load(f)
        except Exception:
            continue

        candidates: list[Any]

        if isinstance(obj, dict):
            candidates = list(obj.values())
        elif isinstance(obj, (list, tuple, set, frozenset)):
            candidates = list(obj)
        else:
            candidates = [obj]

        for candidate in candidates:
            evidence_id = getattr(candidate, "experiment_id", None)

            if not evidence_id:
                continue

            if not hasattr(candidate, "experiment"):
                continue

            evidence_id = str(evidence_id)

            if evidence_id in records:
                raise ValueError(
                    f"duplicate EvidenceRecord ID discovered: {evidence_id}"
                )

            records[evidence_id] = candidate

    return records


def add_fixture_records(records: dict[str, Any]) -> None:
    """
    Add the canonical real-host fixture records E0/E1/E2a/E2b/E3.

    These are legitimate historical evidence sources but do not necessarily
    exist as standalone pickle files.
    """
    from serum2.evidence import fixtures

    for record in fixtures.all_real():
        evidence_id = str(record.experiment_id)

        if evidence_id in records:
            raise ValueError(
                f"duplicate EvidenceRecord ID across files and fixtures: "
                f"{evidence_id}"
            )

        records[evidence_id] = record


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def discover_artifacts(
    experiments_dir: Path,
    evidence_id: str,
) -> Tuple[WitnessReference, ...]:
    """
    Find repository artifacts explicitly mentioning an evidence ID.

    This is discovery only. Content is never inferred.
    """
    refs: list[WitnessReference] = []

    candidates = sorted(
        p
        for p in experiments_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {
            ".py",
            ".json",
            ".md",
            ".txt",
            ".pkl",
        }
    )

    for path in candidates:
        if path.name.startswith("16_5_40"):
            # Do not let this audit's own generated files become historical
            # witnesses for the evidence being audited.
            continue

        try:
            if path.suffix.lower() == ".pkl":
                # Binary pickles are handled separately as evidence stores.
                continue

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        if evidence_id not in text:
            continue

        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        refs.append(
            WitnessReference(
                evidence_id=evidence_id,
                experiment_id=evidence_id,
                artifact_path=str(path),
                artifact_kind=path.suffix.lower().lstrip("."),
                artifact_hash=digest,
                found=True,
                notes=("evidence ID text match",),
            )
        )

    return tuple(refs)


def recover_from_record_and_artifacts(
    record: Any,
    artifact_refs: Sequence[WitnessReference],
    *,
    contamination: Optional[ContaminationManifestEntry] = None,
) -> WitnessRecovery:
    evidence_id = str(record.experiment_id)
    fingerprint = evidence_fingerprint(record)

    if contamination is not None:
        return WitnessRecovery(
            evidence_id=evidence_id,
            fingerprint=fingerprint,
            status=INVALIDATED_ACTUATOR,
            artifact_refs=tuple(artifact_refs),
            recovered_fields=(),
            missing_fields=(),
            reasons=(
                contamination.reason,
                f"source_ref={contamination.source_ref}",
            ),
        )

    exp = getattr(record, "experiment", {}) or {}

    recovered_fields: list[str] = []
    missing_fields: list[str] = []
    reasons: list[str] = []

    # These are the minimum design-level pieces we expect to identify.
    required_record_fields = (
        "mutations",
        "prerequisites",
        "mutation_signature",
        "experiment_condition_signature",
    )

    for field in required_record_fields:
        if field in exp and exp[field] is not None:
            recovered_fields.append(field)
        else:
            missing_fields.append(field)

    # Historical artifact presence is evidence of a witness source, but
    # merely finding a filename/text match does not magically reconstruct
    # missing experiment values.
    if artifact_refs:
        recovered_fields.append("historical_artifact_reference")
    else:
        missing_fields.append("historical_artifact_reference")

    # Baseline overrides are not present in the current EvidenceRecord schema.
    # We only credit them if an explicit historical artifact contains them.
    baseline_recovered = False
    stimulus_recovered = False
    measurement_condition_recovered = False

    for ref in artifact_refs:
        if not ref.artifact_path:
            continue

        path = Path(ref.artifact_path)

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except Exception:
            continue

        if "baseline_overrides" in text:
            baseline_recovered = True

        if "stimulus" in text or "stimulus_notes" in text:
            stimulus_recovered = True

        if "measurement_condition" in text:
            measurement_condition_recovered = True

    if baseline_recovered:
        recovered_fields.append("baseline_overrides")
    else:
        missing_fields.append("baseline_overrides")

    causal = tuple(
        getattr(record, "causal_measurements", ()) or ()
    )

    if causal:
        if measurement_condition_recovered:
            recovered_fields.append("measurement_condition")
        else:
            missing_fields.append("measurement_condition")

        if stimulus_recovered:
            recovered_fields.append("measurement_stimulus")
        else:
            missing_fields.append("measurement_stimulus")

    # We deliberately distinguish:
    #
    #   evidence exists + historical witness exists
    #        => HISTORICAL_VALID
    #
    # from:
    #
    #   no usable historical witness
    #        => CONTEXT_INCOMPLETE
    #
    # Exact current replay requires all mandatory ingredients.
    exact_replay_fields = {
        "mutations",
        "prerequisites",
        "mutation_signature",
        "experiment_condition_signature",
        "baseline_overrides",
    }

    has_exact_design = exact_replay_fields <= set(recovered_fields)

    if causal:
        has_exact_design = has_exact_design and {
            "measurement_condition",
            "measurement_stimulus",
        } <= set(recovered_fields)

    if has_exact_design:
        status = VALID
    elif artifact_refs:
        status = HISTORICAL_VALID
        reasons.append(
            "historical witness identified, but exact replay recipe is incomplete"
        )
    else:
        status = CONTEXT_INCOMPLETE
        reasons.append(
            "no historical witness artifact recovered"
        )

    if missing_fields:
        reasons.extend(
            f"missing:{field}"
            for field in sorted(set(missing_fields))
        )

    return WitnessRecovery(
        evidence_id=evidence_id,
        fingerprint=fingerprint,
        status=status,
        artifact_refs=tuple(artifact_refs),
        recovered_fields=tuple(sorted(set(recovered_fields))),
        missing_fields=tuple(sorted(set(missing_fields))),
        reasons=tuple(sorted(set(reasons))),
    )


def load_contamination_manifest(
    path: Path,
) -> dict[str, ContaminationManifestEntry]:
    """
    Explicit external invalidation manifest.

    Empty / absent manifest is valid.
    """
    if not path.exists():
        return {}

    payload = _load_json(path)

    if not isinstance(payload, dict):
        raise ValueError(
            f"contamination manifest must be a JSON object: {path}"
        )

    raw_entries = payload.get("entries", [])

    if not isinstance(raw_entries, list):
        raise ValueError(
            "contamination manifest 'entries' must be a list"
        )

    result: dict[str, ContaminationManifestEntry] = {}

    for item in raw_entries:
        if not isinstance(item, dict):
            raise ValueError(
                "contamination manifest entry must be an object"
            )

        evidence_id = str(item["evidence_id"])
        reason = str(item["reason"])
        source_ref = str(item["source_ref"])

        if evidence_id in result:
            raise ValueError(
                f"duplicate contamination manifest entry: {evidence_id}"
            )

        result[evidence_id] = ContaminationManifestEntry(
            evidence_id=evidence_id,
            reason=reason,
            source_ref=source_ref,
        )

    return result


def recover_all(
    records: Mapping[str, Any],
    experiments_dir: Path,
    contamination_manifest: Mapping[
        str, ContaminationManifestEntry
    ],
) -> dict[str, Any]:
    results: dict[str, Any] = {}

    for evidence_id, record in sorted(records.items()):
        refs = discover_artifacts(
            experiments_dir,
            evidence_id,
        )

        result = recover_from_record_and_artifacts(
            record,
            refs,
            contamination=contamination_manifest.get(evidence_id),
        )

        results[evidence_id] = result.to_dict()

    counts: dict[str, int] = {}

    for result in results.values():
        status = result["status"]
        counts[status] = counts.get(status, 0) + 1

    return {
        "schema_version": "16.5.40b.1",
        "record_count": len(results),
        "status_counts": counts,
        "records": results,
    }