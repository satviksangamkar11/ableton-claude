"""
16.5.40 — Contract completeness / replay audit.

Read-only.
Does NOT modify contracts, ClaimGroups, or EvidenceRecords.

Inputs:
  experiments/_capability_contracts.pkl
  all discoverable *.pkl evidence artifacts

Outputs:
  experiments/16_5_40_REPLAY_AUDIT.json
  experiments/16_5_40_REPLAYABLE_CONTRACTS.json
  experiments/16_5_40_CONTEXT_INCOMPLETE_CONTRACTS.json
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

ROOT = Path(r"D:\ableton claude")
EXPERIMENTS = ROOT / "experiments"

sys.path.insert(0, str(ROOT))

from serum2.evidence.replay import (  # noqa: E402
    REPLAYABLE,
    CONTEXT_INCOMPLETE,
    RECORD_MISSING,
    audit_contracts,
    discover_evidence_records,
    discover_fixture_records,
    write_json,
)


CONTRACT_PATH = EXPERIMENTS / "_capability_contracts.pkl"
AUDIT_PATH = EXPERIMENTS / "16_5_40_REPLAY_AUDIT.json"
REPLAYABLE_PATH = EXPERIMENTS / "16_5_40_REPLAYABLE_CONTRACTS.json"
INCOMPLETE_PATH = EXPERIMENTS / "16_5_40_CONTEXT_INCOMPLETE_CONTRACTS.json"


def main() -> int:
    print("=" * 80)
    print("16.5.40 — Contract Completeness / Replay Audit")
    print("=" * 80)

    if not CONTRACT_PATH.exists():
        print(f"ERROR: missing {CONTRACT_PATH}")
        return 2

    with CONTRACT_PATH.open("rb") as f:
        contracts = pickle.load(f)

    print(f"Loaded contracts: {len(contracts)}")

    pkl_paths = sorted(EXPERIMENTS.glob("*.pkl"))

    records, evidence_sources = discover_evidence_records(pkl_paths)

    fixture_records = discover_fixture_records()

    for evidence_id, record in fixture_records.items():
        if evidence_id in records:
            existing = records[evidence_id]

            if type(existing) is not type(record):
                raise ValueError(
                    f"fixture/filesystem type collision for {evidence_id}"
                )

            continue

        records[evidence_id] = record

    evidence_sources = tuple(sorted(set(
        evidence_sources + ("fixtures.all_real()",)
    )))

    print(f"Discovered EvidenceRecords: {len(records)}")
    print(f"Evidence source files: {len(evidence_sources)}")

    duplicate_guard = {}

    for evidence_id, record in sorted(records.items()):
        duplicate_guard[evidence_id] = {
            "experiment_id": evidence_id,
            "source_object_type": type(record).__name__,
        }

    audit = audit_contracts(contracts, records)

    replayable = {}
    incomplete = {}
    missing = {}

    for key, result in audit["contracts"].items():
        if result["status"] == REPLAYABLE:
            replayable[key] = result
        elif result["status"] == CONTEXT_INCOMPLETE:
            incomplete[key] = result
        else:
            missing[key] = result

    payload = {
        **audit,
        "evidence_record_count": len(records),
        "evidence_source_files": list(evidence_sources),
        "evidence_records": duplicate_guard,
        "notes": [
            "READ_ONLY audit; no EvidenceRecord, ClaimGroup, or CapabilityContract was modified.",
            "A measurement-condition hash is not treated as the original stimulus.",
            "Missing baseline_overrides/stimulus are reported as context-incomplete.",
            "No capability status is changed by this audit.",
        ],
    }

    write_json(AUDIT_PATH, payload)

    write_json(
        REPLAYABLE_PATH,
        {
            "schema_version": "16.5.40.1",
            "contract_count": len(replayable),
            "contracts": replayable,
        },
    )

    write_json(
        INCOMPLETE_PATH,
        {
            "schema_version": "16.5.40.1",
            "contract_count": len(incomplete) + len(missing),
            "context_incomplete": incomplete,
            "record_missing": missing,
        },
    )

    print()
    print("=== SUMMARY ===")
    for status, count in sorted(audit["status_counts"].items()):
        print(f"{status:22s} {count}")

    print()
    print(f"Audit:       {AUDIT_PATH}")
    print(f"Replayable:  {REPLAYABLE_PATH}")
    print(f"Incomplete:  {INCOMPLETE_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())