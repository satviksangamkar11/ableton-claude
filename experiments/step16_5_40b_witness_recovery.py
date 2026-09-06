"""
16.5.40b — Historical witness recovery runner.

Read-only over evidence and capability artifacts.

Output:
    experiments/16_5_40B_WITNESS_RECOVERY.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"D:\ableton claude")
EXPERIMENTS = ROOT / "experiments"

sys.path.insert(0, str(ROOT))

from serum2.evidence.witness_recovery import (  # noqa: E402
    add_fixture_records,
    load_contamination_manifest,
    load_evidence_records,
    recover_all,
)


OUTPUT = EXPERIMENTS / "16_5_40B_WITNESS_RECOVERY.json"

# This manifest is deliberately NOT populated automatically.
# Invalidated evidence must be explicitly established from known artifacts.
MANIFEST = EXPERIMENTS / "16_5_40B_CONTAMINATION_MANIFEST.json"


def main() -> int:
    print("=" * 80)
    print("16.5.40b — Historical Witness Recovery")
    print("=" * 80)

    pkl_paths = sorted(EXPERIMENTS.glob("*.pkl"))

    records = load_evidence_records(pkl_paths)
    add_fixture_records(records)

    print(f"EvidenceRecords discovered: {len(records)}")

    contamination = load_contamination_manifest(MANIFEST)

    print(
        f"Explicit contamination entries: {len(contamination)}"
    )

    result = recover_all(
        records,
        EXPERIMENTS,
        contamination,
    )

    OUTPUT.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print()
    print("=== SUMMARY ===")

    for status, count in sorted(
        result["status_counts"].items()
    ):
        print(f"{status:24s} {count}")

    print()
    print(f"Output: {OUTPUT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())