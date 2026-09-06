"""
16.5.43 — Foundational Current Capability Revalidation

Purpose
-------
Revalidate two foundational controls in BOTH admitted 16.5.42 seed contexts:

    1. Global MasterVolume -> overall_rms_db
    2. Env Release         -> tail_rms_db

The two seed contexts are:

    canonical native:
        fe45bdd8c3518d45

    normalized corpus:
        220cf7ee652d5c4e

Rules
-----
- Current runtime evidence is required.
- Historical evidence is diagnostic only.
- Each capability is qualified independently.
- One context never promotes another context.
- No ClaimEngine/global frontier mutation is performed here.
- Invalid/malformed processor state must fail closed.
- The exact historical Env Release specification is recovered from
  experiments/step15_2_1_release.py and reproduced exactly.
- The exact MasterVolume specification follows the already-valid
  16.5.37 definition.
"""

from __future__ import annotations

import copy
import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, r"D:\ableton claude")

from serum2 import bridge, processor_state
from serum2.evidence import harness
from serum2.evidence import epoch as epoch_mod
from serum2.evidence.record import (
    EFFECT_OBSERVED,
    NO_OBSERVED_EFFECT,
    WRONG_DIRECTION,
    PASS,
)
from serum2.evidence.spec import (
    ExperimentSpec,
    Mutation,
    Stimulus,
    MeasurementPlan,
    TargetSpec,
    SINGLE_FIELD,
    validate,
)
from serum2.evidence.measurement import MeasurementTargetRef


ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3

SEED_ARTIFACT = ROOT / "experiments" / "16_5_42_SEED_CONTEXT.json"
CORPUS_CACHE = ROOT / "experiments" / "_corpus_cache.pkl"
OUT = ROOT / "experiments" / "16_5_43_FOUNDATIONAL_REVALIDATION.json"

EXPECTED_NATIVE_HASH = "fe45bdd8c3518d45"
EXPECTED_CORPUS_HASH = "220cf7ee652d5c4e"

STIM_MASTER = Stimulus(
    note=48,
    velocity=110,
    note_len=1.8,
    render_seconds=2.0,
    tail_start=None,
)

STIM_RELEASE = Stimulus(
    note=60,
    velocity=110,
    note_len=0.4,
    render_seconds=2.0,
    tail_start=0.6,
)


def require_file(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"required file missing: {path}")


def load_seed_artifact():
    require_file(SEED_ARTIFACT)

    data = json.loads(
        SEED_ARTIFACT.read_text(encoding="utf-8")
    )

    if data.get("step") != "16.5.42":
        raise RuntimeError(
            f"unexpected seed artifact step: {data.get('step')!r}"
        )

    if data.get("status") != "PASS":
        raise RuntimeError(
            f"16.5.42 artifact is not PASS: {data.get('status')!r}"
        )

    contexts = data.get("contexts")
    if not isinstance(contexts, dict):
        raise RuntimeError("16.5.42 artifact lacks contexts")

    canonical = contexts.get("canonical_native")
    corpus = contexts.get("normalized_corpus")

    if not isinstance(canonical, dict):
        raise RuntimeError("missing canonical_native seed manifest")

    if not isinstance(corpus, dict):
        raise RuntimeError("missing normalized_corpus seed manifest")

    return data, canonical, corpus


