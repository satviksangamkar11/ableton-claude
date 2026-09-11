"""12-control behavioral seed set qualification batch.

Runs ExerciseQualification protocol on 11 remaining high-value timbral controls
(Filter.Cutoff was the pilot, already done). Together they form the 12-control
behavioral seed set.

Each target uses the same chain:
  frozen exercise context
  -> ExperimentSpec (SINGLE_FIELD)
  -> baseline render
  -> treatment render
  -> objective measurement
  -> ExerciseQualification binding
  -> CAUSAL_VERIFIED / NO_OBSERVED_EFFECT / WRONG_DIRECTION / UNKNOWN

Two mutation adapters:
  cbor_body  - mutation applied via pathmerge to CBOR body (build_arm)
  host_param - mutation applied via baseline_host_context / mutated_host_context

For FX parameters (FXEQ, FXDistortion): the skeleton is pre-modified with a
real preset body's FXRack0 so both arms share the same FX context. Only the
specific FX parameter differs between arms.
"""

from __future__ import annotations

import copy
import json
import datetime
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from serum2 import bridge
from serum2.evidence import epoch as epoch_mod
from serum2.evidence.spec import ExperimentSpec, Mutation, SINGLE_FIELD
from serum2.evidence.exercise_qualification import make_exercise_qualification, ExerciseQualification

# Lazy-load heavy dependencies
def _get_run_behavior_test():
    from serum2.qualification.a3_behavior_harness import run_behavior_test
    return run_behavior_test

# ---------------------------------------------------------------------------
# Target definitions
# ---------------------------------------------------------------------------

@dataclass
class TargetDef:
    semantic_id: str
    experiment_id: str
    cbor_path: Optional[str]           # None = host_param adapter
    host_param_name: Optional[str]     # None = cbor_body adapter
    mutation_value: Any                # treatment value for CBOR path
    baseline_host_val: Optional[float] # for host_param adapter
    mutated_host_val: Optional[float]  # for host_param adapter
    exercise_context: List[Tuple[str, float]]  # shared both arms
    metric: str
    expected_direction: str
    effect_threshold: Optional[float]
    notes: str = ""
    fx_preset_path: Optional[str] = None  # if set, load this preset's FXRack0 into skeleton


ALTAR_PRESET = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Altar.SerumPreset"

