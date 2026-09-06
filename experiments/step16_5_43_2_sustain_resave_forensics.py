from __future__ import annotations

import copy
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ableton claude")

from serum2 import bridge, processor_state, pathmerge
from serum2.evidence import epoch as epoch_mod
from serum2.evidence import harness


ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3
CACHE = ROOT / "experiments" / "_corpus_cache.pkl"

EXPECTED_HASH = "220cf7ee652d5c4e"


def main():
    print("=" * 80)
    print("16.5.43.2 — SUSTAIN RESAVE FORENSICS")
    print("=" * 80)

    # ------------------------------------------------------------
    # 1. Capture native state
    # ------------------------------------------------------------

    native_meta, native_body = bridge.capture_v8_skeleton(VST3)

    processor_state.require_processor_state(
        (native_meta, native_body),
        source="16.5.43.2.sustain_resave.native",
    )

    # ------------------------------------------------------------
    # 2. Reconstruct exact normalized corpus seed
    # ------------------------------------------------------------

    with CACHE.open("rb") as f:
        corpus = pickle.load(f)

    bodies = corpus["bodies"]
    corpus_body = copy.deepcopy(bodies[4])

    corpus_body["component"] = copy.deepcopy(
        native_body["component"]
    )

    corpus_meta = copy.deepcopy(native_meta)

    processor_state.require_processor_state(
        (corpus_meta, corpus_body),
        source="16.5.43.2.sustain_resave.corpus",
    )

    corpus_hash = bridge.state_hash(
        corpus_meta,
        corpus_body,
    )

    print()
    print("CORPUS HASH:")
    print("  ", corpus_hash)
    print("  expected:", EXPECTED_HASH)

    if corpus_hash != EXPECTED_HASH:
        raise RuntimeError("Corpus hash mismatch")

    # ------------------------------------------------------------
    # 3. Build the exact treatment arm
    # ------------------------------------------------------------

    from serum2.evidence.spec import (
        ExperimentSpec,
        Mutation,
        Stimulus,
        MeasurementPlan,
        TargetSpec,
        SINGLE_FIELD,
    )

    spec = ExperimentSpec(
        experiment_id="16.5.43.2-SUSTAIN-RESAVE-FORENSICS",
        mutations=[
            Mutation(
                "Env0.plainParams.kParamSustain",
                1.0,
                "forensic Sustain=1.0",
            )
        ],
        prerequisites=[],
        isolation_level=SINGLE_FIELD,
        claim_subject="diagnostic",
        claim_predicate="diagnostic_only",
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "shared Decay",
            )
        ],
        measurement_plans=[
            MeasurementPlan(
                metric="sustain_window_rms_db",
                target=TargetSpec(
                    "Env0.plainParams.kParamSustain",
                    "Env",
                    "kParamSustain",
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
        notes="Diagnostic only",
        probe_semantics="NUMERIC_CLAMP_RANGE",
    )

    treatment_meta, treatment_body = harness.build_arm(
        (corpus_meta, corpus_body),
        spec,
        apply_mutations=True,
    )

    print()
    print("PRE-SAVE TREATMENT VALUE:")
    print(
        json.dumps(
            {
                "value": treatment_body
                .get("Env0", {})
                .get("plainParams", {})
                .get("kParamSustain"),
                "type": type(
                    treatment_body
                    .get("Env0", {})
                    .get("plainParams", {})
                    .get("kParamSustain")
                ).__name__,
                "Env0_plainParams": treatment_body
                .get("Env0", {})
                .get("plainParams", {}),
            },
            indent=2,
            default=str,
        )
    )

    # ------------------------------------------------------------
    # 4. Ask Serum itself to save the treatment state
    # ------------------------------------------------------------

    print()
    print("RESAVING THROUGH SERUM...")

    saved_meta, saved_body = harness.resave_state(
        treatment_meta,
        treatment_body,
        spec,
    )

    processor_state.require_processor_state(
        (saved_meta, saved_body),
        source="16.5.43.2.sustain_resave.resaved",
    )

    # ------------------------------------------------------------
    # 5. Inspect exact decoded result
    # ------------------------------------------------------------

    env0 = saved_body.get("Env0")
    plain = (
        env0.get("plainParams")
        if isinstance(env0, dict)
        else None
    )

    print()
    print("=" * 80)
    print("POST-RESAVE ENV0")
    print("=" * 80)

    print(
        json.dumps(
            {
                "Env0_type": type(env0).__name__,
                "Env0_keys": (
                    sorted(env0.keys())
                    if isinstance(env0, dict)
                    else []
                ),
                "plainParams_type": (
                    type(plain).__name__
                    if plain is not None
                    else None
                ),
                "plainParams": plain,
            },
            indent=2,
            default=str,
        )
    )

    # ------------------------------------------------------------
    # 6. Exact target lookup
    # ------------------------------------------------------------

    try:
        decoded_value = pathmerge.read_path_value(
            saved_body,
            "Env0.plainParams.kParamSustain",
        )
    except Exception as exc:
        decoded_value = {
            "ERROR": f"{type(exc).__name__}: {exc}"
        }

    print()
    print("EXACT TARGET READ:")
    print(
        json.dumps(
            {
                "target":
                    "Env0.plainParams.kParamSustain",
                "value": decoded_value,
                "type":
                    type(decoded_value).__name__,
            },
            indent=2,
            default=str,
        )
    )

    # ------------------------------------------------------------
    # 7. Search the entire decoded body for Sustain-like fields
    # ------------------------------------------------------------

    matches = []

    def walk(obj, path="root"):
        if isinstance(obj, dict):
            for key, value in obj.items():
                current = f"{path}.{key}"

                if "sustain" in key.lower():
                    matches.append(
                        {
                            "path": current,
                            "value": value,
                            "type": type(value).__name__,
                        }
                    )

                walk(value, current)

        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                walk(value, f"{path}[{idx}]")

    walk(saved_body)

    print()
    print("=" * 80)
    print("ALL SUSTAIN-LIKE FIELDS AFTER RESAVE")
    print("=" * 80)

    print(
        json.dumps(
            matches,
            indent=2,
            default=str,
        )
    )

    # ------------------------------------------------------------
    # 8. State hashes
    # ------------------------------------------------------------

    print()
    print("=" * 80)
    print("HASHES")
    print("=" * 80)

    print(
        "pre-save treatment:",
        bridge.state_hash(
            treatment_meta,
            treatment_body,
        ),
    )

    print(
        "post-save state:",
        bridge.state_hash(
            saved_meta,
            saved_body,
        ),
    )

    print()
    print("FORENSICS COMPLETE")


if __name__ == "__main__":
    main()