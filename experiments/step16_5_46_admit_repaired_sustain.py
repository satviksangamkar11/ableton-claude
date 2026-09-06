"""16.5.46 — ADMIT REPAIRED SUSTAIN

Purpose
-------
Admit the NEW provenance-repaired 16.5.45 Corpus Sustain EvidenceRecord.

This script:
1. Loads the repaired EvidenceRecord from the pickle written by
   step16_5_45_corpus_sustain_context_revalidation.py
2. Verifies all gate completeness and runtime conditions
3. Asserts exact context values and mutations
4. Checks or creates disposition entry
5. Runs admission gate
6. Writes admission artifacts
7. Pickles the admitted record

The repaired record improves upon 16.5.43.2 by properly recording
baseline_overrides provenance within the EvidenceRecord itself.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.record import EvidenceRecord, EFFECT_OBSERVED, PASS
from serum2.evidence.disposition import (
    evidence_fingerprint,
    DispositionLedger,
    VALID,
)
from serum2.evidence.disposition_gate import EvidenceDispositionGate

ROOT = Path(r"D:\ableton claude")

RECORD_PICKLE = (
    ROOT / "experiments" / "_env_sustain_corpus_16_5_45_repaired_record.pkl"
)

LEDGER = ROOT / "experiments" / "16_5_40C_DISPOSITION_LEDGER.jsonl"

OUT_ARTIFACT = (
    ROOT / "experiments" / "16_5_46_REPAIRED_SUSTAIN_ADMISSION.json"
)

OUT_RECORD_PICKLE = (
    ROOT / "experiments" / "_env_sustain_corpus_16_5_45_repaired_record.pkl"
)


def main():
    print("=" * 80)
    print("16.5.46 — ADMIT REPAIRED SUSTAIN")
    print("=" * 80)

    # ----------------------------------------------------------------
    # 1. LOAD REPAIRED RECORD
    # ----------------------------------------------------------------

    print()
    print("Step 1: Load repaired EvidenceRecord from pickle...")

    if not RECORD_PICKLE.exists():
        raise RuntimeError(
            f"Record pickle not found: {RECORD_PICKLE}. "
            "Run step16_5_45_corpus_sustain_context_revalidation.py first."
        )

    with RECORD_PICKLE.open("rb") as f:
        record = pickle.load(f)

    print(f"  Record loaded: {record.experiment_id}")

    # ----------------------------------------------------------------
    # 2. ASSERT BASELINE_OVERRIDES EXISTS
    # ----------------------------------------------------------------

    print()
    print("Step 2: Assert baseline_overrides exists...")

    baseline_overrides = record.experiment.get("baseline_overrides", [])

    if not baseline_overrides:
        raise RuntimeError("baseline_overrides missing from record.experiment!")

    print(f"  baseline_overrides count: {len(baseline_overrides)}")

    # ----------------------------------------------------------------
    # 3. ASSERT EXACT CONTEXT
    # ----------------------------------------------------------------

    print()
    print("Step 3: Assert exact context...")

    override = baseline_overrides[0]
    expected_path = "Env0.plainParams.kParamDecay"
    expected_value = 0.02

    assert override.get("target_path") == expected_path, (
        f"Baseline override target_path mismatch: "
        f"{override.get('target_path')} != {expected_path}"
    )

    assert override.get("value") == expected_value, (
        f"Baseline override value mismatch: "
        f"{override.get('value')} != {expected_value}"
    )

    print(f"  [OK] target_path == {expected_path!r}")
    print(f"  [OK] value == {expected_value}")

    # ----------------------------------------------------------------
    # 4. ASSERT MUTATION
    # ----------------------------------------------------------------

    print()
    print("Step 4: Assert mutation...")

    mutations = record.experiment.get("mutations", [])

    if not mutations:
        raise RuntimeError("mutations missing from record.experiment!")

    mutation = mutations[0]
    expected_mutation_path = "Env0.plainParams.kParamSustain"
    expected_mutation_value = 0.3

    assert mutation.get("target_path") == expected_mutation_path, (
        f"Mutation target_path mismatch: "
        f"{mutation.get('target_path')} != {expected_mutation_path}"
    )

    assert mutation.get("value") == expected_mutation_value, (
        f"Mutation value mismatch: "
        f"{mutation.get('value')} != {expected_mutation_value}"
    )

    print(f"  [OK] Env0.plainParams.kParamSustain")
    print(f"  [OK] value == {expected_mutation_value}")

    # ----------------------------------------------------------------
    # 5. ASSERT GATE COMPLETENESS
    # ----------------------------------------------------------------

    print()
    print("Step 5: Assert gate completeness...")

    gates = record.gate_completeness()

    required_gates = {
        "generation": PASS,
        "load": PASS,
        "render": PASS,
        "causal": PASS,
        "persistence": PASS,
    }

    for gate_name, expected_status in required_gates.items():
        actual_status = gates.get(gate_name)
        assert actual_status == expected_status, (
            f"Gate {gate_name} status mismatch: "
            f"{actual_status} != {expected_status}"
        )
        print(f"  [OK] {gate_name} = {expected_status}")

    # ----------------------------------------------------------------
    # 6. ASSERT RUNTIME VERIFIED
    # ----------------------------------------------------------------

    print()
    print("Step 6: Assert runtime_verified() == True...")

    runtime_verified = record.runtime_verified()

    assert runtime_verified is True, (
        f"runtime_verified mismatch: {runtime_verified} != True"
    )

    print(f"  [OK] runtime_verified = True")

    # ----------------------------------------------------------------
    # 7. ASSERT CAUSAL STATUS
    # ----------------------------------------------------------------

    print()
    print("Step 7: Assert causal status == EFFECT_OBSERVED...")

    if not record.causal_measurements:
        raise RuntimeError("No causal measurements found!")

    causal_measurement = record.causal_measurements[0]

    assert causal_measurement.status == EFFECT_OBSERVED, (
        f"Causal status mismatch: "
        f"{causal_measurement.status} != {EFFECT_OBSERVED}"
    )

    print(f"  [OK] causal status = {EFFECT_OBSERVED}")

    # ----------------------------------------------------------------
    # 8. ASSERT MEASUREMENT DEFINITION ID
    # ----------------------------------------------------------------

    print()
    print("Step 8: Assert measurement_definition_id...")

    expected_measurement_id = "sustain_window_rms_db:c092f5a1078d"

    actual_measurement_id = causal_measurement.measurement_definition_id

    assert actual_measurement_id == expected_measurement_id, (
        f"Measurement definition ID mismatch: "
        f"{actual_measurement_id} != {expected_measurement_id}"
    )

    print(f"  [OK] measurement_definition_id = {expected_measurement_id}")

    # ----------------------------------------------------------------
    # 9. COMPUTE EVIDENCE FINGERPRINT
    # ----------------------------------------------------------------

    print()
    print("Step 9: Compute evidence fingerprint...")

    fp = evidence_fingerprint(record)

    print(f"  Evidence fingerprint: {fp}")

    # ----------------------------------------------------------------
    # 10. VERIFY DISPOSITION LEDGER INTEGRITY
    # ----------------------------------------------------------------

    print()
    print("Step 10: Verify disposition ledger integrity...")

    ledger = DispositionLedger(LEDGER)
    ledger.verify_integrity()

    print(f"  [OK] Ledger integrity verified")

    # ----------------------------------------------------------------
    # 11. CHECK EXISTING DISPOSITION
    # ----------------------------------------------------------------

    print()
    print("Step 11: Check whether this evidence_id has disposition...")

    existing = ledger.get(record.experiment_id)

    if existing is not None:
        print(f"  Existing disposition found:")
        print(f"    {existing.to_dict()}")
    else:
        print(f"  No existing disposition")

    # ----------------------------------------------------------------
    # 12. CREATE OR VERIFY DISPOSITION
    # ----------------------------------------------------------------

    print()
    print("Step 12: Create or verify disposition...")

    if existing is None:
        print(f"  Creating NEW disposition entry...")

        event = ledger.append(
            evidence_id=record.experiment_id,
            evidence_fingerprint_value=fp,
            disposition=VALID,
            reason=(
                "16.5.46 provenance-repaired Corpus Sustain admission: "
                "generation/load/render/causal/persistence PASS; "
                "runtime verified; EFFECT_OBSERVED (RMS increase); "
                "baseline_overrides provenance properly recorded in "
                "EvidenceRecord.experiment; corpus context verified "
                "against 16.5.45 revalidation; causal effect confirmed "
                "vs. baseline with shared Decay=0.02 override."
            ),
            source_refs=(
                "experiments/16_5_45_CORPUS_SUSTAIN_CONTEXT_REVALIDATION.json",
            ),
        )

        print(f"  Disposition event created:")
        print(f"    {event.to_dict()}")

    else:
        print(f"  Using existing disposition entry")

    # ----------------------------------------------------------------
    # 13. RUN DISPOSITION GATE
    # ----------------------------------------------------------------

    print()
    print("Step 13: Run EvidenceDispositionGate.require_admissible()...")

    gate = EvidenceDispositionGate(ledger)

    decision = gate.require_admissible(record)

    print(f"  Gate decision:")
    print(f"    {decision.to_dict()}")

    if not decision.admissible:
        raise RuntimeError(
            f"Disposition gate rejected: {decision.reason}"
        )

    print(f"  [OK] Record admitted by disposition gate")

    # ----------------------------------------------------------------
    # 14. WRITE ADMISSION ARTIFACT
    # ----------------------------------------------------------------

    print()
    print("Step 14: Write admission artifact...")

    artifact = {
        "step": "16.5.46",
        "phase": "ADMIT_REPAIRED_SUSTAIN",
        "status": "COMPLETE",
        "date": "2026-09-06",
        "evidence_id": record.experiment_id,
        "evidence_fingerprint": fp,
        "assertions": {
            "baseline_overrides": {
                "exists": True,
                "target_path": "Env0.plainParams.kParamDecay",
                "value": 0.02,
                "provenance": override.get("provenance"),
            },
            "mutation": {
                "target_path": "Env0.plainParams.kParamSustain",
                "value": 0.3,
                "provenance": mutation.get("provenance"),
            },
            "gates": gates,
            "runtime_verified": runtime_verified,
            "causal_measurement": {
                "metric": causal_measurement.metric,
                "baseline": causal_measurement.baseline,
                "treatment": causal_measurement.treatment,
                "delta": causal_measurement.delta,
                "expected_direction": causal_measurement.expected_direction,
                "observed_direction": causal_measurement.observed_direction,
                "threshold": causal_measurement.threshold,
                "status": causal_measurement.status,
                "measurement_definition_id": expected_measurement_id,
            },
        },
        "disposition": {
            "gate_decision": decision.to_dict(),
            "ledger_verified": True,
            "new_entry_created": existing is None,
        },
        "rationale": (
            "16.5.46 completes admission of the provenance-repaired "
            "Sustain EvidenceRecord. The 16.5.45 revalidation successfully "
            "reproduced the causal effect from 16.5.43.2 while properly "
            "recording baseline_overrides in the EvidenceRecord.experiment "
            "field. This ensures the record can be correctly replayed and "
            "audited. All gates pass; runtime verification confirms; "
            "causal status is EFFECT_OBSERVED with RMS increase. "
            "Disposition ledger updated and gate admits the record."
        ),
    }

    with OUT_ARTIFACT.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, default=str)

    print(f"  Artifact written: {OUT_ARTIFACT}")

    # ----------------------------------------------------------------
    # 15. PICKLE REPAIRED RECORD
    # ----------------------------------------------------------------

    print()
    print("Step 15: Pickle admitted record...")

    with OUT_RECORD_PICKLE.open("wb") as f:
        pickle.dump(record, f)

    print(f"  Record pickle written: {OUT_RECORD_PICKLE}")

    # ================================================================
    # FINAL REPORT
    # ================================================================

    print()
    print("=" * 80)
    print("16.5.46 — REPAIRED SUSTAIN ADMISSION COMPLETE")
    print("=" * 80)
    print()
    print("assertion_status: ALL PASS")
    print("baseline_overrides_provenance: RECORDED")
    print(f"gate_completeness: {gates}")
    print(f"runtime_verified: {runtime_verified}")
    print(f"causal_status: {causal_measurement.status}")
    print(f"measurement_definition_id: {expected_measurement_id}")
    print(f"evidence_fingerprint: {fp}")
    print(f"disposition_ledger_verified: True")
    print(f"new_disposition_entry: {existing is None}")
    print(f"admission_gate_result: ADMISSIBLE")
    print()
    print("final_decision: REPAIRED_SUSTAIN_ADMITTED")
    print()


if __name__ == "__main__":
    main()
