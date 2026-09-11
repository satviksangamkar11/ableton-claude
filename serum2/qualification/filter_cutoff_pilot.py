"""Filter1.Cutoff Behavioral Qualification Pilot

One complete, auditable behavioral qualification for Filter1.Cutoff.

Chain:
  target (Filter.Cutoff)
  -> frozen exercise context (Filter 1 On=1.0)
  -> ExperimentSpec (SINGLE_FIELD, mutation: kParamFreq=0.9)
  -> baseline render (default CBOR state + Filter 1 On=1.0)
  -> treatment render (kParamFreq=0.9 + Filter 1 On=1.0)
  -> spectral centroid measurement
  -> ExerciseQualification binding
  -> is_valid gate

Why spectral centroid:
  Filter cutoff controls which frequencies pass through.
  Setting cutoff to 0.9 (near max) passes more high-frequency content.
  This raises the spectral centroid. Expected direction: increase.

Why frozen_context = {"Filter 1 On": 1.0}:
  By default in Serum, the filter may be inactive (Filter 1 On = 0.0).
  If the filter is off, mutating kParamFreq has no audible effect.
  The exercise context explicitly activates it for BOTH arms, making the
  filter frequency control exercisable.

Acceptance criteria:
  1. Context explicitly recorded in ExerciseQualification.frozen_context
  2. baseline_rendered = True, mutated_rendered = True
  3. causal_measurement.status == EFFECT_OBSERVED
  4. delta is observable (spectral centroid shifts measurably)
  5. SINGLE_FIELD isolation (only kParamFreq changed between arms)
  6. is_valid = True
"""

from __future__ import annotations

import json
import os
import datetime

from serum2 import bridge
from serum2.evidence import epoch as epoch_mod
from serum2.evidence.spec import ExperimentSpec, Mutation, SINGLE_FIELD
from serum2.qualification.a3_behavior_harness import run_behavior_test
from serum2.evidence.exercise_qualification import make_exercise_qualification

# ---------------------------------------------------------------------------
# Target definition
# ---------------------------------------------------------------------------

TARGET_SEMANTIC_ID = "Filter.Cutoff"
TARGET_CBOR_PATH = "VoiceFilter0.plainParams.kParamFreq"
EXPERIMENT_ID = "filter_cutoff_pilot_001"

# Treatment value: push cutoff high (0.9) so more highs pass through.
# Baseline: Serum default (filter at its default position in CBOR body).
MUTATION_VALUE = 0.9

# Exercise context: both arms must have the filter active.
# Without this, kParamFreq mutation has no audible effect.
FROZEN_CONTEXT = {"Filter 1 On": 1.0}

# Measurement
METRIC = "spectral_centroid_hz"
EXPECTED_DIRECTION = "increase"   # more highs → centroid shifts upward
EFFECT_THRESHOLD_HZ = 200.0       # Hz — conservative; large shift expected


# ---------------------------------------------------------------------------
# Pilot runner
# ---------------------------------------------------------------------------

def build_pilot_spec() -> ExperimentSpec:
    """Build the single-field ExperimentSpec for Filter1.Cutoff."""
    return ExperimentSpec(
        experiment_id=EXPERIMENT_ID,
        mutations=[
            Mutation(
                target_path=TARGET_CBOR_PATH,
                value=MUTATION_VALUE,
                provenance="filter_cutoff_pilot",
            )
        ],
        prerequisites=[],
        isolation_level=SINGLE_FIELD,
        claim_subject=TARGET_SEMANTIC_ID,
        claim_predicate="causal_behavior",
    )


