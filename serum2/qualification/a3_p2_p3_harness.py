"""16.5.69.2-A3-14: P1/P2/P3 Lifecycle Harness

Implements P1 (same-lifecycle), P2 (fresh instance), and P3 (fresh process) persistence tests.

P1: mutate → save/resave → reload (same instance) → inspect
P2: mutate → save → destroy instance → new instance → load → inspect
P3: process A (mutate+save) → process B (subprocess, load+inspect)
"""

from __future__ import annotations

import os
import tempfile
import subprocess
import json
import sys
from typing import Any
import copy

import dawdreamer as daw

from serum2 import bridge, codec, vst3_state, pathmerge
from serum2.evidence import epoch as epoch_mod

from serum2.qualification.a3_evidence_extension import (
    P1PersistenceObservation,
)
from serum2.qualification.a3_evidence_extension import (
    P1_NOT_RUN,
)
from serum2.qualification.a3_persistence_lifecycle import (
    create_p2_observation,
    create_p3_observation,
    P2_NOT_RUN,
    P3_NOT_RUN,
)

VST3 = epoch_mod.SERUM_VST3
SR = 44100
BLOCK = 512


def run_p1_lifecycle_test(
    *,
    experiment_id: str,
    target_path: str,
    mutation_value: Any,
    skeleton: tuple[dict, dict],
    spec: Any,
) -> dict[str, Any]:
    """Run P1 lifecycle test: same-lifecycle persistence.

    Sequence:
      1. Build baseline state (no mutations)
      2. Apply mutation
      3. Save/resave state
      4. Reload same state file
      5. Read target and compare

    Returns dict that can be converted to P1PersistenceObservation.
    """

    try:
        # Build control (baseline) and treatment (mutated) states
        from serum2.evidence.harness import build_arm, resave_state

        meta_c, body_c = build_arm(skeleton, spec, apply_mutations=False)
        meta_t, body_t = build_arm(skeleton, spec, apply_mutations=True)

        # Read target value in baseline
        target_value_before = pathmerge.read_path_value(body_c, target_path)

        # Read target value after mutation
        target_value_after_mutation = pathmerge.read_path_value(body_t, target_path)

        # Save/resave the mutated state and reload it
        try:
            _, resaved_body = resave_state(meta_t, body_t, spec)
            target_value_after_reload = pathmerge.read_path_value(resaved_body, target_path)
            save_completed = True
            reload_completed = True
        except Exception as e:
            return {
                "status": "FAIL",
                "reason": "Save/resave failed: {}".format(str(e)),
                "experiment_id": experiment_id,
                "target_path": target_path,
                "target_value_before": target_value_before,
                "target_value_after_mutation": target_value_after_mutation,
                "save_completed": False,
                "reload_completed": False,
            }

        # Compare: did the value survive reload?
        match = pathmerge.tolerant_equal(target_value_after_reload, mutation_value)

        return {
            "status": "PASS" if match else "FAIL",
            "reason": "P1 persisted value" if match else "P1 lost value on reload",
            "experiment_id": experiment_id,
            "target_path": target_path,
            "target_value_before": target_value_before,
            "target_value_after_mutation": target_value_after_mutation,
            "target_value_after_reload": target_value_after_reload,
            "save_completed": save_completed,
            "reload_completed": reload_completed,
            "expected_value": mutation_value,
            "match": match,
        }

    except Exception as e:
        return {
            "status": "FAIL",
            "reason": "P1 lifecycle error: {}".format(str(e)),
            "experiment_id": experiment_id,
            "target_path": target_path,
            "save_completed": False,
            "reload_completed": False,
        }


