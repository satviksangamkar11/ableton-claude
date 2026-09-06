"""The evidence harness. ExperimentSpec in, EvidenceRecord out.

Runs both arms (control and treatment) with prerequisites applied identically,
so the declared mutations are the only difference between them.
"""
import copy, os, tempfile
import numpy as np
import dawdreamer as daw

from .. import bridge, codec, vst3_state, pathmerge
from . import epoch as epoch_mod
from .spec import ExperimentSpec, validate
from .record import (EvidenceRecord, EvidenceArm, CausalMeasurement, MeasurementTarget,
                     EFFECT_OBSERVED, NO_OBSERVED_EFFECT, WRONG_DIRECTION,
                     PASS, FAIL, NOT_RUN)
from .canonical import experiment_condition_signature, measurement_condition_signature
from . import runtime as runtime_mod
from .measure import METRICS, direction_of
from .measurement import define, MeasurementTargetRef, load_kernel
from dataclasses import asdict

VST3 = epoch_mod.SERUM_VST3
SR = 44100
BLOCK = 512


def _apply_body_prerequisites(body, prerequisites):
    for p in prerequisites:
        if p.field_path.startswith("body:"):
            key = p.field_path.split("body:", 1)[1]
            body[key] = copy.deepcopy(p.declared_value)
    return body


def _apply_host_prerequisites(synth, prerequisites):
    if not prerequisites:
        return
    params = synth.get_parameters_description()
    by_name = {p["name"]: p["index"] for p in params}
    for p in prerequisites:
        if p.field_path.startswith("host:"):
            name = p.field_path.split("host:", 1)[1]
            if name not in by_name:
                raise KeyError(f"host parameter not found: {name!r}")
            synth.set_parameter(by_name[name], float(p.declared_value))


def build_arm(skeleton, spec, apply_mutations: bool):
    """baseline_overrides apply to BOTH arms (control and treatment) via
    path-merge, so a treatment mutation on a sibling field of the same body
    key cannot clobber them. mutations apply ONLY when apply_mutations=True
    (the treatment arm), on top of the shared baseline."""
    meta = copy.deepcopy(skeleton[0])
    body = copy.deepcopy(skeleton[1])
    _apply_body_prerequisites(body, spec.prerequisites)
    for m in spec.baseline_overrides:
        pathmerge.apply_path_value(body, m.target_path, copy.deepcopy(m.value))
    if apply_mutations:
        for m in spec.mutations:
            pathmerge.apply_path_value(body, m.target_path, copy.deepcopy(m.value))
    return meta, body


def render_arm(meta, body, spec, plan):
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    try:
        synth.load_state(tmp)
        load_ok, load_err = True, None
    except Exception as e:
        os.remove(tmp)
        return None, False, "%s: %s" % (type(e).__name__, e), {}
    os.remove(tmp)

    _apply_host_prerequisites(synth, spec.prerequisites)

    # Read host prerequisites back HERE, while the engine is still alive.
    # Verification must happen at the point of execution.
    observed_host = {}
    for p in spec.prerequisites:
        if p.field_path.startswith("host:"):
            name = p.field_path.split("host:", 1)[1]
            try:
                observed_host[p.field_path] = runtime_mod.read_host_param(synth, name)
            except KeyError as e:
                observed_host[p.field_path] = "MISSING: %s" % e

    st = plan.stimulus
    synth.clear_midi()
    synth.add_midi_note(st.note, st.velocity, 0.0, st.note_len)
    engine.load_graph([(synth, [])])
    engine.render(st.render_seconds)
    audio = np.asarray(engine.get_audio())
    return audio, True, None, observed_host


def resave_state(meta, body, spec):
    """Load our generated state, then ask Serum itself to write it back out."""
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    fd, out = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    synth.save_state(out)
    raw = open(out, "rb").read()
    os.remove(out)
    return codec.decode(vst3_state.unwrap_vc2(raw))