TARGETS: List[TargetDef] = [

    # 1. Filter1.Resonance
    # Low cutoff + filter on → resonance peak at the cutoff frequency is audible
    # High resonance raises RMS significantly (self-oscillation effect)
    TargetDef(
        semantic_id="Filter1.Resonance",
        experiment_id="filter1_reso_pilot_001",
        cbor_path="VoiceFilter0.plainParams.kParamReso",
        host_param_name=None,
        mutation_value=0.9,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[("Filter 1 On", 1.0), ("Filter 1 Freq", 0.15)],
        metric="overall_rms_db",
        expected_direction="increase",
        effect_threshold=0.5,
        notes="Low cutoff (0.15) makes resonance peak audible. High reso -> self-osc peak adds energy.",
    ),

    # 2. Filter2.Cutoff
    # Same principle as Filter1.Cutoff: higher cutoff passes more highs -> centroid up
    TargetDef(
        semantic_id="Filter2.Cutoff",
        experiment_id="filter2_cutoff_pilot_001",
        cbor_path="VoiceFilter1.plainParams.kParamFreq",
        host_param_name=None,
        mutation_value=0.9,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[("Filter 2 On", 1.0)],
        metric="spectral_centroid_hz",
        expected_direction="increase",
        effect_threshold=200.0,
        notes="Filter 2 must be active. Treatment=0.9 passes much more high-frequency content.",
    ),

    # 3. OSC1.Level
    # Direct level control: 0.25 baseline -> 1.0 treatment. Always active, no context needed.
    # Metric: RMS increases with higher level.
    TargetDef(
        semantic_id="OSC1.Level",
        experiment_id="osc1_level_pilot_001",
        cbor_path=None,
        host_param_name="A Level",
        mutation_value=None,
        baseline_host_val=0.25,
        mutated_host_val=1.0,
        exercise_context=[],
        metric="overall_rms_db",
        expected_direction="increase",
        effect_threshold=1.0,
        notes="OSC A always active. 0.25->1.0 is a large amplitude change.",
    ),

    # 4. OSC1.Fine (OSC1 pitch detune via fine tune)
    # Fine pitch shift of OSC A. Raising fine tune to 1.0 = +100 cents = +1 semitone.
    # All harmonics shift up -> spectral centroid increases.
    # Default: VoiceOsc0.plainParams.kParamFine absent (0 cents offset)
    # Treatment: kParamFine = 1.0 (+100 cents)
    TargetDef(
        semantic_id="OSC1.Detune",
        experiment_id="osc1_fine_pilot_001",
        cbor_path="VoiceOsc0.plainParams.kParamFine",
        host_param_name=None,
        mutation_value=1.0,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[],
        metric="spectral_centroid_hz",
        expected_direction="increase",
        effect_threshold=50.0,
        notes="A Fine (index 25). Treatment=1.0 shifts OSC A up 100 cents. All harmonics shift up.",
    ),

    # 5. OSC2.Fine (OSC2 pitch detune via fine tune)
    TargetDef(
        semantic_id="OSC2.Detune",
        experiment_id="osc2_fine_pilot_001",
        cbor_path="VoiceOsc1.plainParams.kParamFine",
        host_param_name=None,
        mutation_value=1.0,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[("B Enable", 1.0)],
        metric="spectral_centroid_hz",
        expected_direction="increase",
        effect_threshold=50.0,
        notes="B Fine (index 80). OSC B must be enabled. Treatment=1.0 shifts up 100 cents.",
    ),

    # 6. Env1.Attack
    # Slow attack (0.9) means the sound takes a long time to reach peak volume.
    # In a 2s render, slow attack => less total energy than instant attack.
    # Metric: RMS. Baseline = default (fast attack), treatment = 0.9 (very slow).
    TargetDef(
        semantic_id="Env1.Attack",
        experiment_id="env1_attack_pilot_001",
        cbor_path="Env0.plainParams.kParamAttack",
        host_param_name=None,
        mutation_value=0.9,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[],
        metric="overall_rms_db",
        expected_direction="decrease",
        effect_threshold=0.5,
        notes="Env0 = Env1 in UI (0-indexed). Slow attack=0.9 reduces energy in 2s render window.",
    ),

    # 7. Env1.Release
    # Long release (0.9) means sound persists after note-off.
    # Note: 0.5s, render: 2.0s. Last 1.5s: baseline silent, treatment has tail.
    # Metric: overall_rms_db. Treatment has more total energy.
    TargetDef(
        semantic_id="Env1.Release",
        experiment_id="env1_release_pilot_001",
        cbor_path="Env0.plainParams.kParamRelease",
        host_param_name=None,
        mutation_value=0.9,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[],
        metric="overall_rms_db",
        expected_direction="increase",
        effect_threshold=0.5,
        notes="Long release makes sound persist 1.5s after note-off in 2s render.",
    ),

    # 8. LFO1.Rate
    # LFO1 rate without a modulation target -> expected NO_OBSERVED_EFFECT.
    # This is a valid result: it tells us LFO.Rate requires an active modulation to be exercisable.
    # The ExerciseQualification will be is_valid=False (NO_OBSERVED_EFFECT, not EFFECT_OBSERVED).
    # Documenting this finding is useful for the behavioral vocabulary.
    TargetDef(
        semantic_id="LFO1.Rate",
        experiment_id="lfo1_rate_pilot_001",
        cbor_path="LFO0.plainParams.kParamRate",
        host_param_name=None,
        mutation_value=0.9,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[],
        metric="overall_rms_db",
        expected_direction="change",
        effect_threshold=0.5,
        notes="Without a modulation target, LFO rate has no audible effect. "
              "Expected NO_OBSERVED_EFFECT — valid finding: needs modulation assignment context.",
    ),

    # 9. Filter1.Drive
    # Drive adds saturation/harmonics. More drive -> more energy, brighter.
    # Exercise context: filter must be on so drive is in the signal path.
    TargetDef(
        semantic_id="Filter1.Drive",
        experiment_id="filter1_drive_pilot_001",
        cbor_path="VoiceFilter0.plainParams.kParamDrive",
        host_param_name=None,
        mutation_value=0.9,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[("Filter 1 On", 1.0)],
        metric="overall_rms_db",
        expected_direction="increase",
        effect_threshold=0.5,
        notes="Filter drive adds saturation. Filter must be on. High drive adds energy/harmonics.",
    ),

    # 10. OSC2.Level
    TargetDef(
        semantic_id="OSC2.Level",
        experiment_id="osc2_level_pilot_001",
        cbor_path=None,
        host_param_name="B Level",
        mutation_value=None,
        baseline_host_val=0.0,
        mutated_host_val=1.0,
        exercise_context=[("B Enable", 1.0)],
        metric="overall_rms_db",
        expected_direction="increase",
        effect_threshold=1.0,
        notes="OSC B must be enabled. 0.0->1.0 level is a full amplitude change.",
    ),

    # 11. FXEQ.Freq1
    # Uses Altar preset FXRack0 (has FXEQ at FX[0], Freq1=56.06 Hz).
    # Treatment: push Freq1 to 8000 Hz. Large frequency shift changes spectral balance.
    # Both arms share the same FXRack0 (pre-injected into skeleton).
    TargetDef(
        semantic_id="FXEQ.Freq1",
        experiment_id="fxeq_freq1_pilot_001",
        cbor_path="FXRack0.FX.0.FXEQ.plainParams.kParamFreq1",
        host_param_name=None,
        mutation_value=8000.0,
        baseline_host_val=None,
        mutated_host_val=None,
        exercise_context=[],
        metric="spectral_centroid_hz",
        expected_direction="change",
        effect_threshold=200.0,
        notes="Altar preset FXRack0 injected (FX[0]=FXEQ, Freq1 baseline=56.06 Hz). "
              "Treatment=8000 Hz. EQ shelving/peaking at very different frequency.",
        fx_preset_path=ALTAR_PRESET,
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _build_spec(t: TargetDef) -> ExperimentSpec:
    """Build ExperimentSpec. Empty mutations for host_param adapter."""
    if t.cbor_path is not None:
        mutations = [
            Mutation(
                target_path=t.cbor_path,
                value=t.mutation_value,
                provenance="behavioral_seed_batch",
            )
        ]
    else:
        mutations = []

    return ExperimentSpec(
        experiment_id=t.experiment_id,
        mutations=mutations,
        prerequisites=[],
        isolation_level=SINGLE_FIELD,
        claim_subject=t.semantic_id,
        claim_predicate="causal_behavior",
    )


def _load_fx_skeleton(base_skeleton: tuple, preset_path: str) -> tuple:
    """Inject FXRack0 from a preset into the base skeleton. Returns modified skeleton."""
    from serum2 import codec
    _, preset_body = codec.load_preset_file(preset_path)
    meta = copy.deepcopy(base_skeleton[0])
    body = copy.deepcopy(base_skeleton[1])
    body["FXRack0"] = copy.deepcopy(preset_body["FXRack0"])
    return (meta, body)


def run_one(t: TargetDef, skeleton: tuple, verbose: bool = True) -> dict:
    """Run one ExerciseQualification pilot. Returns result dict."""
    if verbose:
        print("\n  [{}]  {}".format(t.experiment_id, t.semantic_id))
        print("  adapter: {}".format("host_param" if t.cbor_path is None else "cbor_body"))
        print("  metric:  {}".format(t.metric))
        print("  expected: {}".format(t.expected_direction))
        if t.exercise_context:
            print("  exercise_context: {}".format(t.exercise_context))

    # Possibly inject FX preset body
    active_skeleton = skeleton
    if t.fx_preset_path:
        active_skeleton = _load_fx_skeleton(skeleton, t.fx_preset_path)
        if verbose:
            print("  fx_preset: {}".format(os.path.basename(t.fx_preset_path)))

    spec = _build_spec(t)

    # For host_param adapter, arm-specific contexts carry the mutation
    baseline_host_ctx = list(t.exercise_context)
    mutated_host_ctx = list(t.exercise_context)

    if t.cbor_path is None:
        # host_param adapter: differ only in the one param value
        baseline_host_ctx = list(t.exercise_context) + [(t.host_param_name, t.baseline_host_val)]
        mutated_host_ctx = list(t.exercise_context) + [(t.host_param_name, t.mutated_host_val)]
        exercise_ctx = []
    else:
        # cbor_body adapter: exercise_context shared, arm contexts identical
        exercise_ctx = list(t.exercise_context)
        baseline_host_ctx = []
        mutated_host_ctx = []

    run_behavior_test = _get_run_behavior_test()

    behavior_result = run_behavior_test(
        experiment_id=t.experiment_id,
        target_path=t.cbor_path or t.host_param_name,
        mutation_value=t.mutation_value if t.cbor_path else t.mutated_host_val,
        skeleton=active_skeleton,
        spec=spec,
        expected_direction=t.expected_direction,
        metric_name=t.metric,
        effect_threshold=t.effect_threshold,
        exercise_context=exercise_ctx,
        baseline_host_context=baseline_host_ctx,
        mutated_host_context=mutated_host_ctx,
    )

    if verbose:
        status = behavior_result.get("status", "UNKNOWN")
        baseline = behavior_result.get("baseline_metric")
        mutated = behavior_result.get("mutated_metric")
        unit = "Hz" if "centroid" in t.metric else "dB"
        print("  status: {}".format(status))
        if baseline is not None and mutated is not None:
            delta = mutated - baseline
            print("  baseline: {:.1f} {}".format(baseline, unit))
            print("  mutated:  {:.1f} {}".format(mutated, unit))
            print("  delta:    {:+.1f} {}".format(delta, unit))
        if behavior_result.get("error_traceback"):
            print("  ERROR:", behavior_result.get("reason"))

    # Build ExerciseQualification
    frozen_ctx = dict(t.exercise_context)
    if t.cbor_path is None:
        # Record the contrast for host_param case
        frozen_ctx["_baseline_{}".format(t.host_param_name)] = t.baseline_host_val
        frozen_ctx["_mutated_{}".format(t.host_param_name)] = t.mutated_host_val

    eq = make_exercise_qualification(
        target_semantic_id=t.semantic_id,
        target_cbor_path=t.cbor_path or "host_param:{}".format(t.host_param_name),
        frozen_context=frozen_ctx,
        mutation_value=t.mutation_value if t.cbor_path else t.mutated_host_val,
        experiment_id=t.experiment_id,
        behavior_result=behavior_result,
    )

    if verbose:
        print("  is_valid: {}".format(eq.is_valid))

    acceptance = {
        "baseline_rendered": bool(behavior_result.get("baseline_rendered")),
        "mutated_rendered": bool(behavior_result.get("mutated_rendered")),
        "single_field_isolation": eq.isolation_level == SINGLE_FIELD,
        "effect_observed": eq.causal_measurement.status == "EFFECT_OBSERVED",
        "exercise_qualification_valid": eq.is_valid,
    }
    chain_valid = all(acceptance.values())

    return {
        "semantic_id": t.semantic_id,
        "experiment_id": t.experiment_id,
        "exercise_qualification": eq,
        "behavior_result": behavior_result,
        "acceptance": acceptance,
        "chain_valid": chain_valid,
        "notes": t.notes,
    }


def run_batch(verbose: bool = True) -> List[dict]:
    """Run all 11 remaining pilots. Returns list of result dicts.

    Captures skeleton fresh for each target to avoid resource accumulation.
    """
    import gc

    if verbose:
        print("\n" + "=" * 70)
        print("BEHAVIORAL SEED BATCH — 11 REMAINING TARGETS")
        print("=" * 70)

    results = []
    for i, t in enumerate(TARGETS):
        gc.collect()
        if verbose:
            print("\n[{}/{}] Capturing skeleton and running {}".format(
                i + 1, len(TARGETS), t.semantic_id))

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        r = run_one(t, skeleton, verbose=verbose)
        results.append(r)

        # Cleanup
        del skeleton
        gc.collect()

    return results


def save_batch_evidence(results: List[dict], out_path: str = None) -> str:
    if out_path is None:
        out_path = os.path.join(
            os.path.dirname(__file__),
            "A_BEHAVIORAL_SEED_BATCH_EVIDENCE.json",
        )

    summary = []
    for r in results:
        eq = r["exercise_qualification"]
        br = r["behavior_result"]
        unit = "Hz" if "centroid" in (br.get("metric_name") or "") else "dB"
        summary.append({
            "semantic_id": r["semantic_id"],
            "experiment_id": r["experiment_id"],
            "chain_valid": r["chain_valid"],
            "status": br.get("status"),
            "baseline_metric": br.get("baseline_metric"),
            "mutated_metric": br.get("mutated_metric"),
            "delta": br.get("delta"),
            "metric": br.get("metric_name"),
            "unit": unit,
            "observed_direction": br.get("observed_direction"),
            "exercise_qualification_valid": eq.is_valid,
            "scope": eq.scope,
            "notes": r.get("notes", ""),
        })

    payload = {
        "batch": "12-Control Behavioral Seed Set",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "filter_cutoff_pilot": "serum2/qualification/A_FILTER_CUTOFF_PILOT_EVIDENCE.json",
        "targets_attempted": len(results),
        "chain_valid_count": sum(1 for r in results if r["chain_valid"]),
        "summary": summary,
        "full_results": [
            {
                "semantic_id": r["semantic_id"],
                "exercise_qualification": r["exercise_qualification"].to_dict(),
                "behavior_result_raw": {
                    k: v for k, v in r["behavior_result"].items()
                    if k not in ("error_traceback",)
                },
                "acceptance": r["acceptance"],
            }
            for r in results
        ],
    }

    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return out_path


def print_matrix(results: List[dict]) -> None:
    print("\n" + "=" * 70)
    print("BEHAVIORAL SEED MATRIX (11 targets)")
    print("=" * 70)
    print("{:<20} {:<20} {:>8} {:<8} {:<10}".format(
        "target", "status", "delta", "unit", "valid"))
    print("-" * 70)

    # Include the pilot result for display
    print("{:<20} {:<20} {:>8} {:<8} {:<10}".format(
        "Filter.Cutoff", "CAUSAL_VERIFIED", "+2684", "Hz", "True"))

    for r in results:
        br = r["behavior_result"]
        eq = r["exercise_qualification"]
        metric = br.get("metric_name", "")
        unit = "Hz" if "centroid" in metric else "dB"
        delta_raw = br.get("delta")
        delta_str = "{:+.0f}".format(delta_raw) if delta_raw is not None else "N/A"
        print("{:<20} {:<20} {:>8} {:<8} {:<10}".format(
            r["semantic_id"],
            br.get("status", "UNKNOWN"),
            delta_str,
            unit,
            str(eq.is_valid),
        ))

    valid_count = sum(1 for r in results if r["exercise_qualification"].is_valid)
    print("-" * 70)
    print("Chain valid (including pilot): {}/12".format(valid_count + 1))


if __name__ == "__main__":
    results = run_batch(verbose=True)
    print_matrix(results)
    path = save_batch_evidence(results)
    print("\nEvidence saved to: {}".format(path))
