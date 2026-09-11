# A3 P1/P2/P3 Lifecycle Qualification Specification

## Current State

The evidence harness provides a single aggregate `persistence_observation`:

```json
{
  "status": "PASS" | "FAIL" | "NOT_RUN",
  "checked": true,
  "exact_match": true | false,
  "detail": { "target_path": true | false }
}
```

This observation does **not** distinguish between:
- P1: Resave/reload in same lifecycle
- P2: Fresh instance after save
- P3: Fresh process after save

Therefore, in the current architecture:

```python
receipt.persistent_p1 = NOT_RUN  # Not separately established
receipt.persistent_p2 = NOT_RUN  # Not separately established
receipt.persistent_p3 = NOT_RUN  # Not separately established
receipt.persistence.overall.status  # Single aggregate result only
```

## Required Extension

To close Step 12, the evidence harness must be extended to produce **three independent observations**:

### P1 Observation: Same-Lifecycle Persistence

```python
P1_OBSERVATION = {
    "name": "p1_same_lifecycle",
    "sequence": [
        ("baseline_state", {...}),
        ("mutate_target", {...}),
        ("verify_mutation", True),
        ("save_state", "artifact_1"),
        ("reload_state", "artifact_1"),  # SAME instance
        ("inspect_target", {...}),
    ],
    "result": {
        "status": "PASS" | "FAIL",
        "target_persisted": True | False,
        "value_match": True | False,
        "detail": { "target_path": <actual_value> }
    }
}
```

**Test contract:**
- Mutate target in Serum instance
- Verify mutation is present
- Save state
- Reload state into **same Serum instance**
- Inspect whether target retained its mutated value
- Result: PASS if target=mutated_value, FAIL otherwise

### P2 Observation: Fresh-Instance Persistence

```python
P2_OBSERVATION = {
    "name": "p2_fresh_instance",
    "sequence": [
        ("instance_1_baseline", {...}),
        ("instance_1_mutate", {...}),
        ("instance_1_verify", True),
        ("save_state", "artifact_2"),
        ("destroy_instance_1", None),
        ("create_instance_2", None),
        ("load_artifact_2", None),
        ("inspect_target_instance_2", {...}),
    ],
    "result": {
        "status": "PASS" | "FAIL",
        "target_persisted": True | False,
        "value_match": True | False,
        "detail": { "target_path": <actual_value> }
    }
}
```

**Test contract:**
- Mutate target in Serum instance A
- Verify mutation is present in A
- Save state to artifact
- Destroy instance A
- Create new instance B
- Load artifact into instance B
- Inspect whether target retained its value in B
- Result: PASS if target=mutated_value in B, FAIL otherwise

### P3 Observation: Fresh-Process Persistence

```python
P3_OBSERVATION = {
    "name": "p3_fresh_process",
    "sequence": [
        ("process_a_baseline", {...}),
        ("process_a_mutate", {...}),
        ("process_a_verify", True),
        ("process_a_save", "artifact_3"),
        ("process_a_terminate", None),
        ("process_b_start", None),
        ("process_b_load_artifact_3", None),
        ("process_b_inspect", {...}),
    ],
    "result": {
        "status": "PASS" | "FAIL",
        "target_persisted": True | False,
        "value_match": True | False,
        "detail": { "target_path": <actual_value> }
    }
}
```

**Test contract:**
- Process A: Mutate target in Serum
- Process A: Verify mutation
- Process A: Save state
- Process A: Exit
- Process B (fresh Python process): Load artifact
- Process B: Inspect target
- Result: PASS if target=mutated_value, FAIL otherwise

## H1 Pilot Expected Results

Based on H1 overall persistence observation:

### OSC1.Enable
```
overall_persistence = FAIL
→ Likely: P1 = FAIL, P2 = FAIL, P3 = FAIL
   (if mutation doesn't survive any lifecycle reload)

or:

→ Possible: P1 = PASS, P2 = FAIL, P3 = ?
   (survives reload in same instance but not fresh instance)
```

### Filter.Type
```
overall_persistence = PASS
→ Likely: P1 = PASS, P2 = PASS, P3 = PASS
   (persists across all lifecycle transitions)
```

### Filter.Resonance
```
overall_persistence = PASS
→ Likely: P1 = PASS, P2 = PASS, P3 = PASS
   (persists across all lifecycle transitions)
```

## Independence Guarantee

**Critical invariant:**
```
P1 result does NOT imply P2 result
P2 result does NOT imply P3 result
overall result does NOT imply P1/P2/P3
```

Each lifecycle must be independently observed.

## Implementation Path

Step 12 requires:

1. **Extend evidence.harness.run()** to separately establish P1/P2/P3 observations
   - Current: single persistence_observation
   - New: p1_observation, p2_observation, p3_observation

2. **Update EvidenceRecord schema** to store three independent results

3. **Update a3_evaluator.evaluate_persistence()** to:
   - Extract P1/P2/P3 from separate observations
   - Leave them NOT_RUN if evidence not provided
   - Never infer one from another

4. **Re-run H1 targets** with extended harness
   - OSC1.Enable (expecting P1 failure)
   - Filter.Type (expecting all PASS)
   - Filter.Resonance (expecting all PASS)

5. **Verify independence** through the matrix
   - No P1→P2 propagation
   - No overall→P1/P2/P3 propagation
   - BOOLEAN anomaly remains an empirical finding

## After Step 12

MutationReceipt will carry:

```python
receipt.persistent_p1 = PASS | FAIL | NOT_RUN  # Independent
receipt.persistent_p2 = PASS | FAIL | NOT_RUN  # Independent
receipt.persistent_p3 = PASS | FAIL | NOT_RUN  # Independent
receipt.persistence.overall.status              # Aggregate (if still needed)
```

This closes the persistence dimension of the qualification kernel and enables Step 13 (restoration + behavior).

