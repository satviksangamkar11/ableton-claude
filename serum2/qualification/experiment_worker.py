"""Experiment worker — executes ONE BehaviorExperiment in a fresh process.

This is the subprocess entrypoint. It:
1. Loads a serialized BehaviorExperiment
2. Constructs baseline and treatment arms
3. Renders both
4. Measures all dimensions
5. Produces BehaviorObservation + ExerciseQualification
6. Serializes and exits

Called by experiment_orchestrator.py via subprocess.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import datetime
import traceback
from typing import Any, Dict, Optional

import numpy as np
import dawdreamer as daw

from serum2 import bridge, pathmerge
from serum2.evidence import epoch as epoch_mod
from serum2.evidence.harness import build_arm
from serum2.evidence.behavior_observation import BehaviorObservation, MeasurementDimension
from serum2.evidence.exercise_qualification import make_exercise_qualification
from serum2.evidence.measure import METRICS
from serum2.behavior.measurement.pitch import semitone_shift
from serum2.qualification.behavior_experiment import BehaviorExperiment, MeasurementPlan


SR = 44100
BLOCK = 512
VST3 = epoch_mod.SERUM_VST3


def is_valid_signal(audio: np.ndarray) -> dict:
    """Check whether an audio array contains a real (non-silent, finite) signal.

    Returns a dict with keys: peak, nonzero_fraction, valid.
    Gate logic: peak > 1e-6 (above numerical noise) AND nonzero_fraction > 0.01
    (at least 1% non-zero samples) AND all values finite.

    Deliberately avoids any absolute dBFS threshold — the default Serum skeleton
    produces real audio at ~-20 dBFS RMS; a gate of rms_db > -20 would
    incorrectly reject valid signals.
    """
    peak = float(np.max(np.abs(audio)))
    nonzero_fraction = float(np.count_nonzero(audio) / audio.size)
    valid = bool(
        np.isfinite(audio).all()
        and peak > 1e-6
        and nonzero_fraction > 0.01
    )
    return {"peak": peak, "nonzero_fraction": nonzero_fraction, "valid": valid}


def _compute_metric(audio: np.ndarray, kernel: str) -> Optional[float]:
    """Compute a named measurement kernel on audio."""
    if kernel not in METRICS:
        return None
    return METRICS[kernel](audio)


def _apply_host_context(synth: Any, context: list) -> None:
    """Apply host parameter mutations via synth.set_parameter."""
    if not context:
        return
    params = synth.get_parameters_description()
    by_name = {p["name"]: p["index"] for p in params}
    for name, value in context:
        if name not in by_name:
            raise KeyError(f"host parameter not found: {name!r}")
        synth.set_parameter(by_name[name], float(value))


def run_experiment_worker(experiment_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one BehaviorExperiment. Called via subprocess.

    Returns a dict with:
    - behavior_observation (serialized)
    - exercise_qualification (serialized)
    - error (if any)
    """

    try:
        # Reconstruct BehaviorExperiment from dict
        # Measurement plan comes as dicts, need to reconstruct as MeasurementPlan objects
        spec_copy = experiment_spec.copy()
        measurement_plan_dicts = spec_copy.get("measurement_plan", [])
        spec_copy["measurement_plan"] = tuple(
            MeasurementPlan(**mp) if isinstance(mp, dict) else mp
            for mp in measurement_plan_dicts
        )

        exp = BehaviorExperiment(**spec_copy)
        exp.validate()

        # Load skeleton (fresh Serum instance)
        skeleton = bridge.capture_v8_skeleton(VST3)
        meta_c = copy.deepcopy(skeleton[0])
        body_c = copy.deepcopy(skeleton[1])

        # Load FX preset if specified
        if exp.fx_preset_path:
            from serum2 import codec
            _, preset_body = codec.load_preset_file(exp.fx_preset_path)
            body_c["FXRack0"] = copy.deepcopy(preset_body["FXRack0"])

        # Build baseline arm
        meta_baseline = copy.deepcopy(meta_c)
        body_baseline = copy.deepcopy(body_c)

        # Apply baseline overrides if any
        if exp.baseline_override:
            for path, val in exp.baseline_override.items():
                pathmerge.apply_path_value(body_baseline, path, val)

        # Build treatment arm
        meta_treatment = copy.deepcopy(meta_c)
        body_treatment = copy.deepcopy(body_c)

        # Apply treatment CBOR mutation if specified
        if exp.treatment_cbor_path:
            pathmerge.apply_path_value(body_treatment, exp.treatment_cbor_path, exp.treatment_cbor_value)

        # Render both arms
        start_baseline = datetime.datetime.now()
        audio_baseline = _render_arm(meta_baseline, body_baseline, exp)
        end_baseline = datetime.datetime.now()
        baseline_render_time = (end_baseline - start_baseline).total_seconds()

        # Treatment arm: apply treatment-specific host param if specified
        treatment_extra: list = []
        if exp.treatment_host_param_name is not None and exp.treatment_host_param_value is not None:
            treatment_extra = [(exp.treatment_host_param_name, float(exp.treatment_host_param_value))]

        start_treatment = datetime.datetime.now()
        audio_treatment = _render_arm(meta_treatment, body_treatment, exp, extra_host_context=treatment_extra)
        end_treatment = datetime.datetime.now()
        treatment_render_time = (end_treatment - start_treatment).total_seconds()

        # Signal validity checks
        baseline_validity: Optional[dict] = None
        treatment_validity: Optional[dict] = None

        baseline_rendered = audio_baseline is not None and audio_baseline.shape[0] > 0
        treatment_rendered = audio_treatment is not None and audio_treatment.shape[0] > 0

        if baseline_rendered:
            baseline_validity = is_valid_signal(audio_baseline)
            if not baseline_validity["valid"]:
                baseline_rendered = False

        if treatment_rendered:
            treatment_validity = is_valid_signal(audio_treatment)
            if not treatment_validity["valid"]:
                treatment_rendered = False

        # Measure all dimensions.
        # Pass 1: compute direct (non-derived) dimensions from audio.
        # Pass 2: compute derived dimensions from already-measured values.
        measurements: list[MeasurementDimension] = []
        measured_by_name: dict[str, MeasurementDimension] = {}

        for plan in exp.measurement_plan:
            if plan.derived_from is not None:
                # Deferred — resolved in pass 2.
                continue

            baseline_metric = None
            treatment_metric = None
            delta = None
            status = "NOT_RUN"

            if baseline_rendered:
                baseline_metric = _compute_metric(audio_baseline, plan.kernel)

            if treatment_rendered:
                treatment_metric = _compute_metric(audio_treatment, plan.kernel)

            if baseline_metric is not None and treatment_metric is not None:
                delta = treatment_metric - baseline_metric
                abs_delta = abs(delta)
                if plan.threshold is not None:
                    status = "NO_OBSERVED_EFFECT" if abs_delta < plan.threshold else "EFFECT_OBSERVED"
                else:
                    status = "EFFECT_OBSERVED" if abs_delta > 0 else "NO_OBSERVED_EFFECT"

            dim = MeasurementDimension(
                name=plan.name,
                kernel=plan.kernel,
                baseline=baseline_metric,
                treatment=treatment_metric,
                delta=delta,
                threshold=plan.threshold,
                status=status,
            )
            measurements.append(dim)
            measured_by_name[plan.name] = dim

        # Pass 2: derived dimensions.
        for plan in exp.measurement_plan:
            if plan.derived_from is None:
                continue

            baseline_metric = None
            treatment_metric = None
            delta = None
            status = "NOT_RUN"

            source = measured_by_name.get(plan.derived_from)
            if source is not None and source.baseline is not None and source.treatment is not None:
                if plan.kernel == "pitch_shift_semitones":
                    try:
                        delta = semitone_shift(source.baseline, source.treatment)
                        # baseline is 0 by definition (shift relative to self)
                        baseline_metric = 0.0
                        treatment_metric = delta
                    except ValueError:
                        status = "EXPERIMENT_FAILURE"
                else:
                    # Generic derived: treatment - baseline of source
                    delta = source.treatment - source.baseline
                    baseline_metric = source.baseline
                    treatment_metric = source.treatment

                if status != "EXPERIMENT_FAILURE" and delta is not None:
                    abs_delta = abs(delta)
                    if plan.threshold is not None:
                        status = "NO_OBSERVED_EFFECT" if abs_delta < plan.threshold else "EFFECT_OBSERVED"
                    else:
                        status = "EFFECT_OBSERVED" if abs_delta != 0 else "NO_OBSERVED_EFFECT"

            dim = MeasurementDimension(
                name=plan.name,
                kernel=plan.kernel,
                baseline=baseline_metric,
                treatment=treatment_metric,
                delta=delta,
                threshold=plan.threshold,
                status=status,
            )
            measurements.append(dim)
            measured_by_name[plan.name] = dim

        # Build validity notes for execution_notes
        validity_notes = {
            "baseline_validity": baseline_validity,
            "treatment_validity": treatment_validity,
        }

        # Build BehaviorObservation
        observation = BehaviorObservation(
            experiment_id=exp.experiment_id,
            timestamp=datetime.datetime.now(datetime.UTC).isoformat(),
            semantic_target=exp.semantic_target,
            operation=exp.operation,
            context=exp.context,
            context_provenance=exp.context_provenance,
            baseline_intervention={
                "cbor_overrides": exp.baseline_override or {},
                "host_context": exp.baseline_host_context or [],
            },
            treatment_intervention={
                "cbor_path": exp.treatment_cbor_path,
                "cbor_value": exp.treatment_cbor_value,
                "host_param_name": exp.treatment_host_param_name,
                "host_param_value": exp.treatment_host_param_value,
                "host_context": exp.treatment_host_context or [],
            },
            baseline_rendered=baseline_rendered,
            treatment_rendered=treatment_rendered,
            baseline_render_time_sec=baseline_render_time,
            treatment_render_time_sec=treatment_render_time,
            measurements=tuple(measurements),
            isolation_level="single_field",
            execution_notes=json.dumps(validity_notes),
        )

        # Build ExerciseQualification
        primary = observation.primary_measurement
        if primary and primary.status == "EFFECT_OBSERVED":
            eq = make_exercise_qualification(
                target_semantic_id=exp.semantic_target,
                target_cbor_path=exp.treatment_cbor_path or f"host_param:{exp.treatment_host_param_name}",
                frozen_context=exp.context,
                mutation_value=exp.treatment_cbor_value or exp.treatment_host_param_value,
                experiment_id=exp.experiment_id,
                behavior_result={
                    "status": primary.status,
                    "baseline_metric": primary.baseline,
                    "mutated_metric": primary.treatment,
                    "metric_name": primary.kernel,
                    "expected_direction": exp.expected_direction,
                    "observed_direction": "increase" if (primary.delta or 0) > 0 else "decrease",
                    "delta": primary.delta,
                    "baseline_rendered": baseline_rendered,
                    "mutated_rendered": treatment_rendered,
                    "effect_threshold": primary.threshold,
                    "reason": f"{primary.kernel}: baseline={primary.baseline:.2f}, "
                              f"treatment={primary.treatment:.2f}, "
                              f"delta={primary.delta:+.2f}" if primary.delta else "N/A",
                },
            )
        else:
            eq = None

        return {
            "success": True,
            "experiment_id": exp.experiment_id,
            "behavior_observation": observation.to_dict(),
            "exercise_qualification": eq.to_dict() if eq else None,
        }

    except Exception as e:
        return {
            "success": False,
            "experiment_id": experiment_spec.get("experiment_id", "unknown"),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def _render_arm(
    meta: Dict[str, Any],
    body: Dict[str, Any],
    exp: BehaviorExperiment,
    extra_host_context: Optional[list] = None,
) -> Optional[np.ndarray]:
    """Render one arm (baseline or treatment).

    Applies exercise context host params + arm-specific host context.
    extra_host_context: additional (name, value) pairs applied after shared context,
    used for treatment-specific host param mutations.
    Returns audio array or None on failure.
    """
    try:
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)

        bridge.write_state_file(tmp, meta, body)

        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)

        try:
            synth.load_state(tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

        # Apply shared context (both arms)
        _apply_host_context(synth, [(k, float(v)) for k, v in exp.context.items()])

        # Apply arm-specific extra host context (treatment mutations via host params)
        if extra_host_context:
            _apply_host_context(synth, extra_host_context)

        synth.clear_midi()
        synth.add_midi_note(60, 100, 0.0, 1.5)
        engine.load_graph([(synth, [])])
        engine.render(2.0)

        return np.asarray(engine.get_audio())

    except Exception as e:
        print(f"Render arm failed: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    # Called via subprocess: argv[1] = JSON experiment spec
    if len(sys.argv) < 2:
        print("Usage: python experiment_worker.py <experiment_json>", file=sys.stderr)
        sys.exit(1)

    spec_json = sys.argv[1]
    spec = json.loads(spec_json)

    result = run_experiment_worker(spec)
    print(json.dumps(result, default=str))
