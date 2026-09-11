"""16.5.69.2-A3-16/17: Causal Behavior Harness

Sequence per target:
  1. Build baseline arm (no mutations, exercise context applied to body)
  2. Render baseline with exercise context (host params applied)
  3. Build mutated arm (apply mutations, exercise context applied to body)
  4. Render mutated with same exercise context (host params applied)
  5. Compute target-specific metric on each audio
  6. Compare metric values -> classify behavior

The exercise context ensures the signal path actually exercises the parameter.
It is applied identically to both arms — it is NOT a mutation.

The comparison uses an independently generated baseline (not reused from
generation or persistence steps). This is required for causal isolation.

Behavior observation is independent of P1/P2/P3 and restoration.
"""

from __future__ import annotations

from typing import Any, Optional, List, Tuple
import copy
import numpy as np

from serum2.qualification.a3_behavior_observation import (
    create_behavior_observation,
    BEHAVIOR_NOT_RUN,
    BehaviorObservation,
)

# Minimum delta to count as "observed effect" (per-metric defaults)
_DEFAULT_EFFECT_THRESHOLD_DB = 0.5    # dB for rms-based metrics
_DEFAULT_EFFECT_THRESHOLD_HZ = 100.0  # Hz for spectral centroid


def _rms_db(audio: np.ndarray) -> float:
    """RMS energy in dB. -120 dB floor for silence."""
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-10:
        return -120.0
    return float(20.0 * np.log10(rms))


def _spectral_centroid_hz(audio: np.ndarray, sr: int = 44100) -> float:
    """Spectral centroid in Hz, aggregated across channels."""
    from serum2.evidence.measure import spectral_centroid_hz
    return spectral_centroid_hz(audio)


def _compute_metric(audio: np.ndarray, metric_name: str) -> float:
    """Compute the named metric on audio."""
    if metric_name == "overall_rms_db":
        return _rms_db(audio)
    elif metric_name == "spectral_centroid_hz":
        return _spectral_centroid_hz(audio)
    else:
        raise ValueError("Unknown metric: {}".format(metric_name))


def _classify(
    baseline_val: float,
    mutated_val: float,
    expected_direction: Optional[str],
    threshold: float,
) -> tuple[str, str]:
    """Return (status, observed_direction) from metric comparison."""
    delta = mutated_val - baseline_val
    abs_delta = abs(delta)

    if abs_delta < threshold:
        return "NO_OBSERVED_EFFECT", "none"

    observed_dir = "increase" if delta > 0 else "decrease"

    if expected_direction is None or expected_direction == "change":
        return "CAUSAL_VERIFIED", observed_dir

    if expected_direction == observed_dir:
        return "CAUSAL_VERIFIED", observed_dir

    return "WRONG_DIRECTION", observed_dir


def _apply_exercise_context(synth: Any, context: List[Tuple[str, float]]) -> None:
    """Apply exercise context host parameters to a loaded synth instance."""
    if not context:
        return
    params = synth.get_parameters_description()
    by_name = {p["name"]: p["index"] for p in params}
    for name, value in context:
        if name not in by_name:
            raise KeyError("Exercise context: host parameter not found: {!r}".format(name))
        synth.set_parameter(by_name[name], float(value))


def run_behavior_test(
    *,
    experiment_id: str,
    target_path: str,
    mutation_value: Any,
    skeleton: tuple,
    spec: Any,
    expected_direction: Optional[str] = "change",
    metric_name: str = "overall_rms_db",
    effect_threshold: float = None,
    exercise_context: List[Tuple[str, float]] = None,
    exercise_baseline_overrides: List[Tuple[str, Any]] = None,
    baseline_host_context: List[Tuple[str, float]] = None,
    mutated_host_context: List[Tuple[str, float]] = None,
) -> dict[str, Any]:
    """Render baseline and mutated arms; measure audio metric; classify.

    Args:
        exercise_context: list of (host_param_name, value) applied to BOTH arms.
        exercise_baseline_overrides: list of (body_path, value) applied to baseline
            arm body only.
        baseline_host_context: list of (host_param_name, value) applied to baseline
            arm ONLY — allows arm-specific host state (e.g. A Enable=0 baseline).
        mutated_host_context: list of (host_param_name, value) applied to mutated
            arm ONLY — allows arm-specific host state (e.g. A Enable=1 mutated).

    Returns dict that can be converted to BehaviorObservation.
    """
    if effect_threshold is None:
        if metric_name == "spectral_centroid_hz":
            effect_threshold = _DEFAULT_EFFECT_THRESHOLD_HZ
        else:
            effect_threshold = _DEFAULT_EFFECT_THRESHOLD_DB

    if exercise_context is None:
        exercise_context = []
    if exercise_baseline_overrides is None:
        exercise_baseline_overrides = []
    if baseline_host_context is None:
        baseline_host_context = []
    if mutated_host_context is None:
        mutated_host_context = []

    try:
        import os
        import tempfile
        import dawdreamer as daw
        from serum2.evidence.harness import build_arm
        from serum2.evidence import epoch as epoch_mod
        from serum2 import bridge as br, pathmerge

        VST3 = epoch_mod.SERUM_VST3
        SR = 44100
        BLOCK = 512

        st = getattr(spec, "stimulus", None)
        if st is None:
            from serum2.evidence.spec import Stimulus
            st = Stimulus(note=60, velocity=100, note_len=1.5, render_seconds=2.0)

        def render_with_context(meta, body, arm_host_context, is_baseline=False):
            """Write state, load, apply exercise + arm-specific context, render."""
            if is_baseline and exercise_baseline_overrides:
                body = copy.deepcopy(body)
                for path, val in exercise_baseline_overrides:
                    pathmerge.apply_path_value(body, path, val)

            fd, tmp = tempfile.mkstemp(suffix=".bin")
            os.close(fd)
            br.write_state_file(tmp, meta, body)
            engine = daw.RenderEngine(SR, BLOCK)
            synth = engine.make_plugin_processor("serum", VST3)
            try:
                synth.load_state(tmp)
            except Exception as e:
                os.remove(tmp)
                raise RuntimeError("Serum load_state failed: {}".format(e))
            os.remove(tmp)

            # Apply shared context first, then arm-specific context
            _apply_exercise_context(synth, exercise_context)
            _apply_exercise_context(synth, arm_host_context)

            synth.clear_midi()
            synth.add_midi_note(st.note, st.velocity, 0.0, st.note_len)
            engine.load_graph([(synth, [])])
            engine.render(st.render_seconds)
            return np.asarray(engine.get_audio())

        # Baseline arm
        meta_c, body_c = build_arm(skeleton, spec, apply_mutations=False)
        audio_c = render_with_context(meta_c, body_c, baseline_host_context, is_baseline=True)

        # Mutated arm
        meta_t, body_t = build_arm(skeleton, spec, apply_mutations=True)
        audio_t = render_with_context(meta_t, body_t, mutated_host_context, is_baseline=False)

        # Compute metric
        baseline_metric = _compute_metric(audio_c, metric_name)
        mutated_metric = _compute_metric(audio_t, metric_name)

        status, observed_dir = _classify(
            baseline_metric, mutated_metric, expected_direction, effect_threshold
        )

        return {
            "status": status,
            "reason": _reason(status, baseline_metric, mutated_metric,
                              expected_direction, observed_dir, metric_name),
            "baseline_metric": baseline_metric,
            "mutated_metric": mutated_metric,
            "metric_name": metric_name,
            "expected_direction": expected_direction,
            "observed_direction": observed_dir,
            "baseline_rendered": True,
            "mutated_rendered": True,
            "delta": mutated_metric - baseline_metric,
            "experiment_id": experiment_id,
            "target_path": target_path,
        }

    except Exception as e:
        import traceback
        return {
            "status": "UNKNOWN",
            "reason": "Behavior lifecycle error: {}".format(str(e)),
            "baseline_rendered": False,
            "mutated_rendered": False,
            "error_traceback": traceback.format_exc(),
        }


