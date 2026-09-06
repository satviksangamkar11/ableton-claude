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
from serum2.evidence.record import PASS
from serum2.evidence.spec import (
    ExperimentSpec,
    Mutation,
    Stimulus,
    MeasurementPlan,
    TargetSpec,
    SINGLE_FIELD,
    validate,
)


ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3
CACHE = ROOT / "experiments" / "_corpus_cache.pkl"
OUT = ROOT / "experiments" / "16_5_43_1_CORPUS_ENV_FORENSICS.json"

EXPECTED_CORPUS_HASH = "220cf7ee652d5c4e"


def require_file(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"required file missing: {path}")


def build_corpus_seed():
    """
    Exact normalized-corpus reconstruction already established by
    16.5.42 / 16.5.43:

        _corpus_cache.pkl bodies[4]
        + native processor component
        + native metadata
    """

    native_meta, native_body = bridge.capture_v8_skeleton(VST3)

    processor_state.require_processor_state(
        (native_meta, native_body),
        source="16.5.43.1.canonical",
    )

    require_file(CACHE)

    with CACHE.open("rb") as f:
        corpus = pickle.load(f)

    if not isinstance(corpus, dict):
        raise RuntimeError("unexpected corpus cache structure")

    bodies = corpus.get("bodies")
    if not isinstance(bodies, list) or len(bodies) <= 4:
        raise RuntimeError("corpus cache lacks bodies[4]")

    corpus_body = copy.deepcopy(bodies[4])

    if "component" not in native_body:
        raise RuntimeError(
            "native processor body lacks required 'component'"
        )

    corpus_body["component"] = copy.deepcopy(
        native_body["component"]
    )

    corpus_meta = copy.deepcopy(native_meta)

    processor_state.require_processor_state(
        (corpus_meta, corpus_body),
        source="16.5.43.1.normalized_corpus",
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

    return corpus_meta, corpus_body, corpus_hash


def env_snapshot(body: dict) -> dict:
    env0 = body.get("Env0")

    if not isinstance(env0, dict):
        return {
            "present": False,
            "type": type(env0).__name__,
            "keys": [],
            "plainParams_present": False,
            "plainParams_keys": [],
            "fields": {},
        }

    plain = env0.get("plainParams")

    if not isinstance(plain, dict):
        plain = {}

    fields = {}

    for key in (
        "kParamAttack",
        "kParamDecay",
        "kParamSustain",
        "kParamRelease",
    ):
        if key in plain:
            fields[key] = {
                "present": True,
                "value": plain[key],
                "python_type": type(plain[key]).__name__,
            }
        else:
            fields[key] = {
                "present": False,
                "value": None,
                "python_type": None,
            }

    return {
        "present": True,
        "type": type(env0).__name__,
        "keys": sorted(env0.keys()),
        "plainParams_present": "plainParams" in env0,
        "plainParams_keys": sorted(plain.keys()),
        "fields": fields,
    }


def compare_envs(canonical: dict, corpus: dict) -> dict:
    result = {}

    for key in (
        "kParamAttack",
        "kParamDecay",
        "kParamSustain",
        "kParamRelease",
    ):
        c = canonical["fields"][key]
        p = corpus["fields"][key]

        result[key] = {
            "canonical": c,
            "corpus": p,
            "equal": (
                c["present"] == p["present"]
                and c["value"] == p["value"]
                and c["python_type"] == p["python_type"]
            ),
        }

    return result


def make_spec(
    experiment_id: str,
    mutation_path: str,
    mutation_value,
    mutation_note: str,
    metric: str,
    expected_direction: str,
    stimulus: Stimulus,
):
    return ExperimentSpec(
        experiment_id=experiment_id,
        mutations=[
            Mutation(
                mutation_path,
                mutation_value,
                mutation_note,
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "16.5.43.1 diagnostic: shared short decay",
            )
        ],
        isolation_level=SINGLE_FIELD,
        claim_subject=f"diagnostic:{mutation_path}",
        claim_predicate="diagnostic_only",
        measurement_plans=[
            MeasurementPlan(
                metric=metric,
                target=TargetSpec(
                    mutation_path,
                    "Env",
                    mutation_path.rsplit(".", 1)[-1],
                ),
                expected_direction=expected_direction,
                threshold=3.0,
                stimulus=stimulus,
                kernel_artifact=(
                    "sustain_window_rms_db.py"
                    if metric == "sustain_window_rms_db"
                    else "tail_rms_db.py"
                ),
            )
        ],
        notes=(
            "16.5.43.1 diagnostic only. "
            "No capability promotion."
        ),
    )


def serialize_record(rec) -> dict:
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


def run_diagnostic(
    *,
    label: str,
    spec: ExperimentSpec,
    corpus_seed,
) -> dict:
    validate(spec)

    processor_state.require_processor_state(
        corpus_seed,
        source=f"16.5.43.1.{label}.run",
    )

    print()
    print(f"--- {label} ---")
    print(f"experiment_id: {spec.experiment_id}")

    rec = harness.run(
        spec,
        skeleton=corpus_seed,
    )

    gates = rec.gate_completeness()
    runtime_verified = rec.runtime_verified()
    matches_intent = rec.state_observation.get(
        "matches_intent",
        False,
    )

    print("gates:", gates)
    print("runtime_verified:", runtime_verified)
    print("matches_intent:", matches_intent)

    causal = []

    for m in rec.causal_measurements:
        item = {
            "metric": m.metric,
            "baseline": m.baseline,
            "treatment": m.treatment,
            "delta": m.delta,
            "expected_direction": m.expected_direction,
            "observed_direction": m.observed_direction,
            "threshold": m.threshold,
            "status": m.status,
            "measurement_definition_id":
                m.measurement_definition_id,
        }

        causal.append(item)

        print(
            "causal:"
            f" metric={m.metric}"
            f" baseline={m.baseline:.6f}"
            f" treatment={m.treatment:.6f}"
            f" delta={m.delta:+.6f}"
            f" direction={m.observed_direction}"
            f" status={m.status}"
        )

    persistence_status = rec.persistence_observation.get(
        "status"
    )

    print("persistence:", persistence_status)

    return {
        "label": label,
        "experiment_id": spec.experiment_id,
        "gates": gates,
        "runtime_verified": runtime_verified,
        "matches_intent": matches_intent,
        "causal_measurements": causal,
        "persistence": rec.persistence_observation,
        "record": serialize_record(rec),
    }


def main():
    print("=" * 80)
    print("16.5.43.1 — CORPUS ENV FORENSICS")
    print("=" * 80)
    print()

    require_file(Path(VST3))

    # ------------------------------------------------------------
    # STEP 1 — exact seed reconstruction
    # ------------------------------------------------------------

    print("[1/6] Reconstructing normalized corpus seed...")

    corpus_meta, corpus_body, corpus_hash = build_corpus_seed()

    print(f"  corpus state hash: {corpus_hash}")
    print(f"  expected hash:     {EXPECTED_CORPUS_HASH}")
    print(f"  hash match:        {corpus_hash == EXPECTED_CORPUS_HASH}")

    # ------------------------------------------------------------
    # STEP 2 — canonical-vs-corpus Env0 forensic comparison
    # ------------------------------------------------------------

    print()
    print("[2/6] Capturing canonical Env0...")

    canonical_meta, canonical_body = (
        bridge.capture_v8_skeleton(VST3)
    )

    canonical_env = env_snapshot(canonical_body)
    corpus_env = env_snapshot(corpus_body)
    comparison = compare_envs(
        canonical_env,
        corpus_env,
    )

    print()
    print("CANONICAL Env0")
    print("-" * 80)
    print(json.dumps(canonical_env, indent=2))

    print()
    print("CORPUS Env0")
    print("-" * 80)
    print(json.dumps(corpus_env, indent=2))

    print()
    print("FIELD COMPARISON")
    print("-" * 80)
    print(json.dumps(comparison, indent=2))

    baseline_release = (
        corpus_body
        .get("Env0", {})
        .get("plainParams", {})
        .get("kParamRelease")
    )

    # ------------------------------------------------------------
    # STEP 3 — define exact diagnostic comparisons
    # ------------------------------------------------------------

    print()
    print("[3/6] Defining diagnostic comparisons...")

    # A vs B:
    # Corpus baseline versus Sustain=0.3, with shared Decay=0.02.
    sustain_spec = make_spec(
        experiment_id=(
            "16.5.43.1-CORPUS-ENV-SUSTAIN-DIAGNOSTIC"
        ),
        mutation_path="Env0.plainParams.kParamSustain",
        mutation_value=0.3,
        mutation_note=(
            "Diagnostic Sustain=0.3 after corpus Env forensics"
        ),
        metric="sustain_window_rms_db",
        expected_direction="decrease",
        stimulus=Stimulus(
            note=60,
            velocity=110,
            note_len=1.8,
            render_seconds=2.0,
        ),
    )

    # A vs C:
    # Explicitly write Sustain=1.0.
    explicit_sustain_spec = make_spec(
        experiment_id=(
            "16.5.43.1-CORPUS-ENV-SUSTAIN-EXPLICIT-1.0"
        ),
        mutation_path="Env0.plainParams.kParamSustain",
        mutation_value=1.0,
        mutation_note=(
            "Diagnostic explicit Sustain=1.0"
        ),
        metric="sustain_window_rms_db",
        expected_direction="decrease",
        stimulus=Stimulus(
            note=60,
            velocity=110,
            note_len=1.8,
            render_seconds=2.0,
        ),
    )

    # A vs D:
    # Explicitly write the corpus's already-present Release value.
    release_baseline_spec = make_spec(
        experiment_id=(
            "16.5.43.1-CORPUS-ENV-RELEASE-BASELINE-WRITE"
        ),
        mutation_path="Env0.plainParams.kParamRelease",
        mutation_value=baseline_release,
        mutation_note=(
            "Diagnostic explicit write of existing corpus Release value"
        ),
        metric="tail_rms_db",
        expected_direction="increase",
        stimulus=Stimulus(
            note=60,
            velocity=110,
            note_len=0.4,
            render_seconds=2.0,
            tail_start=0.6,
        ),
    )

    # A vs E:
    # Release=1.0.
    release_1_spec = make_spec(
        experiment_id=(
            "16.5.43.1-CORPUS-ENV-RELEASE-1.0"
        ),
        mutation_path="Env0.plainParams.kParamRelease",
        mutation_value=1.0,
        mutation_note=(
            "Diagnostic Release=1.0"
        ),
        metric="tail_rms_db",
        expected_direction="increase",
        stimulus=Stimulus(
            note=60,
            velocity=110,
            note_len=0.4,
            render_seconds=2.0,
            tail_start=0.6,
        ),
    )

    # ------------------------------------------------------------
    # STEP 4 — run four actual harness comparisons
    # ------------------------------------------------------------

    print()
    print("[4/6] Running diagnostic A/B comparisons...")

    results = {}

    results["A_vs_B_sustain_0.3"] = run_diagnostic(
        label="A_vs_B_sustain_0.3",
        spec=sustain_spec,
        corpus_seed=(corpus_meta, corpus_body),
    )

    results["A_vs_C_sustain_1.0"] = run_diagnostic(
        label="A_vs_C_sustain_1.0",
        spec=explicit_sustain_spec,
        corpus_seed=(corpus_meta, corpus_body),
    )

    results["A_vs_D_release_baseline_write"] = run_diagnostic(
        label="A_vs_D_release_baseline_write",
        spec=release_baseline_spec,
        corpus_seed=(corpus_meta, corpus_body),
    )

    results["A_vs_E_release_1.0"] = run_diagnostic(
        label="A_vs_E_release_1.0",
        spec=release_1_spec,
        corpus_seed=(corpus_meta, corpus_body),
    )

    # ------------------------------------------------------------
    # STEP 5 — interpret only as forensic observations
    # ------------------------------------------------------------

    print()
    print("[5/6] Building forensic artifact...")

    artifact = {
        "experiment": "16.5.43.1",
        "name": "Corpus Env Forensics",
        "status": "COMPLETED",
        "classification": "DIAGNOSTIC_ONLY",
        "seed": {
            "source": "experiments/_corpus_cache.pkl bodies[4]",
            "normalization": (
                "corpus body + native processor component + "
                "native metadata"
            ),
            "state_hash": corpus_hash,
            "expected_state_hash": EXPECTED_CORPUS_HASH,
            "hash_match": True,
        },
        "canonical_env0": canonical_env,
        "corpus_env0": corpus_env,
        "field_comparison": comparison,
        "baseline_release_value": baseline_release,
        "diagnostic_design": {
            "A": "corpus baseline",
            "B": "Sustain=0.3 + Decay=0.02",
            "C": "explicit Sustain=1.0 + Decay=0.02",
            "D": (
                "explicit existing corpus Release value "
                "+ Decay=0.02"
            ),
            "E": "Release=1.0 + Decay=0.02",
        },
        "results": results,
        "guardrails": {
            "capability_promotion": False,
            "current_capability_view_update": False,
            "frontier_update": False,
            "diagnostic_only": True,
        },
    }

    OUT.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("[6/6] COMPLETE")
    print("=" * 80)
    print("16.5.43.1 FORENSICS COMPLETE")
    print("Artifact:", OUT)
    print("=" * 80)


if __name__ == "__main__":
    main()