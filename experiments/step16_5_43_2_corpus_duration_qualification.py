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
from serum2.evidence.record import EFFECT_OBSERVED, PASS
from serum2.evidence.spec import (
    ExperimentSpec,
    MeasurementPlan,
    Mutation,
    SINGLE_FIELD,
    Stimulus,
    TargetSpec,
    validate,
)


ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3

CACHE = ROOT / "experiments" / "_corpus_cache.pkl"
OUT = ROOT / "experiments" / "16_5_43_2_CORPUS_DURATION_QUALIFICATION.json"

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
        source="16.5.43.2.canonical",
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
        source="16.5.43.2.normalized_corpus",
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


def env0_snapshot(body: dict) -> dict:
    env0 = body.get("Env0")

    if not isinstance(env0, dict):
        return {
            "present": False,
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
        "keys": sorted(env0.keys()),
        "plainParams_present": "plainParams" in env0,
        "plainParams_keys": sorted(plain.keys()),
        "fields": fields,
    }


def serialize_record(rec) -> dict:
    return {
        "experiment_id": rec.experiment_id,
        "gates": rec.gate_completeness(),
        "runtime_verified": rec.runtime_verified(),
        "outcome_signature": rec.outcome_signature(),
        "state_observation": rec.state_observation,
        "load_observation": rec.load_observation,
        "render_observation": rec.render_observation,
        "persistence_observation": rec.persistence_observation,
        "structural_observation": rec.structural_observation,
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
        "evidence_record": rec.to_dict(),
    }


def make_release_clamp_probe() -> ExperimentSpec:
    """
    Structural-only Sustain ceiling probe.

    The probe deliberately asks for Sustain=1.0 and declares numeric-clamp
    semantics so that harness.structural_observation can recover a stored
    boundary when Serum canonicalizes/clamps the requested value.
    """

    spec = ExperimentSpec(
        experiment_id=(
            "16.5.43.2-CORPUS-SUSTAIN-CEILING-PROBE"
        ),
        mutations=[
            Mutation(
                "Env0.plainParams.kParamSustain",
                1.0,
                "16.5.43.2 structural Sustain ceiling probe",
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "shared short decay for context stabilization",
            )
        ],
        isolation_level=SINGLE_FIELD,
        claim_subject="structural_probe:Env.kParamSustain",
        claim_predicate="numeric_clamp_range",
        measurement_plans=[
            MeasurementPlan(
                metric="sustain_window_rms_db",
                target=TargetSpec(
                    "Env0.plainParams.kParamSustain",
                    "Env",
                    "kParamSustain",
                ),
                # The causal result is NOT used to qualify the structural
                # probe. We still need a normal measurement plan so the
                # existing harness executes both arms and captures state.
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
            "16.5.43.2 structural-only probe. "
            "Requested Sustain=1.0 to recover the maximum persisted "
            "value through harness structural_observation. "
            "Not a capability qualification experiment."
        ),
        probe_semantics="NUMERIC_CLAMP_RANGE",
    )

    return spec


def make_release_spec(sustain_context: float) -> ExperimentSpec:
    """
    Correct-context Env Release qualification.

    Only Release is experimental. Decay and Sustain define shared context.
    """

    return ExperimentSpec(
        experiment_id=(
            "16.5.43.2-CORPUS-ENV-RELEASE-CORRECTED"
        ),
        mutations=[
            Mutation(
                "Env0.plainParams.kParamRelease",
                1.0,
                "16.5.43.2 corrected-context long release",
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "shared short decay",
            ),
            Mutation(
                "Env0.plainParams.kParamSustain",
                sustain_context,
                "shared persisted Sustain context recovered by clamp probe",
            ),
        ],
        isolation_level=SINGLE_FIELD,
        claim_subject="envelope_field:Env.kParamRelease",
        claim_predicate="produces_measurable_effect",
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
                stimulus=Stimulus(
                    note=60,
                    velocity=110,
                    note_len=0.4,
                    render_seconds=2.0,
                    tail_start=0.6,
                ),
                kernel_artifact="tail_rms_db.py",
            )
        ],
        notes=(
            "Corrected normalized-corpus Release context. "
            f"Shared Sustain={sustain_context!r}; "
            "shared Decay=0.02s; only Release is mutated."
        ),
    )


def make_sustain_spec() -> ExperimentSpec:
    """
    Correct-context Sustain fallback.

    Unlike the historical canonical-context specification, the expected
    direction is increase because the normalized corpus baseline is at
    Sustain=0.0.
    """

    return ExperimentSpec(
        experiment_id=(
            "16.5.43.2-CORPUS-ENV-SUSTAIN-CORRECTED"
        ),
        mutations=[
            Mutation(
                "Env0.plainParams.kParamSustain",
                0.3,
                "16.5.43.2 corrected corpus Sustain fallback",
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "shared short decay",
            )
        ],
        isolation_level=SINGLE_FIELD,
        claim_subject="envelope_field:Env.kParamSustain",
        claim_predicate="produces_measurable_effect",
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
        notes=(
            "Corrected normalized-corpus Sustain fallback. "
            "Expected direction is increase because corpus Sustain "
            "baseline is 0.0. Shared Decay=0.02s."
        ),
    )


