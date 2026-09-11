# 16.5.69.2-A3 Step 13: Evidence Integration — Complete

**Status:** ACCEPTANCE GATE PASSED (52/52 tests)

## Summary

Step 13 integrates P1/P2/P3 lifecycle persistence evidence into the A3 qualification layer. The work extends three key components:

1. **Evidence Extension** (`a3_evidence_extension.py`): Data structures for P1 observations
2. **EvidenceRecord Integration** (`serum2/evidence/record.py`): Carries persistence_lifecycle field
3. **Evaluator Enhancement** (`a3_evaluator.py`): Extracts P1/P2/P3 results from lifecycle evidence
4. **Harness Update** (`a3_harness.py`): Passes persistence_lifecycle to evaluator

## Files Created/Modified

### New Files
- `serum2/qualification/a3_evidence_extension.py` — P1 observation dataclass, PersistenceLifecycleEvidence, DEFAULT_PERSISTENCE_LIFECYCLE sentinel
- `serum2/qualification/a3_evidence_extension_tests.py` — 7 tests verifying P1/P2/P3 structure and independence
- `serum2/qualification/a3_evidence_record_extension_tests.py` — 7 tests verifying EvidenceRecord integration and backward compatibility
- `serum2/qualification/a3_evaluator_lifecycle_tests.py` — 9 tests verifying evaluator extracts P1/P2/P3 correctly

### Modified Files
- `serum2/evidence/record.py` — Added `persistence_lifecycle` field, updated `__getattr__` for backward compatibility
- `serum2/qualification/a3_evaluator.py` — Enhanced `evaluate_persistence()` to extract P1/P2/P3 from lifecycle, added lifecycle parameter to `evaluate_record()`
- `serum2/qualification/a3_harness.py` — Passes `persistence_lifecycle` to evaluator

## Acceptance Gate Verification

✓ **1. EvidenceRecord Extension**
   - New field: `persistence_lifecycle: Optional[PersistenceLifecycleEvidence] = None`
   - Defaults to None for new records, backward compatible with old pickled records

✓ **2. Harness Execution**
   - `qualify_plan()` extracts and passes `persistence_lifecycle` from EvidenceRecord
   - No execution engine changes; pure orchestration

✓ **3. Instance/Process Enforcement**
   - P2 carries: `fresh_instance_created`, `saved_state_identity`, `fresh_instance_identity`
   - P3 carries: `process_boundary_crossed`, `process_a_pid`, `process_b_pid`

✓ **4. Receipt Fields**
   - MutationReceipt has: `persistent_p1`, `persistent_p2`, `persistent_p3` (existing)
   - PersistenceResult has: `p1_same_engine`, `p2_new_instance`, `p3_fresh_process` (existing)

✓ **5. NOT_RUN Preservation**
   - Unexecuted lifecycles stay NOT_RUN (NOT_RUN sentinels)
   - Evaluator never synthesizes P1/P2/P3 from aggregate persistence

✓ **6. No Synthesis**
   - Evaluator only extracts what's in persistence_lifecycle
   - Does not infer P1 from P2 or P3
   - Does not infer overall from P1/P2/P3

✓ **7. Comprehensive Tests**
   - 52 total tests across all A3 layers
   - 23 new integration tests
   - All existing tests pass (no regressions)

✓ **8. Backward Compatibility**
   - Old pickled records: `__getattr__("persistence_lifecycle")` returns DEFAULT_PERSISTENCE_LIFECYCLE
   - New records: default to None, can be explicitly set
   - EvidenceRecord.to_dict() includes persistence_lifecycle field

✓ **9. Evaluator Integration**
   - `evaluate_persistence()` extracts P1/P2/P3 when lifecycle available
   - Maintains independent gate evaluation (no collapsing)
   - Backward compatible (accepts lifecycle=None)

✓ **10. Documentation**
   - Code comments explain distinction between aggregate persistence and lifecycle
   - Test names are self-documenting
   - Each gate extraction is explicit and traceable

## Architecture Summary

```
EvidenceRecord
  ├── persistence_observation (aggregate, existing)
  └── persistence_lifecycle (new, independent P1/P2/P3)
       ├── p1: P1PersistenceObservation (same-lifecycle)
       ├── p2: P2PersistenceObservation (fresh-instance)
       └── p3: P3PersistenceObservation (fresh-process)

A3 Evaluator
  ├── evaluate_persistence(persistence_observation, persistence_lifecycle)
  │   ├── overall: from persistence_observation (unchanged)
  │   ├── p1_same_engine: from persistence_lifecycle.p1
  │   ├── p2_new_instance: from persistence_lifecycle.p2
  │   └── p3_fresh_process: from persistence_lifecycle.p3
  │
  └── PersistenceResult (unchanged structure)
```

## Test Results

```
A3 H0 Synthetic Tests:           6/6  PASS
A3 Evaluator Adversarial Tests: 9/9  PASS
A3 Harness Boundary Tests:      5/5  PASS
A3 P2/P3 Lifecycle Tests:       9/9  PASS
A3 Evidence Extension Tests:    7/7  PASS
A3 EvidenceRecord Tests:        7/7  PASS
A3 Evaluator Lifecycle Tests:   9/9  PASS
────────────────────────────────────────
TOTAL:                         52/52 PASS
```

## Key Design Decisions

1. **Separate observations, not inference**: P1/P2/P3 are independently measured, not derived from one another
2. **Explicit NOT_RUN sentinels**: Unexecuted lifecycles have explicit marker objects, never None
3. **Backward compatible by default**: Old pickled records seamlessly return DEFAULT_PERSISTENCE_LIFECYCLE
4. **No aggregation**: Overall persistence status is unchanged; P1/P2/P3 are independent gates
5. **Harness-agnostic**: A3 doesn't require harness changes; it interprets what evidence.harness provides

## Ready for Step 14

Step 13 is complete and verified. The dependency chain is now:

```
ResolvedTarget → ExperimentSpec → evidence.harness.run()
  ↓
EvidenceRecord (with persistence_lifecycle)
  ↓
a3_evaluator.evaluate_record()
  ↓
MutationReceipt (with independent P1/P2/P3 gates)
```

Step 14 can now execute real P1/P2/P3 tests on H1 targets and populate persistence_lifecycle with actual results.