def run_filter_cutoff_pilot(verbose: bool = True) -> dict:
    """Execute the complete Filter1.Cutoff behavioral qualification chain.

    Returns a result dict containing:
      - exercise_qualification: ExerciseQualification instance
      - behavior_result: raw output from run_behavior_test
      - chain_valid: True only when all acceptance criteria pass
      - acceptance: dict mapping each criterion to bool
    """
    if verbose:
        print("\n" + "=" * 70)
        print("FILTER1.CUTOFF BEHAVIORAL QUALIFICATION PILOT")
        print("=" * 70)
        print()
        print("target:         {}".format(TARGET_SEMANTIC_ID))
        print("cbor_path:      {}".format(TARGET_CBOR_PATH))
        print("mutation_value: {}".format(MUTATION_VALUE))
        print("frozen_context: {}".format(FROZEN_CONTEXT))
        print("metric:         {}".format(METRIC))
        print("expected_dir:   {}".format(EXPECTED_DIRECTION))
        print("threshold:      {} Hz".format(EFFECT_THRESHOLD_HZ))
        print()

    # 1. Load Serum skeleton (capture fresh CBOR body)
    if verbose:
        print("Step 1: Capturing VST3 skeleton ...")
    skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
    if verbose:
        print("  skeleton captured.")

    # 2. Build ExperimentSpec
    spec = build_pilot_spec()
    if verbose:
        print("Step 2: ExperimentSpec built.")
        print("  isolation_level: {}".format(spec.isolation_level))
        print("  mutations: {}".format([(m.target_path, m.value) for m in spec.mutations]))

    # 3. Run two-arm render with exercise context
    if verbose:
        print("Step 3: Running two-arm render ...")
        print("  exercise_context applied to BOTH arms: {}".format(
            list(FROZEN_CONTEXT.items())))

    behavior_result = run_behavior_test(
        experiment_id=EXPERIMENT_ID,
        target_path=TARGET_CBOR_PATH,
        mutation_value=MUTATION_VALUE,
        skeleton=skeleton,
        spec=spec,
        expected_direction=EXPECTED_DIRECTION,
        metric_name=METRIC,
        effect_threshold=EFFECT_THRESHOLD_HZ,
        exercise_context=list(FROZEN_CONTEXT.items()),
    )

    if verbose:
        status = behavior_result.get("status", "UNKNOWN")
        baseline = behavior_result.get("baseline_metric")
        mutated = behavior_result.get("mutated_metric")
        print("  baseline_rendered: {}".format(behavior_result.get("baseline_rendered")))
        print("  mutated_rendered:  {}".format(behavior_result.get("mutated_rendered")))
        print("  status:            {}".format(status))
        if baseline is not None and mutated is not None:
            delta = mutated - baseline
            print("  baseline_centroid: {:.1f} Hz".format(baseline))
            print("  mutated_centroid:  {:.1f} Hz".format(mutated))
            print("  delta:             {:+.1f} Hz".format(delta))
        if behavior_result.get("reason"):
            print("  reason: {}".format(behavior_result["reason"]))
        if behavior_result.get("error_traceback"):
            print("  ERROR TRACEBACK:")
            print(behavior_result["error_traceback"])

    # 4. Build ExerciseQualification binding
    if verbose:
        print("Step 4: Building ExerciseQualification binding ...")

    eq = make_exercise_qualification(
        target_semantic_id=TARGET_SEMANTIC_ID,
        target_cbor_path=TARGET_CBOR_PATH,
        frozen_context=FROZEN_CONTEXT,
        mutation_value=MUTATION_VALUE,
        experiment_id=EXPERIMENT_ID,
        behavior_result=behavior_result,
    )

    if verbose:
        print("  is_valid:              {}".format(eq.is_valid))
        print("  scope:                 {}".format(eq.scope))
        print("  isolation_level:       {}".format(eq.isolation_level))
        print("  causal_measurement:    status={}".format(eq.causal_measurement.status))

    # 5. Evaluate acceptance criteria
    acceptance = {
        "context_recorded": bool(eq.frozen_context),
        "baseline_rendered": bool(behavior_result.get("baseline_rendered")),
        "mutated_rendered": bool(behavior_result.get("mutated_rendered")),
        "single_field_isolation": eq.isolation_level == SINGLE_FIELD,
        "effect_observed": eq.causal_measurement.status == "EFFECT_OBSERVED",
        "exercise_qualification_valid": eq.is_valid,
    }
    chain_valid = all(acceptance.values())

    if verbose:
        print()
        print("Acceptance criteria:")
        for k, v in acceptance.items():
            mark = "PASS" if v else "FAIL"
            print("  [{}] {}".format(mark, k))
        print()
        print("chain_valid: {}".format(chain_valid))

    return {
        "exercise_qualification": eq,
        "behavior_result": behavior_result,
        "acceptance": acceptance,
        "chain_valid": chain_valid,
    }


def save_pilot_evidence(result: dict, out_path: str = None) -> str:
    """Serialize pilot result to JSON. Returns the output path."""
    if out_path is None:
        out_path = os.path.join(
            os.path.dirname(__file__),
            "A_FILTER_CUTOFF_PILOT_EVIDENCE.json",
        )
    eq = result["exercise_qualification"]
    br = result["behavior_result"]
    payload = {
        "pilot": "Filter1.Cutoff Behavioral Qualification",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "chain_valid": result["chain_valid"],
        "acceptance": result["acceptance"],
        "exercise_qualification": eq.to_dict(),
        "behavior_result_raw": {
            k: v for k, v in br.items()
            if k not in ("error_traceback",)
        },
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return out_path


if __name__ == "__main__":
    result = run_filter_cutoff_pilot(verbose=True)
    if result["chain_valid"]:
        path = save_pilot_evidence(result)
        print("\nEvidence saved to: {}".format(path))
    else:
        print("\nChain invalid — evidence NOT saved. Fix failing acceptance criteria.")
        for k, v in result["acceptance"].items():
            if not v:
                print("  FAIL: {}".format(k))
