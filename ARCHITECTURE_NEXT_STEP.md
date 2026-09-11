# Next Step: Refactor Filter1.Cutoff Pilot

**Status**: Architecture designed and committed. NOT YET EXECUTED.

**Target**: Single Filter1.Cutoff experiment through the revised architecture.

## What to Build

### 1. Filter1.Cutoff BehaviorExperiment Spec

Create `serum2/qualification/filter_cutoff_experiment_spec.py`:

```python
from serum2.qualification.behavior_experiment import (
    BehaviorExperiment, MeasurementPlan
)

FILTER_CUTOFF_SPEC = BehaviorExperiment(
    experiment_id="filter_cutoff_pilot_revised_001",
    semantic_target="Filter1.Cutoff",
    operation="SET_PARAMETER",
    
    # Explicit context
    context={"Filter 1 On": 1.0},
    context_provenance="filter must be active for cutoff to be exercisable",
    
    # Intervention: CBOR path mutation
    treatment_cbor_path="VoiceFilter0.plainParams.kParamFreq",
    treatment_cbor_value=0.9,
    
    # Measurement plan: multi-dimensional
    measurement_plan=(
        MeasurementPlan(
            name="spectral_centroid_hz",
            kernel="spectral_centroid_hz",
            threshold=200.0,
        ),
        MeasurementPlan(
            name="overall_rms_db",
            kernel="rms_db",
            threshold=0.5,
        ),
    ),
    
    # Expected outcome
    expected_outcome="EFFECT_OBSERVED",
    expected_direction="increase",
    
    notes="Baseline: Serum default. Treatment: cutoff=0.9 (near-max). "
          "Expected: more high-frequency content → centroid increases.",
)
```

### 2. Subprocess Runner

Create `serum2/qualification/run_single_experiment.py`:

```python
import json
import subprocess
import sys
from serum2.qualification.filter_cutoff_experiment_spec import FILTER_CUTOFF_SPEC

def main():
    spec = FILTER_CUTOFF_SPEC
    spec.validate()
    
    spec_json = json.dumps(spec.to_dict())
    
    result = subprocess.run(
        [sys.executable, "-m", "serum2.qualification.experiment_worker", spec_json],
        capture_output=True,
        text=True,
    )
    
    output = json.loads(result.stdout)
    
    if output["success"]:
        print("Experiment completed successfully.")
        obs = output["behavior_observation"]
        eq = output["exercise_qualification"]
        print(f"  observation: {obs['experiment_id']}")
        print(f"  is_valid: {eq['is_valid'] if eq else 'N/A'}")
        
        # Compare to pilot
        with open("serum2/qualification/A_FILTER_CUTOFF_PILOT_EVIDENCE.json") as f:
            pilot = json.load(f)
        print(f"  pilot delta: {pilot['exercise_qualification']['causal_measurement']['delta']:.1f} Hz")
        print(f"  revised delta: {obs['measurements'][0]['delta']:.1f} Hz")
    else:
        print(f"Experiment failed: {output['error']}")
        print(output.get("traceback"))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 3. Validation

Run: `python -m serum2.qualification.run_single_experiment`

Expected success:
- BehaviorObservation produced with all dimensions
- ExerciseQualification.is_valid = True
- spectral_centroid delta approximately +2684 Hz (matching pilot)
- Serialized JSON matches the structure

## Success Condition

```
BehaviorExperiment spec
    ↓
subprocess.run(experiment_worker)
    ↓
BehaviorObservation (raw measurements)
    ↓
ExerciseQualification.is_valid = True
    ↓
JSON serialization deterministic and readable
```

When this works:
- ✓ Architecture is sound
- ✓ Worker process isolation works
- ✓ Measurement capture accurate
- ✓ Ready to expand to 11 experiments with proper context handling

## Do NOT Yet

- Run the 11-control batch
- Promote results to CapabilityContract
- Build YouTube parser
- Add production loop
- Use Ableton MCP (not needed for Serum-only experiments)

## After This Works

1. Expand to 11 experiments with explicit contexts
2. Include null-effect cases (LFO1 without destination)
3. Include conditional cases (LFO1 with destination)
4. Review measurement patterns across seed
5. Build BehaviorClaim interpretation layer
6. Only then: integrate with Ableton orchestration if needed

---

**Blocked on**: Implementation of refactored Filter1.Cutoff pilot.

**Architecture**: DONE (committed to main)

**Execution**: PENDING (next task)
