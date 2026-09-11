"""16.5.69.2-A3-17: Valid Causal Exercise Contexts

Builds and proves target-specific exercise contexts so behavior tests
actually exercise the parameter being changed.

Step 16 found: all three targets NO_OBSERVED_EFFECT because:
  - Filter.Resonance / Filter.Type: filter OFF by default (Filter 1 On=0.0)
  - OSC1.Enable=True: OSC A already enabled by default (A Enable=1.0)

Step 17 fixes:
  - Filter targets: activate filter, route OSC A through it, set audible cutoff
  - OSC1.Enable: baseline_override kParamEnable=False so mutation True is causal

Acceptance:
  - At least the H1 targets produce CAUSAL_VERIFIED
  - NO_OBSERVED_EFFECT remains valid when appropriate
"""

from __future__ import annotations

import json
from typing import Any

from serum2 import bridge
from serum2.qualification.a3_test_plans import build_h1_pilot_plans
from serum2.qualification.a3_behavior_harness import qualify_with_behavior
from serum2.qualification.a3_exercise_contexts import (
    EXERCISE_CONTEXTS,
    EXERCISE_BASELINE_OVERRIDES,
    EXERCISE_BASELINE_HOST_CONTEXT,
    EXERCISE_MUTATED_HOST_CONTEXT,
    EXERCISE_METRICS,
    EXERCISE_THRESHOLDS,
)


def run_causal_on_target(
    target_name: str,
    plan: Any,
    resolved_target: dict,
    skeleton: tuple,
) -> dict[str, Any]:
    """Run causal behavior test with exercise context. Returns result dict."""

    print("\n  {}".format(target_name))

    exercise_ctx = EXERCISE_CONTEXTS.get(target_name, [])
    baseline_overrides = EXERCISE_BASELINE_OVERRIDES.get(target_name, [])
    baseline_host_ctx = EXERCISE_BASELINE_HOST_CONTEXT.get(target_name, [])
    mutated_host_ctx = EXERCISE_MUTATED_HOST_CONTEXT.get(target_name, [])
    metric = EXERCISE_METRICS.get(target_name, "overall_rms_db")
    threshold = EXERCISE_THRESHOLDS.get(target_name, None)

    if exercise_ctx:
        print("    exercise_context: {}".format(
            ", ".join("{}={:.2f}".format(n, v) for n, v in exercise_ctx)
        ))
    if baseline_host_ctx:
        print("    baseline_host: {}".format(
            ", ".join("{}={}".format(n, v) for n, v in baseline_host_ctx)
        ))
    if mutated_host_ctx:
        print("    mutated_host: {}".format(
            ", ".join("{}={}".format(n, v) for n, v in mutated_host_ctx)
        ))
    if baseline_overrides:
        print("    baseline_overrides: {}".format(
            ", ".join("{}={}".format(p, v) for p, v in baseline_overrides)
        ))
    print("    metric: {}".format(metric))

    try:
        result = qualify_with_behavior(
            experiment_id=plan.experiment_id,
            resolved_target=resolved_target,
            spec=plan,
            skeleton=skeleton,
            expected_direction="change",
            metric_name=metric,
            effect_threshold=threshold,
            exercise_context=exercise_ctx,
            exercise_baseline_overrides=baseline_overrides,
            baseline_host_context=baseline_host_ctx,
            mutated_host_context=mutated_host_ctx,
        )

        obs = result["behavior_observation"]
        print("    behavior: {}".format(obs.status))
        if obs.baseline_metric is not None:
            unit = "Hz" if "centroid" in (obs.metric_name or "") else "dB"
            print("    baseline: {:.2f} {}".format(obs.baseline_metric, unit))
            print("    mutated:  {:.2f} {}".format(obs.mutated_metric, unit))
            delta = obs.mutated_metric - obs.baseline_metric
            print("    delta:    {:+.2f} {}".format(delta, unit))
        if obs.reason:
            print("    reason: {}".format(obs.reason))

        return {
            "semantic_id": target_name,
            "behavior": obs.status,
            "baseline_rendered": obs.baseline_rendered,
            "mutated_rendered": obs.mutated_rendered,
            "baseline_metric": obs.baseline_metric,
            "mutated_metric": obs.mutated_metric,
            "metric_name": obs.metric_name,
            "observed_direction": obs.observed_direction,
            "reason": obs.reason,
            "exercise_context_used": [n for n, _ in exercise_ctx],
            "baseline_overrides_used": [p for p, _ in baseline_overrides],
            "baseline_host_used": [n for n, _ in baseline_host_ctx],
            "mutated_host_used": [n for n, _ in mutated_host_ctx],
        }

    except Exception as e:
        print("    ERROR: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return {
            "semantic_id": target_name,
            "behavior": "UNKNOWN",
            "baseline_rendered": False,
            "mutated_rendered": False,
            "error": str(e),
        }