def build_seed_contexts():
    """
    Reconstruct the two seed contexts exactly as 16.5.42 does.

    canonical:
        fresh native Serum save_state skeleton

    normalized corpus:
        _corpus_cache.pkl bodies[4]
        + native processor component
        + native metadata
    """

    native_meta, native_body = bridge.capture_v8_skeleton(VST3)

    processor_state.require_processor_state(
        (native_meta, native_body),
        source="16.5.43.canonical",
    )

    native_hash = bridge.state_hash(
        native_meta,
        native_body,
    )

    if native_hash != EXPECTED_NATIVE_HASH:
        raise RuntimeError(
            "canonical seed hash changed: "
            f"expected {EXPECTED_NATIVE_HASH}, got {native_hash}"
        )

    require_file(CORPUS_CACHE)

    with CORPUS_CACHE.open("rb") as f:
        corpus = pickle.load(f)

    if not isinstance(corpus, dict):
        raise RuntimeError("unexpected corpus cache structure")

    bodies = corpus.get("bodies")

    if not isinstance(bodies, list):
        raise RuntimeError("corpus cache lacks bodies")

    if len(bodies) <= 4:
        raise RuntimeError("corpus cache lacks bodies[4]")

    corpus_body = copy.deepcopy(bodies[4])

    if "component" not in native_body:
        raise RuntimeError(
            "native processor body lacks component"
        )

    corpus_body["component"] = copy.deepcopy(
        native_body["component"]
    )

    corpus_meta = copy.deepcopy(native_meta)

    processor_state.require_processor_state(
        (corpus_meta, corpus_body),
        source="16.5.43.normalized_corpus",
    )

    corpus_hash = bridge.state_hash(
        corpus_meta,
        corpus_body,
    )

    if corpus_hash != EXPECTED_CORPUS_HASH:
        raise RuntimeError(
            "normalized corpus seed hash changed: "
            f"expected {EXPECTED_CORPUS_HASH}, got {corpus_hash}"
        )

    return {
        "canonical_native": (
            copy.deepcopy(native_meta),
            copy.deepcopy(native_body),
        ),
        "normalized_corpus": (
            copy.deepcopy(corpus_meta),
            copy.deepcopy(corpus_body),
        ),
    }


def make_master_volume_spec(context_name: str) -> ExperimentSpec:
    return ExperimentSpec(
        experiment_id=(
            f"16.5.43-{context_name}-GLOBAL-MASTERVOLUME"
        ),
        mutations=[
            Mutation(
                "Global0.plainParams.kParamMasterVolume",
                0.1,
                "16.5.37 current revalidation",
            )
        ],
        prerequisites=[],
        isolation_level=SINGLE_FIELD,
        claim_subject="global_master_volume",
        claim_predicate="affects_overall_rms_db",
        baseline_overrides=[],
        measurement_plans=[
            MeasurementPlan(
                metric="overall_rms_db",
                target=MeasurementTargetRef(
                    "Global0.plainParams.kParamMasterVolume",
                    None,
                    None,
                ),
                expected_direction="decrease",
                threshold=3.0,
                stimulus=STIM_MASTER,
                kernel_artifact="overall_rms_db.py",
            )
        ],
        notes=(
            "Exact 16.5.37 specification: "
            "Global0.plainParams.kParamMasterVolume=0.1, "
            "overall_rms_db, decrease, threshold=3.0, "
            "Stimulus(note=48, velocity=110, note_len=1.8, "
            "render_seconds=2.0, tail_start=None)."
        ),
    )


def make_release_spec(context_name: str) -> ExperimentSpec:
    """
    Exact source definition recovered from:
        experiments/step15_2_1_release.py
    """

    return ExperimentSpec(
        experiment_id=(
            f"16.5.43-{context_name}-ENV-RELEASE"
        ),
        mutations=[
            Mutation(
                "Env0.plainParams.kParamRelease",
                1.0,
                "16.5.15 foundational current revalidation",
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "shared: short decay so we're fully settled before note-off",
            )
        ],
        isolation_level=SINGLE_FIELD,
        claim_subject="envelope_field:Env.kParamRelease",
        claim_predicate="affects_tail_rms_db",
        measurement_plans=[
            MeasurementPlan(
                metric="tail_rms_db",
                target=TargetSpec(
                    "Env0.plainParams.kParamRelease",
                    "Env",
                    "kParamRelease",
                ),
                expected_direction="increase",
                threshold=3.0,
                stimulus=STIM_RELEASE,
                kernel_artifact="tail_rms_db.py",
            )
        ],
        notes=(
            "Exact source definition recovered from "
            "step15_2_1_release.py: both arms use Decay=0.02s; "
            "control uses implicit default Release; treatment uses "
            "Release=1.0s; note_len=0.4s; tail measurement starts "
            "at 0.6s."
        ),
    )