def _reason(status, baseline, mutated, expected, observed, metric):
    unit = "dB" if "rms" in metric else "Hz"
    delta = mutated - baseline
    if status == "CAUSAL_VERIFIED":
        return "Effect: baseline={:.1f} {}, mutated={:.1f} {} (delta={:+.1f} {}, dir={})".format(
            baseline, unit, mutated, unit, delta, unit, observed
        )
    if status == "NO_OBSERVED_EFFECT":
        return "No effect: baseline={:.1f} {}, mutated={:.1f} {} (|delta|<threshold)".format(
            baseline, unit, mutated, unit
        )
    if status == "WRONG_DIRECTION":
        return "Wrong direction: expected={}, observed={}, delta={:+.1f} {}".format(
            expected, observed, delta, unit
        )
    return "status={}, baseline={:.1f} {}, mutated={:.1f} {}".format(
        status, baseline, unit, mutated, unit
    )


def qualify_with_behavior(
    *,
    experiment_id: str,
    resolved_target: dict[str, Any],
    spec: Any,
    skeleton: tuple,
    expected_direction: Optional[str] = "change",
    metric_name: str = "overall_rms_db",
    effect_threshold: float = None,
    exercise_context: List[Tuple[str, float]] = None,
    exercise_baseline_overrides: List[Tuple[str, Any]] = None,
    baseline_host_context: List[Tuple[str, float]] = None,
    mutated_host_context: List[Tuple[str, float]] = None,
) -> dict[str, Any]:
    """Run causal behavior qualification on the specification."""

    if not spec.mutations:
        return {
            "experiment_id": experiment_id,
            "error": "No mutations in spec",
            "behavior_observation": BEHAVIOR_NOT_RUN,
        }

    mutation = spec.mutations[0]
    target_path = mutation.target_path

    result_dict = run_behavior_test(
        experiment_id=experiment_id,
        target_path=target_path,
        mutation_value=mutation.value,
        skeleton=skeleton,
        spec=spec,
        expected_direction=expected_direction,
        metric_name=metric_name,
        effect_threshold=effect_threshold,
        exercise_context=exercise_context,
        exercise_baseline_overrides=exercise_baseline_overrides,
        baseline_host_context=baseline_host_context,
        mutated_host_context=mutated_host_context,
    )

    behavior_obs = create_behavior_observation(
        status=result_dict.get("status", "UNKNOWN"),
        reason=result_dict.get("reason"),
        baseline_metric=result_dict.get("baseline_metric"),
        mutated_metric=result_dict.get("mutated_metric"),
        metric_name=result_dict.get("metric_name"),
        expected_direction=result_dict.get("expected_direction"),
        observed_direction=result_dict.get("observed_direction"),
        baseline_rendered=result_dict.get("baseline_rendered", False),
        mutated_rendered=result_dict.get("mutated_rendered", False),
        details={k: v for k, v in result_dict.items()
                 if k not in ["status", "reason", "baseline_metric", "mutated_metric",
                              "metric_name", "expected_direction", "observed_direction",
                              "baseline_rendered", "mutated_rendered"]},
    )

    return {
        "experiment_id": experiment_id,
        "target_semantic_id": resolved_target.get("semantic_id"),
        "target_path": target_path,
        "behavior_observation": behavior_obs,
        "result_dict": result_dict,
    }
