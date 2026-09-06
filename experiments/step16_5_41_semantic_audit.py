"""
16.5.41 — Claim/current-capability semantic audit.

Reads:
    _capability_contracts.pkl
    16_5_40C_DISPOSITION_LEDGER.jsonl

Writes:
    16_5_41_SEMANTIC_AUDIT.json

No mutation of contracts or evidence.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

ROOT = Path(r"D:\ableton claude")
EXPERIMENTS = ROOT / "experiments"

sys.path.insert(0, str(ROOT))

from serum2.evidence.disposition import (  # noqa: E402
    DispositionLedger,
)
from serum2.evidence.semantics import (  # noqa: E402
    evaluate_all_contracts,
    semantic_summary,
)


CONTRACT_PATH = EXPERIMENTS / "_capability_contracts.pkl"
LEDGER_PATH = EXPERIMENTS / "16_5_40C_DISPOSITION_LEDGER.jsonl"
OUTPUT_PATH = EXPERIMENTS / "16_5_41_SEMANTIC_AUDIT.json"


def main() -> int:
    print("=" * 80)
    print("16.5.41 — Claim / Current-Capability Semantic Audit")
    print("=" * 80)

    with CONTRACT_PATH.open("rb") as f:
        contracts = pickle.load(f)

    ledger = DispositionLedger(LEDGER_PATH)
    ledger.verify_integrity()

    current = ledger.current()

    dispositions = {
        evidence_id: event.disposition
        for evidence_id, event in current.items()
    }

    views = evaluate_all_contracts(
        contracts,
        dispositions,
    )

    summary = semantic_summary(views)

    payload = {
        "schema_version": "16.5.41.1",
        "summary": summary,
        "contracts": {
            key: view.to_dict()
            for key, view in sorted(views.items())
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print()
    print("=== SUMMARY ===")
    print(
        "Contracts:",
        summary["contract_count"],
    )
    print(
        "Historical admissible:",
        summary["counts"]["historical_admissible"],
    )
    print(
        "Current-runtime candidates:",
        summary["counts"]["current_runtime_candidates"],
    )
    print(
        "Current-runtime requalification required:",
        summary["counts"][
            "current_runtime_requalification_required"
        ],
    )
    print(
        "Current-runtime VERIFIED:",
        summary["current_runtime_verified_contracts"],
    )

    print()
    print(f"Output: {OUTPUT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())