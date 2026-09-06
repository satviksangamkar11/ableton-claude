"""
16.5.40c — Build the first external disposition ledger.

Input:
    experiments/16_5_40B_WITNESS_RECOVERY.json

Output:
    experiments/16_5_40C_DISPOSITION_LEDGER.jsonl

This script is append-only.

It does NOT:
- modify EvidenceRecords
- modify CapabilityContracts
- modify ClaimGroups
- promote evidence
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"D:\ableton claude")
EXPERIMENTS = ROOT / "experiments"

sys.path.insert(0, str(ROOT))

from serum2.evidence.disposition import (  # noqa: E402
    CONTEXT_INCOMPLETE,
    HISTORICAL_VALID,
    INVALIDATED_ACTUATOR,
    VALID,
    DispositionLedger,
)


RECOVERY_PATH = (
    EXPERIMENTS / "16_5_40B_WITNESS_RECOVERY.json"
)

LEDGER_PATH = (
    EXPERIMENTS / "16_5_40C_DISPOSITION_LEDGER.jsonl"
)


def main() -> int:
    print("=" * 80)
    print("16.5.40c — External Evidence Disposition Ledger")
    print("=" * 80)

    if not RECOVERY_PATH.exists():
        print(f"ERROR: missing {RECOVERY_PATH}")
        return 2

    recovery = json.loads(
        RECOVERY_PATH.read_text(
            encoding="utf-8"
        )
    )

    records = recovery.get("records", {})

    if not isinstance(records, dict):
        print("ERROR: recovery records must be an object")
        return 2

    ledger = DispositionLedger(LEDGER_PATH)

    # Integrity-check whatever already exists before appending anything.
    ledger.verify_integrity()

    existing = ledger.current()

    appended = 0
    skipped = 0

    for evidence_id, result in sorted(records.items()):
        disposition = str(result["status"])
        fingerprint = str(result["fingerprint"])

        if disposition not in {
            VALID,
            HISTORICAL_VALID,
            CONTEXT_INCOMPLETE,
            INVALIDATED_ACTUATOR,
        }:
            raise ValueError(
                f"unsupported recovery status for "
                f"{evidence_id}: {disposition}"
            )

        prior = existing.get(evidence_id)

        if prior is not None:
            if prior.evidence_fingerprint != fingerprint:
                raise ValueError(
                    "existing ledger fingerprint mismatch for "
                    f"{evidence_id}"
                )

            if prior.disposition != disposition:
                raise ValueError(
                    f"existing disposition conflict for {evidence_id}: "
                    f"{prior.disposition} != {disposition}. "
                    "No automatic disposition change is allowed."
                )

            skipped += 1
            continue

        reasons = tuple(
            str(x)
            for x in result.get("reasons", ())
        )

        source_refs = []

        for ref in result.get("artifact_refs", ()):
            artifact_path = ref.get("artifact_path")
            if artifact_path:
                source_refs.append(str(artifact_path))

            artifact_hash = ref.get("artifact_hash")
            if artifact_hash:
                source_refs.append(
                    f"sha256:{artifact_hash}"
                )

        event = ledger.append(
            evidence_id=evidence_id,
            evidence_fingerprint_value=fingerprint,
            disposition=disposition,
            reason=(
                "16.5.40b witness-recovery classification"
                if not reasons
                else "; ".join(reasons)
            ),
            source_refs=source_refs
            + ["16.5.40B_WITNESS_RECOVERY.json"],
        )

        print(
            f"APPEND {event.evidence_id}: "
            f"{event.disposition}"
        )

        appended += 1

    ledger.verify_integrity()

    print()
    print("=== SUMMARY ===")
    print(f"Appended: {appended}")
    print(f"Skipped:  {skipped}")
    print(f"Entries:  {len(ledger.current())}")

    print()
    print("=== STATUS COUNTS ===")

    for status, count in sorted(
        ledger.status_counts().items()
    ):
        print(f"{status:24s} {count}")

    print()
    print(f"Ledger: {LEDGER_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())