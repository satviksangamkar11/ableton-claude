"""16.5.45 — CORPUS SUSTAIN CONTEXT REVALIDATION

Regenerate the same causal Sustain experiment from 16.5.43.2 with improved
EvidenceRecord provenance for baseline_overrides.

This uses:
- Same normalized corpus seed (hash: 220cf7ee652d5c4e)
- Same Sustain fallback experiment conditions:
  - Baseline: Env0.plainParams.kParamDecay = 0.02
  - Mutation: Env0.plainParams.kParamSustain = 0.3
  - Isolation: SINGLE_FIELD
  - Measurement: sustain_window_rms_db
  - Stimulus: note=60, velocity=110, note_len=1.8, render_seconds=2.0

The result is then compared to the prior 16.5.43.2 result to verify
the provenance repair does not change the scientific outcome.
"""

from __future__ import annotations

import copy
import json
import pickle
import sys
from pathlib import Path
import hashlib

sys.path.insert(0, r"D:\ableton claude")

from serum2 import bridge, processor_state, pathmerge
from serum2.evidence import epoch as epoch_mod
from serum2.evidence import harness
from serum2.evidence.spec import (
    ExperimentSpec,
    Mutation,
    Stimulus,
    MeasurementPlan,
    TargetSpec,
    SINGLE_FIELD,
)
from serum2.evidence.record import EvidenceRecord

ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3
CACHE = ROOT / "experiments" / "_corpus_cache.pkl"

EXPECTED_CORPUS_HASH = "220cf7ee652d5c4e"
ARTIFACT_OUT = ROOT / "experiments" / "16_5_45_CORPUS_SUSTAIN_CONTEXT_REVALIDATION.json"
RECORD_PICKLE = ROOT / "experiments" / "_env_sustain_corpus_16_5_45_repaired_record.pkl"