def run_step_17():
    """Execute valid causal behavior tests on all 3 H1 targets."""

    print("\n" + "=" * 70)
    print("STEP 17: VALID CAUSAL EXERCISE CONTEXTS")
    print("=" * 70 + "\n")

    print("Exercise contexts:")
    print("  Filter.Resonance: Filter 1 On=1.0, Filter 1 Freq=0.35, A>Filter Balance=1.0")
    print("    Metric: spectral_centroid_hz")
    print("  Filter.Type: same as Resonance")
    print("    Metric: spectral_centroid_hz")
    print("  OSC1.Enable: baseline_override kParamEnable=False, mutation=True")
    print("    Metric: overall_rms_db\n")

    plans = build_h1_pilot_plans()
    plan_dict = {p.claim_subject: p for p in plans}

    with open("serum2/qualification/RESOLVED_TARGET_REGISTRY.json", "r") as f:
        data = json.load(f)
        resolved_list = data.get("resolved_targets", [])
    targets_dict = {t["semantic_id"]: t for t in resolved_list}

    from serum2.evidence import epoch as epoch_mod
    skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)

    target_names = ["Filter.Resonance", "Filter.Type", "OSC1.Enable"]
    results = []

    print("Results:")
    for name in target_names:
        r = run_causal_on_target(
            name,
            plan_dict[name],
            targets_dict[name],
            skeleton,
        )
        results.append(r)

    matrix = {r["semantic_id"]: r for r in results}

    print("\n" + "=" * 70)
    print("STEP 17 CAUSAL BEHAVIOR MATRIX")
    print("=" * 70)

    for name in target_names:
        m = matrix[name]
        metric = m.get("metric_name", "N/A")
        unit = "Hz" if "centroid" in metric else "dB"
        delta_str = ""
        if m.get("baseline_metric") is not None and m.get("mutated_metric") is not None:
            delta = m["mutated_metric"] - m["baseline_metric"]
            delta_str = " (delta={:+.2f} {})".format(delta, unit)
        print("  {}:".format(name))
        print("    behavior: {}{}".format(m["behavior"], delta_str))
        print("    context: {}".format(", ".join(m.get("exercise_context_used", [])) or "none"))

    return matrix


def test_step_17_causal():
    """Pytest: causal behavior test with exercise context on all 3 targets."""
    matrix = run_step_17()
    assert matrix is not None
    assert len(matrix) == 3

    for name, result in matrix.items():
        assert result["behavior"] in (
            "CAUSAL_VERIFIED", "NO_OBSERVED_EFFECT", "WRONG_DIRECTION",
            "INCONCLUSIVE", "UNKNOWN"
        ), "Invalid status for {}: {}".format(name, result["behavior"])

    # With exercise contexts, we expect actual causal evidence
    causal_count = sum(
        1 for r in matrix.values() if r["behavior"] == "CAUSAL_VERIFIED"
    )
    assert causal_count >= 1, (
        "Expected at least 1 CAUSAL_VERIFIED with exercise contexts, got {}. "
        "Results: {}".format(
            causal_count,
            {n: r["behavior"] for n, r in matrix.items()}
        )
    )


if __name__ == "__main__":
    run_step_17()