def serialize_record(rec):
    data = rec.to_dict()

    return {
        "experiment_id": rec.experiment_id,
        "gates": rec.gate_completeness(),
        "runtime_verified": rec.runtime_verified(),
        "outcome_signature": rec.outcome_signature(),
        "state_observation": rec.state_observation,
        "load_observation": rec.load_observation,
        "render_observation": rec.render_observation,
        "persistence_observation": rec.persistence_observation,
        "runtime_verifications": list(
            rec.runtime_verifications
        ),
        "causal_measurements": [
            {
                "metric": m.metric,
                "target": {
                    "field_path": m.target.field_path,
                    "module": m.target.module,
                    "parameter": m.target.parameter,
                },
                "baseline": m.baseline,
                "treatment": m.treatment,
                "delta": m.delta,
                "expected_direction": m.expected_direction,
                "observed_direction": m.observed_direction,
                "threshold": m.threshold,
                "status": m.status,
                "measurement_condition_signature":
                    m.measurement_condition_signature,
                "measurement_definition_id":
                    m.measurement_definition_id,
            }
            for m in rec.causal_measurements
        ],
        "evidence_record": data,
    }


def qualification_for(rec):
    """
    Current qualification gate.

    No historical value is used to qualify the capability.
    """

    if rec is None:
        return False, ["missing EvidenceRecord"]

    failures = []

    gates = rec.gate_completeness()

    required_gate_values = {
        "generation": PASS,
        "load": PASS,
        "render": PASS,
        "causal": PASS,
        "persistence": PASS,
    }

    for gate, expected in required_gate_values.items():
        if gates.get(gate) != expected:
            failures.append(
                f"{gate}={gates.get(gate)!r}, expected {expected!r}"
            )

    if not rec.runtime_verified():
        failures.append("runtime prerequisites not verified")

    if not rec.state_observation.get("matches_intent"):
        failures.append("state_observation.matches_intent is false")

    if not rec.causal_measurements:
        failures.append("no causal measurement")
    else:
        for m in rec.causal_measurements:
            if m.status != EFFECT_OBSERVED:
                failures.append(
                    f"causal status={m.status!r}"
                )

    return len(failures) == 0, failures


def run_case(context_name, skeleton, label):
    print("=" * 80)
    print(
        f"CONTEXT={context_name} | CAPABILITY={label}"
    )
    print("=" * 80)

    if label == "Global MasterVolume":
        spec = make_master_volume_spec(context_name)
    elif label == "Env Release":
        spec = make_release_spec(context_name)
    else:
        raise RuntimeError(
            f"unknown capability label: {label}"
        )

    validate(spec)

    processor_state.require_processor_state(
        skeleton,
        source=(
            f"16.5.43.{context_name}.{label}"
        ),
    )

    print("  executing harness.run(spec, skeleton=seed)")

    rec = harness.run(
        spec,
        skeleton=skeleton,
    )

    qualification, failures = qualification_for(rec)

    print("  gates:", rec.gate_completeness())
    print(
        "  runtime_verified:",
        rec.runtime_verified(),
    )
    print(
        "  matches_intent:",
        rec.state_observation.get(
            "matches_intent"
        ),
    )

    if rec.causal_measurements:
        m = rec.causal_measurements[0]

        print(
            "  causal:"
            f" baseline={m.baseline:.6f}"
            f" treatment={m.treatment:.6f}"
            f" delta={m.delta:+.6f}"
            f" direction={m.observed_direction}"
            f" status={m.status}"
        )

        print(
            "  measurement_definition_id:",
            m.measurement_definition_id,
        )

    print(
        "  persistence:",
        rec.persistence_observation.get("status"),
    )

    print(
        "  CURRENT QUALIFICATION:",
        "PASS" if qualification else "FAIL",
    )

    if failures:
        for failure in failures:
            print("   -", failure)

    return rec, qualification, failures