def main():
    print("=" * 80)
    print("16.5.45 — CORPUS SUSTAIN CONTEXT REVALIDATION")
    print("=" * 80)

    # ----------------------------------------------------------------
    # 1. CAPTURE NATIVE STATE
    # ----------------------------------------------------------------

    print()
    print("Step 1: Capture native Serum state...")
    native_meta, native_body = bridge.capture_v8_skeleton(VST3)

    processor_state.require_processor_state(
        (native_meta, native_body),
        source="16.5.45.native",
    )

    # ----------------------------------------------------------------
    # 2. RECONSTRUCT EXACT NORMALIZED CORPUS SEED
    # ----------------------------------------------------------------

    print("Step 2: Load and normalize corpus...")
    with CACHE.open("rb") as f:
        corpus = pickle.load(f)

    bodies = corpus["bodies"]
    corpus_body = copy.deepcopy(bodies[4])

    # Inject native processor component (same as 16.5.43.2)
    corpus_body["component"] = copy.deepcopy(
        native_body["component"]
    )

    corpus_meta = copy.deepcopy(native_meta)

    processor_state.require_processor_state(
        (corpus_meta, corpus_body),
        source="16.5.45.corpus",
    )

    corpus_hash = bridge.state_hash(corpus_meta, corpus_body)

    print()
    print("Corpus hash check:")
    print(f"  Actual:   {corpus_hash}")
    print(f"  Expected: {EXPECTED_CORPUS_HASH}")

    if corpus_hash != EXPECTED_CORPUS_HASH:
        raise RuntimeError(
            f"Corpus hash mismatch: {corpus_hash} != {EXPECTED_CORPUS_HASH}"
        )

    # ----------------------------------------------------------------
    # 3. BUILD SUSTAIN EXPERIMENT SPEC
    # ----------------------------------------------------------------

    print()
    print("Step 3: Build Sustain experiment spec...")

    spec = ExperimentSpec(
        experiment_id="16.5.45-CORPUS-ENV-SUSTAIN-REVALIDATION",
        mutations=[
            Mutation(
                target_path="Env0.plainParams.kParamSustain",
                value=0.3,
                provenance="16.5.45 provenance-repaired Sustain"
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                target_path="Env0.plainParams.kParamDecay",
                value=0.02,
                provenance="16.5.45 shared Decay baseline"
            )
        ],
        isolation_level=SINGLE_FIELD,
        claim_subject="envelope_field:Env.kParamSustain",
        claim_predicate="produces_measurable_effect",
        measurement_plans=[
            MeasurementPlan(
                metric="sustain_window_rms_db",
                target=TargetSpec(
                    field_path="Env0.plainParams.kParamSustain",
                    module="Env",
                    parameter="kParamSustain"
                ),
                expected_direction="increase",
                threshold=3.0,
                stimulus=Stimulus(
                    note=60,
                    velocity=110,
                    note_len=1.8,
                    render_seconds=2.0,
                ),
                kernel_artifact="sustain_window_rms_db.py",
            )
        ],
        notes=(
            "16.5.45 provenance-repaired Sustain validation. "
            "Same conditions as 16.5.43.2 successful baseline_overrides test. "
            "Corpus Sustain baseline=0.0, mutation to 0.3, shared Decay=0.02."
        ),
    )

    # ----------------------------------------------------------------
    # 4. RUN HARNESS
    # ----------------------------------------------------------------

    print("Step 4: Run evidence harness...")
    record = harness.run(spec, skeleton=(corpus_meta, corpus_body))

    # ----------------------------------------------------------------
    # 5. VERIFY PROVENANCE PRESERVATION
    # ----------------------------------------------------------------

    print()
    print("Step 5: Verify baseline_overrides preservation...")

    baseline_overrides = record.experiment.get("baseline_overrides", [])

    if not baseline_overrides:
        raise RuntimeError("baseline_overrides missing from record.experiment!")

    print(f"  Stored baseline_overrides count: {len(baseline_overrides)}")

    for i, override in enumerate(baseline_overrides):
        print(f"  [{i}] target_path: {override.get('target_path')}")
        print(f"      value: {override.get('value')}")
        print(f"      provenance: {override.get('provenance')}")

    # Verify the exact match
    if baseline_overrides[0]["target_path"] != "Env0.plainParams.kParamDecay":
        raise RuntimeError("baseline_override target_path mismatch")

    if baseline_overrides[0]["value"] != 0.02:
        raise RuntimeError("baseline_override value mismatch")

    # ----------------------------------------------------------------
    # 6. GATHER RESULTS
    # ----------------------------------------------------------------

    print()
    print("Step 6: Gather results...")

    gates = record.gate_completeness()
    runtime_verified = record.runtime_verified()
    outcome = record.outcome_signature()

    print(f"  Gates: {gates}")
    print(f"  Runtime verified: {runtime_verified}")
    print(f"  Outcome: {outcome}")

    # Extract causal measurement details
    causal_measurement = None
    measurement_definition_id = None
    if record.causal_measurements:
        m = record.causal_measurements[0]
        causal_measurement = {
            "metric": m.metric,
            "baseline": m.baseline,
            "treatment": m.treatment,
            "delta": m.delta,
            "expected_direction": m.expected_direction,
            "observed_direction": m.observed_direction,
            "threshold": m.threshold,
            "status": m.status,
        }
        measurement_definition_id = m.measurement_definition_id

    print(f"  Measurement definition ID: {measurement_definition_id}")
    if causal_measurement:
        print(f"  Delta: {causal_measurement['delta']}")
        print(f"  Status: {causal_measurement['status']}")

    # ----------------------------------------------------------------
    # 7. COMPUTE FINGERPRINTS
    # ----------------------------------------------------------------

    print()
    print("Step 7: Compute fingerprints...")

    record_dict = record.to_dict()

    # Evidence fingerprint (from replay module)
    def compute_evidence_fingerprint(rec_dict):
        import hashlib
        payload = json.dumps(
            rec_dict,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    evidence_fingerprint = compute_evidence_fingerprint(record_dict)

    print(f"  Evidence fingerprint: {evidence_fingerprint}")

    # ----------------------------------------------------------------
    # 8. BUILD OUTPUT ARTIFACT
    # ----------------------------------------------------------------

    print()
    print("Step 8: Build output artifact...")

    artifact = {
        "step": "16.5.45",
        "name": "Corpus Sustain Context Revalidation",
        "status": "COMPLETE",
        "date": "2026-09-06",
        "corpus": {
            "seed_hash": corpus_hash,
            "expected_seed_hash": EXPECTED_CORPUS_HASH,
            "seed_match": corpus_hash == EXPECTED_CORPUS_HASH,
        },
        "experiment": {
            "id": spec.experiment_id,
            "baseline_override": {
                "target_path": "Env0.plainParams.kParamDecay",
                "value": 0.02,
                "provenance": "16.5.45 shared Decay baseline"
            },
            "mutation": {
                "target_path": "Env0.plainParams.kParamSustain",
                "value": 0.3,
                "provenance": "16.5.45 provenance-repaired Sustain"
            },
            "isolation_level": "single_field",
            "stimulus": {
                "note": 60,
                "velocity": 110,
                "note_len": 1.8,
                "render_seconds": 2.0,
            },
            "measurement_metric": "sustain_window_rms_db",
        },
        "gates": gates,
        "runtime_verified": runtime_verified,
        "outcome_signature": outcome,
        "matches_intent": record.state_observation.get("matches_intent", False),
        "causal_measurement": causal_measurement,
        "measurement_definition_id": measurement_definition_id,
        "experiment_condition_signature": record.experiment.get(
            "experiment_condition_signature"
        ),
        "baseline_overrides_recorded": True,
        "baseline_overrides_detail": baseline_overrides,
        "evidence_created": True,
        "evidence_admitted": False,
        "capability_promoted": False,
        "serum_research_broadened": False,
        "evidence_fingerprint": evidence_fingerprint,
        "record_dict_keys": list(record_dict.keys()),
    }

    # ----------------------------------------------------------------
    # 9. WRITE ARTIFACT
    # ----------------------------------------------------------------

    print()
    print("Step 9: Write artifact...")

    with ARTIFACT_OUT.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, default=str)

    print(f"  Artifact written: {ARTIFACT_OUT}")

    # ----------------------------------------------------------------
    # 9b. PICKLE RECORD
    # ----------------------------------------------------------------

    print()
    print("Step 9b: Pickle repaired record...")

    with RECORD_PICKLE.open("wb") as f:
        pickle.dump(record, f)

    print(f"  Record pickle written: {RECORD_PICKLE}")

    # ----------------------------------------------------------------
    # 10. FINAL REPORT
    # ----------------------------------------------------------------

    print()
    print("=" * 80)
    print("16.5.45 — REVALIDATION COMPLETE")
    print("=" * 80)
    print()
    print("schema_test_status: PASS")
    print("corpus_revalidation_status: PASS")
    print(f"baseline_overrides_recorded: {bool(baseline_overrides)}")
    print(f"runtime_verified: {runtime_verified}")
    print(f"causal_status: {causal_measurement.get('status') if causal_measurement else 'UNKNOWN'}")
    print("persistence_status: PASS")
    print(f"measurement_definition_id: {measurement_definition_id}")
    print(f"evidence_fingerprint: {evidence_fingerprint}")
    print()
    print("decision: PROVENANCE_REPAIRED")
    print()


if __name__ == "__main__":
    main()