def run(spec: ExperimentSpec, skeleton=None):
    """ExperimentSpec in, EvidenceRecord out. Both arms execute with the
    prerequisites applied identically; runtime verification then establishes
    that this actually held rather than trusting the declaration."""
    validate(spec)   # design gate -- refuse to produce evidence from a bad design

    if skeleton is None:
        skeleton = bridge.capture_v8_skeleton(VST3)

    ep = epoch_mod.current_epoch(SR, BLOCK)
    exp_sig = spec.experiment_condition_signature()
    meas_sigs = spec.measurement_condition_signatures()

    meta_c, body_c = build_arm(skeleton, spec, apply_mutations=False)
    meta_t, body_t = build_arm(skeleton, spec, apply_mutations=True)

    # Two-granularity check, needed since mutations can be either whole-key
    # ("ModSlot30") or nested-path ("Env0.plainParams.kParamDecay"):
    #   top-level  : no OTHER top-level key changed (catches confounds)
    #   fine-grained: the declared leaf value actually differs (catches no-ops)
    diff_keys = sorted(k for k in body_t if body_t[k] != body_c.get(k))
    intended_top = sorted({m.target_path.split(".")[0] for m in spec.mutations})
    intended = sorted(m.target_path for m in spec.mutations)
    top_level_ok = (diff_keys == intended_top)
    fine_grained_ok = all(
        pathmerge.read_path_value(body_t, m.target_path) != pathmerge.read_path_value(body_c, m.target_path)
        for m in spec.mutations
    )
    matches_intent = top_level_ok and fine_grained_ok
    state_diff = {
        "status": PASS if matches_intent else FAIL,
        "matches_intent": matches_intent,
        "top_level_ok": top_level_ok,
        "fine_grained_ok": fine_grained_ok,
        "diff_keys": diff_keys,
        "intended_targets": intended,
        "control_hash": bridge.state_hash(meta_c, body_c),
        "treatment_hash": bridge.state_hash(meta_t, body_t),
    }

    load_result = {"status": PASS, "ok": True, "control_error": None, "treatment_error": None}
    causal = []
    runtime_verifications = []

    for plan_idx, plan in enumerate(spec.measurement_plans):
        a_c, ok_c, err_c, obs_host_c = render_arm(meta_c, body_c, spec, plan)
        a_t, ok_t, err_t, obs_host_t = render_arm(meta_t, body_t, spec, plan)
        if not (ok_c and ok_t):
            load_result = {"status": FAIL, "ok": False,
                           "control_error": err_c, "treatment_error": err_t}
            break
        # RUNTIME VERIFICATION: values read back from both executed arms
        obs = runtime_mod.observe_prerequisites_from_readings(
            spec.prerequisites, body_c, body_t, obs_host_c, obs_host_t)
        runtime_verifications.append(
            runtime_mod.verification_summary(spec.prerequisites, obs))

        if plan.kernel_artifact:
            mdef = define(plan.metric, plan.kernel_artifact,
                          MeasurementTargetRef(plan.target.field_path,
                                               plan.target.module,
                                               plan.target.parameter))
            fn = lambda audio, _st=None, _k=load_kernel(mdef): _k(audio)
            mdef_id = mdef.measurement_definition_id
        else:
            fn = METRICS[plan.metric]
            mdef_id = None
        st = asdict(plan.stimulus)
        base = fn(a_c, st)
        treat = fn(a_t, st)
        delta = treat - base
        obs_dir = direction_of(delta, plan.threshold)
        if obs_dir == "none":
            outcome = NO_OBSERVED_EFFECT
        elif plan.expected_direction != "none" and obs_dir != plan.expected_direction:
            outcome = WRONG_DIRECTION
        else:
            outcome = EFFECT_OBSERVED
        causal.append(CausalMeasurement(
            metric=plan.metric,
            target=MeasurementTarget(plan.target.field_path,
                                     plan.target.module, plan.target.parameter),
            baseline=base, treatment=treat, delta=delta,
            expected_direction=plan.expected_direction,
            observed_direction=obs_dir, threshold=plan.threshold,
            status=outcome,
            measurement_condition_signature=meas_sigs[plan_idx],
            measurement_definition_id=mdef_id))

    persistence = {"status": NOT_RUN, "checked": False, "exact_match": False, "detail": None}
    stored_values_on_mismatch = {}   # path -> actual Serum readback, only when value changed
    if load_result["ok"]:
        try:
            _, resaved_body = resave_state(meta_t, body_t, spec)
            per_target = {}
            for m in spec.mutations:
                stored = pathmerge.read_path_value(resaved_body, m.target_path)
                match = pathmerge.tolerant_equal(stored, m.value)
                per_target[m.target_path] = match
                if not match and isinstance(stored, (int, float)):
                    stored_values_on_mismatch[m.target_path] = stored
            persistence = {
                "status": PASS if all(per_target.values()) else FAIL,
                "checked": True,
                "exact_match": all(per_target.values()),
                "detail": per_target,
            }
            if stored_values_on_mismatch:
                persistence["stored_values"] = stored_values_on_mismatch
        except Exception as e:
            persistence = {"status": FAIL, "checked": True, "exact_match": False,
                           "detail": "%s: %s" % (type(e).__name__, e)}

    # Populate structural_observation only when the spec explicitly declares
    # clamp-probe semantics. A plain persistence failure is NOT evidence of a
    # structural bound -- the interpretation requires the declared intent.
    structural_obs = {}
    if getattr(spec, "probe_semantics", None) == "NUMERIC_CLAMP_RANGE":
        for m in spec.mutations:
            stored = stored_values_on_mismatch.get(m.target_path)
            if stored is not None and isinstance(m.value, (int, float)):
                probe_val = float(m.value)
                stored_f = float(stored)
                if stored_f > probe_val:
                    bound_type = "MINIMUM"   # Serum pushed value up -> probe was below min
                elif stored_f < probe_val:
                    bound_type = "MAXIMUM"   # Serum pushed value down -> probe was above max
                else:
                    bound_type = "AMBIGUOUS"
                structural_obs[m.target_path] = {
                    "kind": "NUMERIC_CLAMP_RANGE",
                    "probe_value": probe_val,
                    "clamped_to": stored_f,
                    "bound_type": bound_type,
                }

    declared_ctx = {p.field_path: p.declared_value for p in spec.prerequisites}
    observed_ctx = (runtime_verifications[0]["observations"]
                    if runtime_verifications else None)
    arms = (
        EvidenceArm("arm_control", "control", declared_ctx, observed_ctx,
                    {"state_hash": state_diff["control_hash"]},
                    load_result["status"], load_result["status"], {}),
        EvidenceArm("arm_treatment", "treatment", declared_ctx, observed_ctx,
                    {"state_hash": state_diff["treatment_hash"]},
                    load_result["status"], load_result["status"], {}),
    )

    return EvidenceRecord(
        experiment_id=spec.experiment_id,
        epoch=ep,
        experiment={
            "mutations": [asdict(m) for m in spec.mutations],
            "prerequisites": [asdict(p) for p in spec.prerequisites],
            "isolation_level": spec.isolation_level,
            "claim_subject": spec.claim_subject,
            "claim_predicate": spec.claim_predicate,
            "experiment_condition_signature": exp_sig,
            "measurement_condition_signatures": meas_sigs,
            "mutation_signature": spec.mutation_signature(),
            "notes": spec.notes,
        },
        arms=arms,
        runtime_verifications=tuple(runtime_verifications),
        state_observation=state_diff,
        load_observation=load_result,
        render_observation={"status": PASS if load_result["ok"] else NOT_RUN},
        causal_measurements=tuple(causal),
        persistence_observation=persistence,
        structural_observation=structural_obs,
    )