def main():
    print("=" * 80)
    print("16.5.43 — FOUNDATIONAL CURRENT CAPABILITY REVALIDATION")
    print("=" * 80)
    print()

    if not Path(VST3).exists():
        raise RuntimeError(
            f"Serum VST3 not found: {VST3}"
        )

    print("[1/4] Loading accepted 16.5.42 artifact...")
    seed_artifact, canonical_manifest, corpus_manifest = (
        load_seed_artifact()
    )

    print(
        "  artifact status:",
        seed_artifact["status"],
    )

    print(
        "  canonical artifact hash:",
        canonical_manifest["state_hash"],
    )

    print(
        "  corpus artifact hash:",
        corpus_manifest["state_hash"],
    )

    print()

    print("[2/4] Reconstructing and validating seed contexts...")

    contexts = build_seed_contexts()

    print(
        "  canonical:",
        bridge.state_hash(
            *contexts["canonical_native"]
        ),
    )

    print(
        "  corpus:",
        bridge.state_hash(
            *contexts["normalized_corpus"]
        ),
    )

    print()

    results = {}
    views = {
        "canonical_native": {
            "qualified_controls": []
        },
        "normalized_corpus": {
            "qualified_controls": []
        },
    }

    print("[3/4] Running four current-runtime revalidations...")
    print()

    for context_name, skeleton in contexts.items():

        context_results = {}

        for label in (
            "Global MasterVolume",
            "Env Release",
        ):
            rec, qualified, failures = run_case(
                context_name,
                skeleton,
                label,
            )

            key = label.lower().replace(" ", "_")

            context_results[key] = {
                "qualified": qualified,
                "failures": failures,
                "record": serialize_record(rec),
            }

            if qualified:
                if label == "Global MasterVolume":
                    role = "loudness"
                else:
                    role = "duration"

                views[context_name][
                    "qualified_controls"
                ].append(
                    {
                        "role": role,
                        "control": label,
                        "experiment_id": rec.experiment_id,
                    }
                )

            print()

        results[context_name] = context_results

    print("[4/4] Final gate...")
    print()

    final_gate = True

    for context_name in (
        "canonical_native",
        "normalized_corpus",
    ):
        controls = views[context_name][
            "qualified_controls"
        ]

        loudness = any(
            c["role"] == "loudness"
            and c["control"] == "Global MasterVolume"
            for c in controls
        )

        duration = any(
            c["role"] == "duration"
            and c["control"] == "Env Release"
            for c in controls
        )

        views[context_name][
            "loudness_control_qualified"
        ] = loudness

        views[context_name][
            "duration_control_qualified"
        ] = duration

        context_pass = loudness and duration

        views[context_name]["status"] = (
            "CURRENTLY_QUALIFIED"
            if context_pass
            else "INSUFFICIENT"
        )

        print(
            f"  {context_name}: "
            f"loudness={loudness} "
            f"duration={duration}"
        )

        if not context_pass:
            final_gate = False

    overall_status = (
        "PASS"
        if final_gate
        else "FAIL"
    )

    result = {
        "step": "16.5.43",
        "status": overall_status,
        "purpose": (
            "Foundational current capability "
            "revalidation in both admitted seed contexts"
        ),
        "environment": {
            "serum_vst3": VST3,
            "sample_rate": 44100,
            "block_size": 512,
        },
        "seed_contexts": {
            "canonical_native": {
                "expected_state_hash":
                    EXPECTED_NATIVE_HASH,
                "actual_state_hash":
                    bridge.state_hash(
                        *contexts["canonical_native"]
                    ),
                "artifact_state_hash":
                    canonical_manifest["state_hash"],
            },
            "normalized_corpus": {
                "expected_state_hash":
                    EXPECTED_CORPUS_HASH,
                "actual_state_hash":
                    bridge.state_hash(
                        *contexts["normalized_corpus"]
                    ),
                "artifact_state_hash":
                    corpus_manifest["state_hash"],
            },
        },
        "results": results,
        "current_capability_views": views,
        "admission_rules": {
            "historical_evidence_used_for_current_qualification": False,
            "cross_context_promotion": False,
            "claim_engine_mutation": False,
            "frontier_mutation": False,
        },
        "final_gate": {
            "both_contexts_have_loudness": all(
                views[c]["loudness_control_qualified"]
                for c in views
            ),
            "both_contexts_have_duration": all(
                views[c]["duration_control_qualified"]
                for c in views
            ),
            "passed": final_gate,
        },
    }

    OUT.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)

    if final_gate:
        print("16.5.43 PASS")
    else:
        print("16.5.43 FAIL")

    print("=" * 80)
    print("Artifact:", OUT)


if __name__ == "__main__":
    main()