"""
16.5.43 — Corpus Sustain Fallback

Purpose
-------
Fallback qualification for the normalized corpus context after
Env Release produced NO_OBSERVED_EFFECT.

From the frozen plan (16.5.43 gate specification):
    "When Release is unobserved, test Env Sustain as the fallback."

The canonical native context already passed Env Release
(baseline -47.941438 dB, treatment -47.941438 dB expected, actually observed).
Do not rerun it.

This script tests ONLY:
    normalized corpus + Env Sustain

Seed Context
------------
normalized_corpus (hash: 220cf7ee652d5c4e)
    bodies[4] from _corpus_cache.pkl
    + native processor component
    + native metadata

Experiment Definition
---------------------
Source: experiments/step15_2_1_sustain.py (exact historical specification)

Mutation:
    Env0.plainParams.kParamSustain = 0.3

Shared baseline override:
    Env0.plainParams.kParamDecay = 0.02

Isolation:
    SINGLE_FIELD

Metric:
    sustain_window_rms_db

Direction:
    decrease (implicit default Sustain=1.0 down to treatment 0.3)

Threshold:
    3.0

Stimulus:
    note=60
    velocity=110
    note_len=1.8
    render_seconds=2.0

Kernel:
    sustain_window_rms_db.py

Qualification Gate
------------------
PASS requires:
    - generation PASS
    - load PASS
    - render PASS
    - runtime_verified: True
    - state_observation.matches_intent: True
    - causal.status: EFFECT_OBSERVED
    - causal.observed_direction: decrease
    - persistence PASS

FAIL CLOSED:
    If any gate fails, print "16.5.43 CORPUS SUSTAIN FALLBACK FAIL"
    Do not promote Sustain to CurrentCapabilityView.
    Do not invent another duration control.
    Do not change the 16.5.43 PASS/FAIL result.
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


ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3
CORPUS_CACHE = ROOT / "experiments" / "_corpus_cache.pkl"
OUT = ROOT / "experiments" / "16_5_43_CORPUS_SUSTAIN_FALLBACK.json"

EXPECTED_CORPUS_HASH = "220cf7ee652d5c4e"


def require_file(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"required file missing: {path}")


def build_corpus_seed():
    """
    Reconstruct the normalized corpus seed exactly as 16.5.42 does:
        _corpus_cache.pkl bodies[4]
        + native processor component
        + native metadata
    """

    native_meta, native_body = bridge.capture_v8_skeleton(VST3)

    processor_state.require_processor_state(
        (native_meta, native_body),
        source="16.5.43_corpus_sustain.canonical",
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
        source="16.5.43_corpus_sustain.normalized_corpus",
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

    return (corpus_meta, corpus_body)


def make_sustain_spec() -> ExperimentSpec:
    """
    Exact definition recovered from:
        experiments/step15_2_1_sustain.py
    """

    return ExperimentSpec(
        experiment_id="16.5.43-normalized_corpus-ENV-SUSTAIN-FALLBACK",
        mutations=[
            Mutation(
                "Env0.plainParams.kParamSustain",
                0.3,
                "16.5.43 corpus fallback: sustain after Release NO_OBSERVED_EFFECT",
            )
        ],
        prerequisites=[],
        baseline_overrides=[
            Mutation(
                "Env0.plainParams.kParamDecay",
                0.02,
                "shared: short decay so we're in sustain phase by 0.9s",
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
                expected_direction="decrease",
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
            "Exact 15.2.1 specification on normalized corpus seed. "
            "Fallback after corpus Release NO_OBSERVED_EFFECT. "
            "Control: implicit default Sustain=1.0. "
            "Treatment: Sustain=0.3. "
            "Both arms use Decay=0.02s."
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


def main():
    print("=" * 80)
    print("16.5.43 — CORPUS SUSTAIN FALLBACK")
    print("=" * 80)
    print()

    if not Path(VST3).exists():
        raise RuntimeError(f"Serum VST3 not found: {VST3}")

    print("[1/3] Reconstructing normalized corpus seed...")

    corpus_seed = build_corpus_seed()

    corpus_hash = bridge.state_hash(*corpus_seed)

    print(f"  corpus state hash: {corpus_hash}")
    print(f"  matches expected : {corpus_hash == EXPECTED_CORPUS_HASH}")

    print()

    print("[2/3] Running Env Sustain experiment on corpus...")

    spec = make_sustain_spec()

    validate(spec)

    processor_state.require_processor_state(
        corpus_seed,
        source="16.5.43_corpus_sustain.run",
    )

    print("  executing harness.run(spec, skeleton=corpus_seed)")

    rec = harness.run(spec, skeleton=corpus_seed)

    gates = rec.gate_completeness()
    runtime_verified = rec.runtime_verified()
    matches_intent = rec.state_observation.get("matches_intent", False)

    print("  gates:", gates)
    print("  runtime_verified:", runtime_verified)
    print("  matches_intent:", matches_intent)

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

        print("  measurement_definition_id:", m.measurement_definition_id)

    print("  persistence:", rec.persistence_observation.get("status"))

    print()

    print("[3/3] Qualification gate...")

    failures = []

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

    if not runtime_verified:
        failures.append("runtime_verified is false")

    if not matches_intent:
        failures.append("state_observation.matches_intent is false")

    if not rec.causal_measurements:
        failures.append("no causal measurement")
    else:
        for m in rec.causal_measurements:
            if m.status != EFFECT_OBSERVED:
                failures.append(f"causal status={m.status!r}")
            if m.observed_direction != "decrease":
                failures.append(
                    f"observed_direction={m.observed_direction!r}, "
                    f"expected 'decrease'"
                )

    qualified = len(failures) == 0

    if qualified:
        print("  CURRENT QUALIFICATION: PASS")
    else:
        print("  CURRENT QUALIFICATION: FAIL")
        for failure in failures:
            print("   -", failure)

    print()

    result = {
        "step": "16.5.43",
        "phase": "CORPUS_SUSTAIN_FALLBACK",
        "status": "PASS" if qualified else "FAIL",
        "purpose": (
            "Fallback qualification for normalized corpus context "
            "after Env Release NO_OBSERVED_EFFECT"
        ),
        "context": "normalized_corpus",
        "seed_hash": corpus_hash,
        "expected_seed_hash": EXPECTED_CORPUS_HASH,
        "seed_hash_matches": corpus_hash == EXPECTED_CORPUS_HASH,
        "environment": {
            "serum_vst3": VST3,
            "sample_rate": 44100,
            "block_size": 512,
        },
        "experiment": {
            "id": rec.experiment_id,
            "capability": "Env Sustain",
            "source": "experiments/step15_2_1_sustain.py",
            "mutation": "Env0.plainParams.kParamSustain = 0.3",
            "baseline_override": "Env0.plainParams.kParamDecay = 0.02",
            "isolation_level": "SINGLE_FIELD",
            "metric": "sustain_window_rms_db",
            "direction": "decrease",
            "threshold": 3.0,
        },
        "qualification": {
            "gates": gates,
            "runtime_verified": runtime_verified,
            "matches_intent": matches_intent,
            "causal_measurement": (
                {
                    "baseline": m.baseline,
                    "treatment": m.treatment,
                    "delta": m.delta,
                    "observed_direction": m.observed_direction,
                    "status": m.status,
                }
                if rec.causal_measurements
                else None
            ),
            "persistence": rec.persistence_observation.get("status"),
        },
        "failures": failures,
        "record": serialize_record(rec),
        "rationale": (
            "16.5.43 gate (frozen plan): "
            "normalized corpus Env Release produced NO_OBSERVED_EFFECT. "
            "Fallback tests Env Sustain using exact 15.2.1 historical spec. "
            "Sustain qualifies only if all gates pass (EFFECT_OBSERVED, "
            "decrease direction, persistence PASS). "
            "If this fails, do not promote any other duration control."
        ),
    }

    OUT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print("=" * 80)

    if qualified:
        print("16.5.43 CORPUS SUSTAIN FALLBACK PASS")
    else:
        print("16.5.43 CORPUS SUSTAIN FALLBACK FAIL")

    print("=" * 80)
    print("Artifact:", OUT)


if __name__ == "__main__":
    main()
