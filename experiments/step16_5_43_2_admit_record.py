from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.record import (
    EvidenceArm,
    EvidenceRecord,
    CausalMeasurement,
    MeasurementTarget,
)
from serum2.evidence.disposition import (
    evidence_fingerprint,
    DispositionLedger,
    VALID,
)
from serum2.evidence.disposition_gate import EvidenceDispositionGate


ROOT = Path(r"D:\ableton claude")

ARTIFACT = (
    ROOT
    / "experiments"
    / "16_5_43_2_CORPUS_DURATION_QUALIFICATION.json"
)

LEDGER = (
    ROOT
    / "experiments"
    / "16_5_40C_DISPOSITION_LEDGER.jsonl"
)

OUT_RECORD = (
    ROOT
    / "experiments"
    / "_env_sustain_corpus_16_5_43_2_record.pkl"
)


def reconstruct_record(record_dict: dict) -> EvidenceRecord:
    causal = tuple(
        CausalMeasurement(
            metric=m["metric"],
            target=MeasurementTarget(
                field_path=m["target"]["field_path"],
                module=m["target"].get("module"),
                parameter=m["target"].get("parameter"),
            ),
            baseline=m.get("baseline"),
            treatment=m.get("treatment"),
            delta=m.get("delta"),
            expected_direction=m["expected_direction"],
            observed_direction=m.get("observed_direction"),
            threshold=m.get("threshold"),
            status=m["status"],
            measurement_condition_signature=
                m.get("measurement_condition_signature"),
            measurement_definition_id=
                m.get("measurement_definition_id"),
        )
        for m in record_dict.get("causal_measurements", [])
    )

    arms = tuple(
        EvidenceArm(
            arm_id=a["arm_id"],
            role=a["role"],
            declared_context=a["declared_context"],
            observed_context=a.get("observed_context"),
            state_observation=a.get("state_observation"),
            load_status=a["load_status"],
            render_status=a["render_status"],
            artifacts=a.get("artifacts", {}),
        )
        for a in record_dict.get("arms", [])
    )

    return EvidenceRecord(
        experiment_id=record_dict["experiment_id"],
        epoch=record_dict["epoch"],
        experiment=record_dict["experiment"],
        arms=arms,
        runtime_verifications=tuple(
            record_dict.get("runtime_verifications", [])
        ),
        state_observation=record_dict["state_observation"],
        load_observation=record_dict["load_observation"],
        render_observation=record_dict["render_observation"],
        causal_measurements=causal,
        persistence_observation=
            record_dict["persistence_observation"],
        integrity=record_dict.get(
            "integrity",
            {
                "synthetic": False,
                "contradictions": [],
                "relationships": [],
                "reverify_required": False,
            },
        ),
        structural_observation=
            record_dict.get("structural_observation", {}),
    )


def main():
    print("=" * 80)
    print("16.5.43.2 — RECONSTRUCT + DISPOSITION NEW EVIDENCE")
    print("=" * 80)

    artifact = json.loads(
        ARTIFACT.read_text(encoding="utf-8")
    )

    # The qualifying current corpus Sustain record is the one produced by
    # the corrected fallback experiment.
    nested = (
        artifact["corrected_sustain_fallback"]
        ["record"]["evidence_record"]
    )

    record = reconstruct_record(nested)

    fp = evidence_fingerprint(record)

    print()
    print("Evidence ID:")
    print(record.experiment_id)

    print()
    print("Fingerprint:")
    print(fp)

    print()
    print("Gates:")
    print(record.gate_completeness())

    print()
    print("Runtime verified:")
    print(record.runtime_verified())

    print()
    print("Outcome:")
    print(record.outcome_signature())

    print()
    print("Measurement definition IDs:")
    for m in record.causal_measurements:
        print(" ", m.measurement_definition_id)

    # Verify immutability representation before any admission.
    if record.is_synthetic:
        raise RuntimeError(
            "Refusing synthetic EvidenceRecord"
        )

    # Disposition ledger must already be internally valid.
    ledger = DispositionLedger(LEDGER)
    ledger.verify_integrity()

    existing = ledger.get(record.experiment_id)

    if existing is None:
        print()
        print("No existing disposition entry.")
        print("Creating VALID disposition for this new current record.")

        event = ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=fp,
            disposition=VALID,
            reason=(
                "Current 16.5.43.2 normalized-corpus Sustain "
                "qualification: generation/load/render/causal/"
                "persistence PASS; runtime verified; EFFECT_OBSERVED; "
                "increase direction; corpus context explicitly "
                "tested and reproducible."
            ),
            source_refs=(
                "experiments/16_5_43_2_CORPUS_DURATION_QUALIFICATION.json",
            ),
        )

        print("Disposition event:")
        print(event.to_dict())

    else:
        print()
        print("Existing disposition:")
        print(existing.to_dict())

    gate = EvidenceDispositionGate(ledger)

    decision = gate.require_admissible(record)

    print()
    print("Disposition gate:")
    print(decision.to_dict())

    with OUT_RECORD.open("wb") as f:
        pickle.dump(record, f)

    print()
    print("Pickle written:")
    print(OUT_RECORD)

    print()
    print("16.5.43.2 RECORD RECONSTRUCTION COMPLETE")


if __name__ == "__main__":
    main()