def extract_clamp_value(structural_observation: dict):
    """
    Search structurally for a harness-reported clamped_to value.

    We do not assume the exact nesting shape; the harness owns that shape.
    """

    found = []

    def walk(obj, path="root"):
        if isinstance(obj, dict):
            if "clamped_to" in obj:
                found.append(
                    (
                        path + ".clamped_to",
                        obj["clamped_to"],
                    )
                )

            for key, value in obj.items():
                walk(value, f"{path}.{key}")

        elif isinstance(obj, (list, tuple)):
            for idx, value in enumerate(obj):
                walk(value, f"{path}[{idx}]")

    walk(structural_observation)

    numeric = [
        (path, value)
        for path, value in found
        if isinstance(value, (int, float))
    ]

    if not numeric:
        return None

    # There should normally be one value for this single-field probe.
    # Preserve the first one and report all findings in the artifact.
    return numeric[0][1]


def run_experiment(label: str, spec: ExperimentSpec, seed):
    validate(spec)

    processor_state.require_processor_state(
        seed,
        source=f"16.5.43.2.{label}.run",
    )

    print()
    print("=" * 80)
    print(label)
    print("=" * 80)

    rec = harness.run(
        spec,
        skeleton=seed,
    )

    gates = rec.gate_completeness()

    print("gates:", gates)
    print("runtime_verified:", rec.runtime_verified())
    print(
        "matches_intent:",
        rec.state_observation.get("matches_intent"),
    )

    if rec.causal_measurements:
        for m in rec.causal_measurements:
            print(
                "causal:"
                f" metric={m.metric}"
                f" baseline={m.baseline:.6f}"
                f" treatment={m.treatment:.6f}"
                f" delta={m.delta:+.6f}"
                f" expected={m.expected_direction}"
                f" observed={m.observed_direction}"
                f" status={m.status}"
            )

    print(
        "persistence:",
        rec.persistence_observation.get("status"),
    )

    if rec.structural_observation:
        print(
            "structural_observation:",
            json.dumps(
                rec.structural_observation,
                indent=2,
                default=str,
            ),
        )

    return rec


def release_qualifies(rec) -> tuple[bool, list[str]]:
    failures = []

    gates = rec.gate_completeness()

    for gate in (
        "generation",
        "load",
        "render",
        "causal",
        "persistence",
    ):
        if gates.get(gate) != PASS:
            failures.append(
                f"{gate}={gates.get(gate)!r}, expected {PASS!r}"
            )

    if not rec.runtime_verified():
        failures.append("runtime_verified is false")

    if not rec.state_observation.get(
        "matches_intent",
        False,
    ):
        failures.append(
            "state_observation.matches_intent is false"
        )

    if not rec.causal_measurements:
        failures.append("no causal measurement")
    else:
        for m in rec.causal_measurements:
            if m.status != EFFECT_OBSERVED:
                failures.append(
                    f"causal status={m.status!r}"
                )

            if m.observed_direction != "increase":
                failures.append(
                    "observed_direction="
                    f"{m.observed_direction!r}, "
                    "expected 'increase'"
                )

            if m.delta == 0.0:
                failures.append(
                    "causal delta is exactly 0.0"
                )

            if m.delta < m.threshold:
                failures.append(
                    f"delta={m.delta!r} below threshold={m.threshold!r}"
                )

    qualified = not failures
    return qualified, failures


def sustain_qualifies(rec) -> tuple[bool, list[str]]:
    failures = []

    gates = rec.gate_completeness()

    for gate in (
        "generation",
        "load",
        "render",
        "causal",
        "persistence",
    ):
        if gates.get(gate) != PASS:
            failures.append(
                f"{gate}={gates.get(gate)!r}, expected {PASS!r}"
            )

    if not rec.runtime_verified():
        failures.append("runtime_verified is false")

    if not rec.state_observation.get(
        "matches_intent",
        False,
    ):
        failures.append(
            "state_observation.matches_intent is false"
        )

    if not rec.causal_measurements:
        failures.append("no causal measurement")
    else:
        for m in rec.causal_measurements:
            if m.status != EFFECT_OBSERVED:
                failures.append(
                    f"causal status={m.status!r}"
                )

            if m.observed_direction != "increase":
                failures.append(
                    "observed_direction="
                    f"{m.observed_direction!r}, "
                    "expected 'increase'"
                )

            if m.delta == 0.0:
                failures.append(
                    "causal delta is exactly 0.0"
                )

            if m.delta < m.threshold:
                failures.append(
                    f"delta={m.delta!r} below threshold={m.threshold!r}"
                )

    qualified = not failures
    return qualified, failures