def run_p2_lifecycle_test(
    *,
    experiment_id: str,
    target_path: str,
    mutation_value: Any,
    skeleton: tuple[dict, dict],
    spec: Any,
) -> dict[str, Any]:
    """Run P2 lifecycle test: fresh instance persistence.

    Sequence:
      1. Create Serum instance A, mutate, save state
      2. Destroy instance A
      3. Create new Serum instance B, load state
      4. Inspect whether target retained mutated_value

    Returns observation dict that can be converted to P2PersistenceObservation.
    """

    try:
        from serum2.evidence.harness import build_arm

        meta_t, body_t = build_arm(skeleton, spec, apply_mutations=True)

        # Read baseline value
        meta_c, body_c = build_arm(skeleton, spec, apply_mutations=False)
        target_value_before = pathmerge.read_path_value(body_c, target_path)
        target_value_after_mutation = pathmerge.read_path_value(body_t, target_path)

        # ========== INSTANCE A ==========
        # Create first instance, save state
        fd_a, state_file_a = tempfile.mkstemp(suffix=".bin")
        os.close(fd_a)
        bridge.write_state_file(state_file_a, meta_t, body_t)

        engine_a = daw.RenderEngine(SR, BLOCK)
        synth_a = engine_a.make_plugin_processor("serum", VST3)
        synth_a.load_state(state_file_a)
        instance_a_id = id(synth_a)

        # Save state from instance A
        fd_save, save_file = tempfile.mkstemp(suffix=".bin")
        os.close(fd_save)
        synth_a.save_state(save_file)
        saved_state_identity = str(hash(open(save_file, "rb").read()))

        # Destroy instance A
        del synth_a
        del engine_a
        os.remove(state_file_a)

        # ========== INSTANCE B ==========
        # Create new instance, load state
        engine_b = daw.RenderEngine(SR, BLOCK)
        synth_b = engine_b.make_plugin_processor("serum", VST3)
        instance_b_id = id(synth_b)

        synth_b.load_state(save_file)

        # Read target value from fresh instance
        fd_reload, reload_file = tempfile.mkstemp(suffix=".bin")
        os.close(fd_reload)
        synth_b.save_state(reload_file)
        raw = open(reload_file, "rb").read()
        reloaded_state = codec.decode(vst3_state.unwrap_vc2(raw))
        target_value_in_fresh_instance = pathmerge.read_path_value(reloaded_state[1], target_path)

        # Compare
        match = pathmerge.tolerant_equal(target_value_in_fresh_instance, mutation_value)

        # Cleanup
        del synth_b
        del engine_b
        os.remove(save_file)
        os.remove(reload_file)

        return {
            "status": "PASS" if match else "FAIL",
            "reason": "P2 persisted value" if match else "P2 lost value in fresh instance",
            "experiment_id": experiment_id,
            "target_path": target_path,
            "target_value_before": target_value_before,
            "target_value_after_mutation": target_value_after_mutation,
            "target_value_in_fresh_instance": target_value_in_fresh_instance,
            "saved_state_identity": saved_state_identity,
            "fresh_instance_created": instance_a_id != instance_b_id,
            "source_instance_id": instance_a_id,
            "fresh_instance_id": instance_b_id,
            "match": match,
        }

    except Exception as e:
        import traceback
        return {
            "status": "FAIL",
            "reason": "P2 lifecycle error: {}".format(str(e)),
            "experiment_id": experiment_id,
            "target_path": target_path,
            "error_traceback": traceback.format_exc(),
        }


def _p3_subprocess_reader(state_file: str, target_path: str, mutation_value: Any) -> dict[str, Any]:
    """Subprocess worker: load state and inspect target value.

    This runs in a genuinely separate process.
    Returns result as JSON to stdout.
    """
    try:
        import dawdreamer as daw
        from serum2 import bridge, codec, vst3_state, pathmerge
        from serum2.evidence import epoch as epoch_mod

        VST3 = epoch_mod.SERUM_VST3
        SR = 44100
        BLOCK = 512

        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)
        synth.load_state(state_file)

        # Save and reload to get decoded state
        import tempfile
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        import os
        os.close(fd)
        synth.save_state(tmp)
        raw = open(tmp, "rb").read()
        reloaded_state = codec.decode(vst3_state.unwrap_vc2(raw))
        target_value = pathmerge.read_path_value(reloaded_state[1], target_path)
        os.remove(tmp)

        match = pathmerge.tolerant_equal(target_value, mutation_value)

        return {
            "status": "PASS" if match else "FAIL",
            "target_value_in_fresh_process": target_value,
            "match": match,
            "reader_pid": os.getpid(),
        }

    except Exception as e:
        import os
        return {
            "status": "FAIL",
            "error": str(e),
            "reader_pid": os.getpid(),
        }


