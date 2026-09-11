"""16.5.69.2-A3-18: Generic qualification pipeline.

Dispatches over ControlCapability without any semantic-ID-specific branching.
All target-specific configuration lives in the capability definition.

Pipeline sequence per capability:
  1. Resolve adapter  -> build baseline and mutated body/host state
  2. Generation gate  -> verify mutation is isolated and correctly applied
  3. Behavior gate    -> measure audio metric, classify causality
  4. Return MutationReceipt

Adapters:
  cbor_body   -> pathmerge write to CBOR body dict
  host_param  -> set_parameter call, no body write
  cbor_string -> string field assignment in CBOR body dict

The behavior harness (a3_behavior_harness.py) remains the single render
implementation; this pipeline routes capability configuration into it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import copy

from serum2.qualification.a3_capability import ControlCapability
from serum2.qualification.a3_route import MutationRoute, BehaviorRoute
from serum2.qualification.a3_behavior_observation import BehaviorObservation, BEHAVIOR_NOT_RUN


# ---------------------------------------------------------------------------
# Receipt — one per pipeline execution
# ---------------------------------------------------------------------------

@dataclass
class MutationReceipt:
    semantic_id: str
    mutation_class: str
    adapter: str
    generation_status: str       # PASS | FAIL | NOT_RUN | SKIPPED
    behavior_status: str         # CAUSAL_VERIFIED | NO_OBSERVED_EFFECT | ... | SKIPPED
    behavior_observation: Optional[BehaviorObservation] = None
    generation_details: Optional[dict] = None
    error: Optional[str] = None

    @property
    def is_causal(self) -> bool:
        return self.behavior_status == "CAUSAL_VERIFIED"


# ---------------------------------------------------------------------------
# Adapter: apply mutation to baseline/mutated arms
# ---------------------------------------------------------------------------

def _apply_mutation_cbor_body(body: dict, path: str, value: Any) -> dict:
    from serum2 import pathmerge
    body = copy.deepcopy(body)
    pathmerge.apply_path_value(body, path, value)
    return body


def _apply_mutation_cbor_string(body: dict, path: str, value: str) -> dict:
    from serum2 import pathmerge
    body = copy.deepcopy(body)
    pathmerge.apply_path_value(body, path, value)
    return body


def _apply_mutation_host_param(
    host_param: str, value: float
) -> list[tuple[str, float]]:
    """Returns arm-specific host context list for a host-param mutation."""
    return [(host_param, value)]


# ---------------------------------------------------------------------------
# Generation gate: verify mutation is isolated (cbor_body and cbor_string only)
# ---------------------------------------------------------------------------

def _check_generation_gate(
    body_baseline: dict,
    body_mutated: dict,
    route: MutationRoute,
) -> dict:
    """Verify that the mutation changed exactly the declared path and nothing else.

    For host_param adapter: generation gate is NOT_RUN because no CBOR body
    change is expected or verifiable at state-build time.
    """
    if route.adapter == "host_param":
        return {
            "status": "NOT_RUN",
            "reason": "host_param adapter has no CBOR body to diff",
        }

    from serum2 import pathmerge

    path = route.path
    top_key = path.split(".")[0]

    diff_keys = sorted(
        k for k in body_mutated
        if body_mutated[k] != body_baseline.get(k)
    )
    intended_top = [top_key]
    top_ok = diff_keys == intended_top

    try:
        baseline_val = pathmerge.read_path_value(body_baseline, path)
        mutated_val = pathmerge.read_path_value(body_mutated, path)
        leaf_changed = baseline_val != mutated_val
    except Exception as e:
        return {
            "status": "FAIL",
            "reason": "Path read error: {}".format(e),
            "top_ok": top_ok,
            "diff_keys": diff_keys,
        }

    status = "PASS" if (top_ok and leaf_changed) else "FAIL"
    return {
        "status": status,
        "top_ok": top_ok,
        "leaf_changed": leaf_changed,
        "diff_keys": diff_keys,
        "intended_top": intended_top,
    }


# ---------------------------------------------------------------------------
# Behavior gate: run audio measurement via behavior harness
# ---------------------------------------------------------------------------

def _run_behavior_gate(
    *,
    capability: ControlCapability,
    baseline_value: Any,
    mutated_value: Any,
    body_baseline: dict,
    body_mutated: dict,
    skeleton: tuple,
    experiment_id: str,
    route: MutationRoute,
    behavior: BehaviorRoute,
) -> BehaviorObservation:
    """Route capability configuration into the behavior harness. No branching on semantic_id."""

    if not behavior.is_observable:
        from serum2.qualification.a3_behavior_observation import create_behavior_observation
        return create_behavior_observation(
            status="UNKNOWN",
            reason="Behavior route is NOT_OBSERVABLE for this capability class",
        )

    import os, tempfile, numpy as np
    import dawdreamer as daw
    from serum2 import bridge as br
    from serum2.evidence import epoch as epoch_mod

    VST3 = epoch_mod.SERUM_VST3
    SR = 44100
    BLOCK = 512

    def _apply_context(synth, context):
        if not context:
            return
        params = synth.get_parameters_description()
        by_name = {p["name"]: p["index"] for p in params}
        for name, val in context:
            if name not in by_name:
                raise KeyError("Exercise context: host param not found: {!r}".format(name))
            synth.set_parameter(by_name[name], float(val))

    def render_body(body, arm_host_ctx):
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        br.write_state_file(tmp, skeleton[0], body)
        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)
        try:
            synth.load_state(tmp)
        except Exception as e:
            os.remove(tmp)
            raise RuntimeError("load_state failed: {}".format(e))
        os.remove(tmp)
        _apply_context(synth, behavior.exercise_context)
        _apply_context(synth, arm_host_ctx)
        synth.clear_midi()
        synth.add_midi_note(60, 100, 0.0, 1.5)
        engine.load_graph([(synth, [])])
        engine.render(2.0)
        return np.asarray(engine.get_audio())

    try:
        audio_baseline = render_body(body_baseline, behavior.baseline_host_context)
        audio_mutated = render_body(body_mutated, behavior.mutated_host_context)

        from serum2.qualification.a3_behavior_harness import _compute_metric, _classify
        baseline_val = _compute_metric(audio_baseline, behavior.metric)
        mutated_val = _compute_metric(audio_mutated, behavior.metric)

        threshold = behavior.effect_threshold
        if threshold is None:
            threshold = 0.5 if "rms" in behavior.metric else 100.0

        status, observed_dir = _classify(baseline_val, mutated_val, "change", threshold)
        unit = "dB" if "rms" in behavior.metric else "Hz"
        delta = mutated_val - baseline_val

        from serum2.qualification.a3_behavior_observation import create_behavior_observation
        return create_behavior_observation(
            status=status,
            reason="baseline={:.2f}{}, mutated={:.2f}{}, delta={:+.2f}{}".format(
                baseline_val, unit, mutated_val, unit, delta, unit
            ),
            baseline_metric=baseline_val,
            mutated_metric=mutated_val,
            metric_name=behavior.metric,
            expected_direction="change",
            observed_direction=observed_dir,
            baseline_rendered=True,
            mutated_rendered=True,
        )

    except Exception as e:
        import traceback
        from serum2.qualification.a3_behavior_observation import create_behavior_observation
        return create_behavior_observation(
            status="UNKNOWN",
            reason="Behavior pipeline error: {}".format(e),
            details={"traceback": traceback.format_exc()},
        )


# ---------------------------------------------------------------------------
# Build arm bodies from capability + mutation value
# ---------------------------------------------------------------------------

def _build_arms(
    capability: ControlCapability,
    skeleton: tuple,
    baseline_value: Any,
    mutated_value: Any,
) -> tuple[dict, dict, list, list]:
    """Return (body_baseline, body_mutated, baseline_arm_host, mutated_arm_host).

    For cbor_body/cbor_string: both arms start from skeleton body; mutated arm
    has mutation applied to CBOR.
    For host_param: both arms use the same skeleton body; arm-specific host
    contexts carry the baseline and mutated values.
    """
    route = capability.mutation_route
    meta, body = skeleton
    body_base = copy.deepcopy(body)

    if route.adapter in ("cbor_body", "cbor_string"):
        body_mut = _apply_mutation_cbor_body(body_base, route.path, mutated_value)
        if baseline_value is not None:
            body_base = _apply_mutation_cbor_body(body_base, route.path, baseline_value)
        baseline_host: list = list(capability.behavior_route.baseline_host_context)
        mutated_host: list = list(capability.behavior_route.mutated_host_context)

    elif route.adapter == "host_param":
        body_mut = copy.deepcopy(body_base)
        # baseline and mutated values expressed as arm-specific host contexts
        baseline_host = [(route.host_param, float(baseline_value))]
        mutated_host = [(route.host_param, float(mutated_value))]
        # Merge with any additional behavior route host contexts
        baseline_host = baseline_host + list(capability.behavior_route.baseline_host_context)
        mutated_host = mutated_host + list(capability.behavior_route.mutated_host_context)

    else:
        raise ValueError("Unsupported adapter: {!r}".format(route.adapter))

    return body_base, body_mut, baseline_host, mutated_host


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def qualify_capability(
    *,
    capability: ControlCapability,
    skeleton: tuple,
    baseline_value: Any,
    mutated_value: Any,
    experiment_id: str,
    run_behavior: bool = True,
) -> MutationReceipt:
    """Generic qualification pipeline.

    No semantic-ID-specific branching. All routing is from capability fields.

    Args:
        capability: The ControlCapability to qualify.
        skeleton: (meta, body) from bridge.capture_v8_skeleton().
        baseline_value: Value for the baseline arm (pre-mutation state).
        mutated_value: Value for the mutated arm.
        experiment_id: Unique experiment identifier.
        run_behavior: If False, skip behavior gate (route-resolution-only mode).
    """
    route = capability.mutation_route

    if route.adapter == "NOT_SUPPORTED":
        return MutationReceipt(
            semantic_id=capability.semantic_id,
            mutation_class=capability.mutation_class,
            adapter=route.adapter,
            generation_status="SKIPPED",
            behavior_status="SKIPPED",
            error="Adapter NOT_SUPPORTED: {}".format(route.notes),
        )

    try:
        body_baseline, body_mutated, baseline_host, mutated_host = _build_arms(
            capability, skeleton, baseline_value, mutated_value
        )
    except Exception as e:
        return MutationReceipt(
            semantic_id=capability.semantic_id,
            mutation_class=capability.mutation_class,
            adapter=route.adapter,
            generation_status="FAIL",
            behavior_status="NOT_RUN",
            error="Arm build failed: {}".format(e),
        )

    # Generation gate
    gen_result = _check_generation_gate(body_baseline, body_mutated, route)
    gen_status = gen_result.get("status", "FAIL")

    # Behavior gate
    if not run_behavior or not capability.behavior_route.is_observable:
        behavior_obs = BEHAVIOR_NOT_RUN
        behavior_status = "NOT_RUN"
    else:
        # Build a modified capability with merged host contexts for behavior
        from dataclasses import replace
        behavior_with_context = BehaviorRoute(
            metric=capability.behavior_route.metric,
            exercise_context=capability.behavior_route.exercise_context,
            baseline_host_context=tuple(baseline_host),
            mutated_host_context=tuple(mutated_host),
            effect_threshold=capability.behavior_route.effect_threshold,
            notes=capability.behavior_route.notes,
        )
        behavior_obs = _run_behavior_gate(
            capability=capability,
            baseline_value=baseline_value,
            mutated_value=mutated_value,
            body_baseline=body_baseline,
            body_mutated=body_mutated,
            skeleton=skeleton,
            experiment_id=experiment_id,
            route=route,
            behavior=behavior_with_context,
        )
        behavior_status = behavior_obs.status

    return MutationReceipt(
        semantic_id=capability.semantic_id,
        mutation_class=capability.mutation_class,
        adapter=route.adapter,
        generation_status=gen_status,
        behavior_status=behavior_status,
        behavior_observation=behavior_obs,
        generation_details=gen_result,
    )