def main():
    print("=" * 80)
    print("16.5.43.2 — CONTEXT-CORRECT CORPUS DURATION QUALIFICATION")
    print("=" * 80)

    require_file(Path(VST3))

    # ------------------------------------------------------------
    # 1. Exact normalized corpus seed
    # ------------------------------------------------------------

    print()
    print("[1/5] Reconstructing normalized corpus seed...")

    corpus_seed = build_corpus_seed()
    corpus_meta, corpus_body, corpus_hash = corpus_seed

    print("  hash:", corpus_hash)
    print("  expected:", EXPECTED_CORPUS_HASH)
    print("  match:", corpus_hash == EXPECTED_CORPUS_HASH)

    if corpus_hash != EXPECTED_CORPUS_HASH:
        raise RuntimeError("normalized corpus seed hash mismatch")

    # ------------------------------------------------------------
    # 2. Structural Sustain ceiling probe FIRST
    # ------------------------------------------------------------

    print()
    print("[2/5] Running Sustain ceiling structural probe FIRST...")

    clamp_spec = make_release_clamp_probe()

    clamp_rec = run_experiment(
        "SUSTAIN_CEILING_PROBE",
        clamp_spec,
        (corpus_meta, corpus_body),
    )

    clamp_value = extract_clamp_value(
        clamp_rec.structural_observation
    )

    persistence_status = clamp_rec.persistence_observation.get(
        "status"
    )

    requested_sustain = 1.0

    print()
    print("=" * 80)
    print("SUSTAIN PROBE RAW FORENSIC OUTPUT")
    print("=" * 80)

    print()
    print("PERSISTENCE OBSERVATION:")
    print(
        json.dumps(
            clamp_rec.persistence_observation,
            indent=2,
            default=str,
        )
    )

    print()
    print("STRUCTURAL OBSERVATION:")
    print(
        json.dumps(
            clamp_rec.structural_observation,
            indent=2,
            default=str,
        )
    )

    print()
    print("STATE OBSERVATION:")
    print(
        json.dumps(
            clamp_rec.state_observation,
            indent=2,
            default=str,
        )
    )

    print()
    print("LOAD OBSERVATION:")
    print(
        json.dumps(
            clamp_rec.load_observation,
            indent=2,
            default=str,
        )
    )

    print()
    print("RAW RECORD KEYS:")
    print(
        json.dumps(
            list(clamp_rec.to_dict().keys()),
            indent=2,
            default=str,
        )
    )

    if clamp_value is not None:
        sustain_context = float(clamp_value)
        context_source = "harness.structural_observation.clamped_to"

    elif (
        isinstance(clamp_rec.persistence_observation, dict)
        and isinstance(
            clamp_rec.persistence_observation.get("stored_values"),
            dict,
        )
        and "Env0.plainParams.kParamSustain"
        in clamp_rec.persistence_observation["stored_values"]
    ):
        sustain_context = float(
            clamp_rec.persistence_observation["stored_values"][
                "Env0.plainParams.kParamSustain"
            ]
        )
        context_source = (
            "harness.persistence_observation.stored_values"
        )

    elif persistence_status == PASS:
        sustain_context = requested_sustain
        context_source = (
            "exact persistence of requested Sustain=1.0"
        )

    else:
        raise RuntimeError(
            "STOP: Sustain probe did not expose a usable persisted "
            "Sustain value. Raw forensic observations were printed above."
        )

    if sustain_context <= 0.0:
        raise RuntimeError(
            "STOP: recovered Sustain context is not > 0.0: "
            f"{sustain_context!r}"
        )

    print()
    print("  requested Sustain:", requested_sustain)
    print("  recovered context:", sustain_context)
    print("  context source:", context_source)

    # ------------------------------------------------------------
    # 3. Corrected Release qualification
    # ------------------------------------------------------------

    print()
    print("[3/5] Running corrected-context Env Release...")

    release_spec = make_release_spec(
        sustain_context,
    )

    release_rec = run_experiment(
        "CORRECTED_RELEASE",
        release_spec,
        (corpus_meta, corpus_body),
    )

    release_qualified, release_failures = release_qualifies(
        release_rec
    )

    print()
    print(
        "  RELEASE LOCAL QUALIFICATION:",
        "PASS" if release_qualified else "FAIL",
    )

    for failure in release_failures:
        print("   -", failure)

    # ------------------------------------------------------------
    # 4. Conditional Sustain fallback
    # ------------------------------------------------------------

    sustain_rec = None
    sustain_qualified = False
    sustain_failures = []
    sustain_ran = False

    if not release_qualified:
        print()
        print(
            "[4/5] Release did not qualify; "
            "running corrected Sustain fallback..."
        )

        sustain_spec = make_sustain_spec()

        sustain_rec = run_experiment(
            "CORRECTED_SUSTAIN_FALLBACK",
            sustain_spec,
            (corpus_meta, corpus_body),
        )

        sustain_qualified, sustain_failures = sustain_qualifies(
            sustain_rec
        )

        sustain_ran = True

        print()
        print(
            "  SUSTAIN LOCAL QUALIFICATION:",
            "PASS" if sustain_qualified else "FAIL",
        )

        for failure in sustain_failures:
            print("   -", failure)

    else:
        print()
        print(
            "[4/5] Release qualified; "
            "Sustain causal fallback is intentionally skipped."
        )

    # ------------------------------------------------------------
    # 5. Write one immutable experiment artifact
    # ------------------------------------------------------------

    print()
    print("[5/5] Writing qualification artifact...")

    duration_qualified = (
        release_qualified
        or sustain_qualified
    )

    result = {
        "step": "16.5.43.2",
        "name": "Context-Correct Corpus Duration Qualification",
        "status": (
            "PASS"
            if duration_qualified
            else "FAIL"
        ),
        "classification": (
            "EXPERIMENT_RESULT_ONLY"
        ),
        "context": "normalized_corpus",
        "seed": {
            "source": "experiments/_corpus_cache.pkl bodies[4]",
            "normalization": (
                "corpus body + native processor component "
                "+ native metadata"
            ),
            "state_hash": corpus_hash,
            "expected_state_hash": EXPECTED_CORPUS_HASH,
            "hash_match": True,
        },
        "forensic_basis": {
            "prior_experiment": (
                "16.5.43.1_CORPUS_ENV_FORENSICS.json"
            ),
            "prior_corpus_env0": {
                "Attack": 0.004875846483662035,
                "Decay": 3.1898578238230217,
                "Sustain": 0.0,
                "Release": 0.8837453206371405,
            },
            "old_release_negative_disposition": (
                "CONTEXT_INCOMPLETE"
            ),
            "reason": (
                "shared Decay override was unsuitable for the "
                "zero-Sustain corpus baseline"
            ),
        },
        "sustain_context_recovery": {
            "probe_experiment_id": clamp_rec.experiment_id,
            "requested_value": requested_sustain,
            "recovered_context_value": sustain_context,
            "source": context_source,
            "structural_observation":
                clamp_rec.structural_observation,
            "persistence": (
                clamp_rec.persistence_observation
            ),
            "record": serialize_record(clamp_rec),
        },
        "corrected_release": {
            "experiment_id": release_rec.experiment_id,
            "shared_context": {
                "Decay": 0.02,
                "Sustain": sustain_context,
            },
            "local_qualification": {
                "passed": release_qualified,
                "failures": release_failures,
            },
            "record": serialize_record(release_rec),
        },
        "corrected_sustain_fallback": (
            {
                "ran": True,
                "local_qualification": {
                    "passed": sustain_qualified,
                    "failures": sustain_failures,
                },
                "record": serialize_record(sustain_rec),
            }
            if sustain_ran
            else {
                "ran": False,
                "reason": (
                    "Release qualified; frozen ladder stops "
                    "after first qualifying duration control."
                ),
            }
        ),
        "final_local_duration_result": {
            "duration_control_qualified": duration_qualified,
            "qualifying_control": (
                "Env Release"
                if release_qualified
                else (
                    "Env Sustain"
                    if sustain_qualified
                    else None
                )
            ),
        },
        "guardrails": {
            "frontier_mutated": False,
            "current_capability_view_mutated": False,
            "capability_promoted_by_script": False,
            "historical_evidence_used_as_current_verification": False,
            "old_16_5_43_1_artifact_modified": False,
            "a_vs_d_used_as_causal_evidence": False,
            "structural_probe_used_as_causal_qualification": False,
        },
        "notes": (
            "Local experiment qualification is not equivalent to "
            "capability admission. Evidence must proceed through "
            "the normal EvidenceRecord -> ClaimGroup -> "
            "CapabilityContract -> context-scoped admission path."
        ),
    }

    OUT.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print(
        "16.5.43.2 RESULT:",
        "PASS" if duration_qualified else "FAIL",
    )
    print(
        "qualifying control:",
        (
            "Env Release"
            if release_qualified
            else (
                "Env Sustain"
                if sustain_qualified
                else "NONE"
            )
        ),
    )
    print("Artifact:", OUT)
    print("=" * 80)
    print("16.5.43.2 COMPLETE")


if __name__ == "__main__":
    main()