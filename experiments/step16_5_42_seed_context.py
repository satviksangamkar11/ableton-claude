"""
16.5.42 — Native Serum seed-context admission.

Purpose:
    Establish a fresh current-runtime EvidenceRecord starting from Serum's
    own native save_state() output.

This is NOT a new capability claim. The mutation uses an already-established
control only as an actuator for validating the seed/execution path.

Acceptance:
    1. native Serum skeleton capture succeeds
    2. harness state-diff gate passes
    3. both arms load
    4. measurable audio difference is observed
    5. persistence survives Serum save_state()
    6. resulting EvidenceRecord is written separately for later disposition
"""

from pathlib import Path
import pickle
import json

from serum2 import bridge
from serum2.evidence import harness
from serum2.evidence.spec import (
    ExperimentSpec,
    Mutation,
    MeasurementPlan,
    TargetSpec,
    Stimulus,
    CONTROLLED_MULTI_FIELD,
)

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

ROOT = Path(r"D:\ableton claude")
OUT_RECORD = ROOT / "experiments" / "16_5_42_seed_context_record.pkl"
OUT_SUMMARY = ROOT / "experiments" / "16_5_42_SEED_CONTEXT.json"


def main():
    if not Path(VST3).exists():
        raise RuntimeError(f"Serum VST3 not found: {VST3}")

    print("16.5.42 — capturing native Serum seed context...")

    # IMPORTANT:
    # This is Serum's own freshly captured processor state.
    skeleton = bridge.capture_v8_skeleton(VST3)

    # Sanity check the exact native seed before handing it to the harness.
    meta, body = skeleton
    if not meta or not body:
        raise RuntimeError("native Serum seed is empty")

    print("Native seed captured.")
    print("Native seed hash:", bridge.state_hash(meta, body))

    # Use a previously established actuator solely to validate that the
    # native seed can be mutated, loaded, rendered and persisted.
    global0 = body.get("Global0")
    if not isinstance(global0, dict):
        raise RuntimeError("native seed missing Global0")

    plain = global0.get("plainParams")
    if not isinstance(plain, dict):
        raise RuntimeError("native seed Global0 missing plainParams")

    original = plain.get("kParamMasterVolume")
    if not isinstance(original, (int, float)):
        raise RuntimeError(
            f"native seed MasterVolume is not numeric: {original!r}"
        )

    treatment = max(0.0, min(1.0, float(original) * 0.5))

    print("MasterVolume:", original, "->", treatment)

    spec = ExperimentSpec(
        experiment_id="SEED-CONTEXT-16.5.42",
        mutations=[
            Mutation(
                target_path="Global0.plainParams.kParamMasterVolume",
                value=treatment,
                provenance="16.5.42 native-seed validation actuator",
            )
        ],
        prerequisites=[],
        isolation_level=CONTROLLED_MULTI_FIELD,
        claim_subject="seed_context",
        claim_predicate="native_seed_current_runtime_executable",
        measurement_plans=[
            MeasurementPlan(
                metric="overall_rms_db",
                target=TargetSpec(
                    field_path="Global0.plainParams.kParamMasterVolume",
                    module="Global0",
                    parameter="kParamMasterVolume",
                ),
                expected_direction="decrease",
                threshold=0.5,
                stimulus=Stimulus(
                    note=48,
                    velocity=110,
                    note_len=1.8,
                    render_seconds=2.0,
                ),
                kernel_artifact="overall_rms_db.py",
            )
        ],
        notes=(
            "Fresh native Serum 2.0.21 seed-context validation. "
            "The MasterVolume mutation is an existing actuator only; "
            "this experiment does not promote a new capability."
        ),
    )

    rec = harness.run(spec, skeleton=skeleton)

    # ---------------------------------------------------------------
    # Explicit acceptance checks.
    # ---------------------------------------------------------------
    gate = rec.gate_completeness()

    load_pass = (
        rec.load_observation.get("status") == "PASS"
        and rec.load_observation.get("ok") is True
    )

    persistence_pass = (
        rec.persistence_observation.get("status") == "PASS"
        and rec.persistence_observation.get("exact_match") is True
    )

    state_pass = (
        rec.state_observation.get("status") == "PASS"
        and rec.state_observation.get("matches_intent") is True
    )

    effect_observed = any(
        m.status == "EFFECT_OBSERVED"
        for m in rec.causal_measurements
    )

    overall_pass = (
        state_pass
        and load_pass
        and persistence_pass
        and effect_observed
    )

    print()
    print("=== 16.5.42 acceptance ===")
    print("state_pass:", state_pass)
    print("load_pass:", load_pass)
    print("persistence_pass:", persistence_pass)
    print("effect_observed:", effect_observed)
    print("overall_pass:", overall_pass)
    print("gate:", gate)

    # Store the EvidenceRecord independently. Do NOT promote it into the
    # claim/capability chain here.
    with open(OUT_RECORD, "wb") as f:
        pickle.dump(rec, f, protocol=pickle.HIGHEST_PROTOCOL)

    summary = {
        "step": "16.5.42",
        "experiment_id": spec.experiment_id,
        "native_seed_hash": bridge.state_hash(meta, body),
        "mutation": {
            "target": "Global0.plainParams.kParamMasterVolume",
            "baseline": original,
            "treatment": treatment,
        },
        "state_pass": state_pass,
        "load_pass": load_pass,
        "persistence_pass": persistence_pass,
        "effect_observed": effect_observed,
        "overall_pass": overall_pass,
        "record_file": str(OUT_RECORD),
    }

    OUT_SUMMARY.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print("EvidenceRecord:", OUT_RECORD)
    print("Summary:", OUT_SUMMARY)

    if not overall_pass:
        raise SystemExit("16.5.42 FAILED")

    print()
    print("16.5.42 PASS")


if __name__ == "__main__":
    main()