def run_p3_lifecycle_test(
    *,
    experiment_id: str,
    target_path: str,
    mutation_value: Any,
    skeleton: tuple[dict, dict],
    spec: Any,
) -> dict[str, Any]:
    """Run P3 lifecycle test: fresh process persistence.

    Sequence:
      1. Process A: Create Serum, mutate, save artifact
      2. Process A: Exit
      3. Process B: Subprocess, load artifact, inspect target

    Returns observation dict that can be converted to P3PersistenceObservation.
    """

    try:
        import os
        from serum2.evidence.harness import build_arm

        meta_t, body_t = build_arm(skeleton, spec, apply_mutations=True)

        # Read baseline value
        meta_c, body_c = build_arm(skeleton, spec, apply_mutations=False)
        target_value_before = pathmerge.read_path_value(body_c, target_path)
        target_value_after_mutation = pathmerge.read_path_value(body_t, target_path)

        # Save mutated state to artifact
        fd_artifact, artifact_file = tempfile.mkstemp(suffix=".bin")
        os.close(fd_artifact)
        bridge.write_state_file(artifact_file, meta_t, body_t)

        saved_state_identity = str(hash(open(artifact_file, "rb").read()))
        writer_pid = os.getpid()

        # Run subprocess to load and inspect
        reader_script = """
import sys, json, os
sys.path.insert(0, {!r})
from serum2.qualification.a3_p2_p3_harness import _p3_subprocess_reader
result = _p3_subprocess_reader({!r}, {!r}, {!r})
print(json.dumps(result))
""".format(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            artifact_file,
            target_path,
            mutation_value,
        )

        result = subprocess.run(
            [sys.executable, "-c", reader_script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            os.remove(artifact_file)
            return {
                "status": "FAIL",
                "reason": "Subprocess failed: {}".format(result.stderr),
                "experiment_id": experiment_id,
                "target_path": target_path,
                "writer_pid": writer_pid,
            }

        # Parse subprocess result
        reader_result = json.loads(result.stdout.strip())
        reader_pid = reader_result.get("reader_pid")

        target_value_in_fresh_process = reader_result.get("target_value_in_fresh_process")
        match = reader_result.get("match", False)

        os.remove(artifact_file)

        return {
            "status": "PASS" if match else "FAIL",
            "reason": "P3 persisted value" if match else "P3 lost value in fresh process",
            "experiment_id": experiment_id,
            "target_path": target_path,
            "target_value_before": target_value_before,
            "target_value_after_mutation": target_value_after_mutation,
            "target_value_in_fresh_process": target_value_in_fresh_process,
            "saved_state_identity": saved_state_identity,
            "process_a_pid": writer_pid,
            "process_b_pid": reader_pid,
            "process_boundary_crossed": writer_pid != reader_pid,
            "match": match,
        }

    except Exception as e:
        import traceback
        return {
            "status": "FAIL",
            "reason": "P3 lifecycle error: {}".format(str(e)),
            "experiment_id": experiment_id,
            "target_path": target_path,
            "error_traceback": traceback.format_exc(),
        }


def qualify_with_p2_p3(
    *,
    experiment_id: str,
    resolved_target: dict[str, Any],
    experiment_spec: dict[str, Any],
) -> dict[str, Any]:
    """Backward compatibility wrapper. Returns NOT_RUN until real execution."""

    return {
        "experiment_id": experiment_id,
        "p2_observation": create_p2_observation(
            status="NOT_RUN",
            reason="P2 lifecycle test not executed",
        ),
        "p3_observation": create_p3_observation(
            status="NOT_RUN",
            reason="P3 lifecycle test not executed",
        ),
    }


def qualify_with_p1_p2_p3(
    *,
    experiment_id: str,
    resolved_target: dict[str, Any],
    spec: Any,
    skeleton: tuple[dict, dict],
) -> dict[str, Any]:
    """Run P1/P2/P3 lifecycle tests on the specification.

    Args:
        experiment_id: Experiment ID
        resolved_target: Resolved target metadata
        spec: ExperimentSpec (from serum2.evidence.spec)
        skeleton: VST3 skeleton (meta, body) from bridge

    Returns dict with p1/p2/p3 observations and results.
    """

    if not spec.mutations:
        return {
            "experiment_id": experiment_id,
            "error": "No mutations in spec",
            "p1_observation": P1_NOT_RUN,
            "p2_observation": P2_NOT_RUN,
            "p3_observation": P3_NOT_RUN,
        }

    mutation = spec.mutations[0]
    target_path = mutation.target_path
    mutation_value = mutation.value

    # Run P1 lifecycle
    p1_obs_dict = run_p1_lifecycle_test(
        experiment_id=experiment_id,
        target_path=target_path,
        mutation_value=mutation_value,
        skeleton=skeleton,
        spec=spec,
    )

    # Run P2 lifecycle
    p2_obs_dict = run_p2_lifecycle_test(
        experiment_id=experiment_id,
        target_path=target_path,
        mutation_value=mutation_value,
        skeleton=skeleton,
        spec=spec,
    )

    # Run P3 lifecycle
    p3_obs_dict = run_p3_lifecycle_test(
        experiment_id=experiment_id,
        target_path=target_path,
        mutation_value=mutation_value,
        skeleton=skeleton,
        spec=spec,
    )

    # Import factory functions
    from serum2.qualification.a3_evidence_extension import create_p1_observation

    # Convert to observation objects with full details
    p1_obs = create_p1_observation(
        status=p1_obs_dict.get("status", "NOT_RUN"),
        reason=p1_obs_dict.get("reason"),
        target_value_before=p1_obs_dict.get("target_value_before"),
        target_value_after_mutation=p1_obs_dict.get("target_value_after_mutation"),
        target_value_after_reload=p1_obs_dict.get("target_value_after_reload"),
        details={k: v for k, v in p1_obs_dict.items()
                if k not in ["status", "reason", "target_value_before",
                            "target_value_after_mutation", "target_value_after_reload"]},
    )

    p2_obs = create_p2_observation(
        status=p2_obs_dict.get("status", "NOT_RUN"),
        reason=p2_obs_dict.get("reason"),
        target_value_before=p2_obs_dict.get("target_value_before"),
        target_value_after_mutation=p2_obs_dict.get("target_value_after_mutation"),
        target_value_in_fresh_instance=p2_obs_dict.get("target_value_in_fresh_instance"),
        saved_state_identity=p2_obs_dict.get("saved_state_identity"),
        fresh_instance_created=p2_obs_dict.get("fresh_instance_created", False),
        fresh_instance_identity=str(p2_obs_dict.get("fresh_instance_id")),
        details={k: v for k, v in p2_obs_dict.items()
                if k not in ["status", "reason", "target_value_before",
                            "target_value_after_mutation", "target_value_in_fresh_instance",
                            "saved_state_identity", "fresh_instance_created",
                            "fresh_instance_identity", "fresh_instance_id"]},
    )

    p3_obs = create_p3_observation(
        status=p3_obs_dict.get("status", "NOT_RUN"),
        reason=p3_obs_dict.get("reason"),
        target_value_before=p3_obs_dict.get("target_value_before"),
        target_value_after_mutation=p3_obs_dict.get("target_value_after_mutation"),
        target_value_in_fresh_process=p3_obs_dict.get("target_value_in_fresh_process"),
        saved_state_identity=p3_obs_dict.get("saved_state_identity"),
        process_a_pid=p3_obs_dict.get("process_a_pid"),
        process_b_pid=p3_obs_dict.get("process_b_pid"),
        process_boundary_crossed=p3_obs_dict.get("process_boundary_crossed", False),
        details={k: v for k, v in p3_obs_dict.items()
                if k not in ["status", "reason", "target_value_before",
                            "target_value_after_mutation", "target_value_in_fresh_process",
                            "saved_state_identity", "process_a_pid", "process_b_pid",
                            "process_boundary_crossed"]},
    )

    return {
        "experiment_id": experiment_id,
        "target_semantic_id": resolved_target.get("semantic_id"),
        "target_path": target_path,
        "p1_observation": p1_obs,
        "p2_observation": p2_obs,
        "p3_observation": p3_obs,
        "p1_dict": p1_obs_dict,
        "p2_dict": p2_obs_dict,
        "p3_dict": p3_obs_dict,
    }
