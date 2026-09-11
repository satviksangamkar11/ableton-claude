# A3 — Mutation Qualification Specification

**Phase:** 16.5.69.2 / A3  
**Gate:** Phase 1 QUALIFIED (RESOLVED_TARGET_REGISTRY.json, 11 targets)  
**Status:** SPECIFICATION (not yet executed)

---

## Purpose

Establish that for each `ResolvedTarget`:
1. DawDreamer can mutate the parameter to intended values (GENERATION)
2. Mutations survive process/instance boundaries (PERSISTENCE)
3. Mutations produce expected audio effects (BEHAVIOR)
4. Mutations do not unexpectedly change other state (COLLATERAL)

A3 does NOT claim "parameter X is now production-ready." It claims: "Our qualification pipeline correctly identifies whether parameter X meets these four gates."

---

## Pipeline Architecture

```
RESOLVED_TARGET_REGISTRY
       ↓
A3-H0: Harness Self-Test
       ↓ (if H0 PASS)
A3-H1: 3-Target Pilot
       ├─ 1 BOOLEAN
       ├─ 1 ENUM
       └─ 1 SCALAR
       ↓ (if H1 PASS)
A3-Expanded: Remaining 8 targets
       ↓
MUTATION_QUALIFICATION_REPORT
```

---

## A3-H0 — Harness Self-Test

**Purpose:** Verify the qualification machinery itself before using it on real targets.

**Test Cases (intentional):**

### H0.1 — Known Good Mutation
- Target: OSC1.Volume (SCALAR, 0.0–1.0)
- Requested: 0.75 semantic → 0.75 VST3 transport
- Expected: parameter changes to 0.75, no collateral
- **Harness should report:** GENERATION PASS, PERSISTENCE all-levels PASS, BEHAVIOR CAUSAL_VERIFIED

### H0.2 — Known Bad Target (Invalid VST3 Index)
- Target: synthetic, index 99999 (doesn't exist)
- Requested: 0.5
- Expected: mutation fails, readback unchanged, explicit error
- **Harness should report:** GENERATION FAIL, reason "VST3 index not found", no persistence attempted

### H0.3 — Out-of-Range Value
- Target: OSC1.Volume (min 0.0, max 1.0)
- Requested: 2.0
- Expected: DawDreamer clamps/rejects, readback shows clamped value
- **Harness should report:** GENERATION PASS (clamped), READBACK 1.0 (or documented clamp behavior)

### H0.4 — Ambiguous Target (Simulated)
- Target: deliberately constructed to test resolver identity verification
- Expected: harness rejects with explicit ambiguity error
- **Harness should report:** GENERATION FAIL, reason "ambiguous target identity"

### H0.5 — Persistence Failure (Simulated)
- Target: modified to simulate process death between capture and readback
- Expected: harness detects state mismatch, downgrades persistence levels
- **Harness should report:** P1 PASS, P2 FAIL, P3 FAIL (specific levels, not collapsed)

### H0.6 — Collateral Mutation (Intentional)
- Target: parameter known to couple with another (if any exist in test set)
- Expected: harness detects state change in coupled parameter
- **Harness should report:** COLLATERAL EXPECTED_COUPLED, with coupled_parameter listed

**H0 Gate:** ALL test cases must produce expected harness output (not necessarily all PASS, but all correctly labeled).

If H0 fails: harness has bugs, do not proceed to H1 or H1-Expanded.

---

## A3-H1 — 3-Target Pilot

**Targets (one representative of each transport kind):**

| Transport | Semantic ID | Target | Domain | Test Values |
|-----------|-------------|--------|--------|------------|
| BOOLEAN | OSC1.Enable | A Enable | {0, 1} | off, on |
| ENUM | OSC1.Octave | A Octave | {0..8} | first, middle, last |
| SCALAR | Env1.Attack | Env 1 Attack | [0.0, 1.0] | 0.0, 0.5, 1.0 |

For each:

### A3.1 — Baseline

**Capture:**
```
baseline_state = {
  complete Serum state (V8 chunk),
  target_parameter_value,
  render 4 bars silence,
  measure baseline audio (RMS, spectral)
}
```

**Requirement:** Baseline must be reproducible (same input → same output, within floating-point tolerance).

### A3.2 — Mutation Recipe

**Define test vectors in both semantic and transport domains:**

For OSC1.Enable (BOOLEAN):
```json
{
  "semantic_domain": ["off", "on"],
  "test_vectors": [
    {
      "semantic_value": "on",
      "transport_value": 1.0,
      "description": "enable oscillator"
    }
  ]
}
```

For OSC1.Octave (ENUM):
```json
{
  "semantic_domain": ["0", "1", "2", ..., "8"],
  "test_vectors": [
    {
      "semantic_value": "4",
      "transport_value": 4/8,
      "description": "middle octave"
    },
    {
      "semantic_value": "8",
      "transport_value": 1.0,
      "description": "highest octave"
    }
  ]
}
```

For Env1.Attack (SCALAR):
```json
{
  "semantic_domain": "[0.0, 1.0]",
  "test_vectors": [
    {
      "semantic_value": 0.5,
      "transport_value": 0.5,
      "description": "mid-range attack time"
    }
  ]
}
```

### A3.3 — Generation Qualification

**Procedure:**
1. Apply mutation via DawDreamer: `set_parameter(vst3_index, transport_value)`
2. Readback: `get_parameter(vst3_index)`
3. Verify:
   - Readback matches requested value (within tolerance)
   - Correct parameter changed (resolver identity verified)
   - No silent substitution (e.g. wrong parameter index)

**Result Classification:**
```
GENERATION_PASS:
  ✓ requested == readback
  ✓ target identity verified
  ✓ no unexpected mutation

GENERATION_FAIL:
  ✗ readback != requested
  ✗ target identity mismatch
  ✗ unexpected target substituted
```

### A3.4 — Persistence Qualification

Three separate tests, not collapsed:

**P1 — Same Engine Reload**
```
mutated_state = baseline + mutation
save(mutated_state)
reload(mutated_state, same_process)
readback(target_parameter)
compare(readback, mutated_value)
```

Result: `PASS` | `FAIL`

**P2 — New Serum Instance (Same Process)**
```
mutated_state = baseline + mutation
save(mutated_state)
destroy(serum_instance)
new_serum_instance = DawDreamer(...)
load(mutated_state)
readback(target_parameter)
compare(readback, mutated_value)
```

Result: `PASS` | `FAIL`

**P3 — Fresh Process**
```
mutated_state = baseline + mutation
save(mutated_state)
exit_process()
spawn_new_process()
new_dawdreamer = DawDreamer(...)
load(mutated_state)
readback(target_parameter)
compare(readback, mutated_value)
```

Result: `PASS` | `FAIL`

**Reporting:**
```json
{
  "persistence": {
    "P1_same_engine": "PASS",
    "P2_new_instance": "PASS",
    "P3_fresh_process": "FAIL",
    "interpretation": "mutation survives reload but not process boundary"
  }
}
```

Do NOT collapse to single boolean.

### A3.5 — Behavioral Qualification

**Per-target measurement recipe:**

| Target | Measurement | Expected Effect |
|--------|-------------|-----------------|
| OSC1.Enable | RMS (silence vs sound) | ENABLE=0 → silent, ENABLE=1 → sound |
| OSC1.Octave | Spectral fundamental | octave shift doubles/halves frequency |
| Env1.Attack | Envelope rise time | attack=0 → instant, attack=1 → slow |

**Procedure:**
1. Render 4 bars with mutation
2. Apply target-specific measurement
3. Compare to baseline
4. Classify:
   - `CAUSAL_VERIFIED`: effect observed, magnitude reasonable, direction correct
   - `NO_OBSERVED_EFFECT`: parameter changed, but no measurable audio difference
   - `INCONCLUSIVE`: measurement noisy or direction ambiguous
   - `UNKNOWN`: measurement not applicable (e.g. UI-only parameter)

**Reporting:**
```json
{
  "behavior": {
    "status": "CAUSAL_VERIFIED",
    "measurement_kind": "spectral_fundamental",
    "baseline": 440.0,
    "after_mutation": 880.0,
    "change_magnitude": "octave_up",
    "confidence": 0.95
  }
}
```

### A3.6 — Collateral Qualification

**Procedure:**
1. Capture complete state after mutation (all 2,623 parameters)
2. Diff against baseline
3. Classify each change:
   - `INTENDED`: target parameter (expected)
   - `EXPECTED_COUPLED`: documented parameter coupling
   - `UNEXPECTED`: unplanned state change

**Reporting:**
```json
{
  "collateral": {
    "status": "PASS",
    "total_changes": 1,
    "expected_changes": 1,
    "unexpected_changes": 0,
    "details": [
      {
        "parameter": "A Octave",
        "baseline": 4,
        "after": 8,
        "classification": "INTENDED"
      }
    ]
  }
}
```

---

## Mutation Receipt (Machine-Readable)

Every A3 operation produces a receipt:

```json
{
  "receipt_version": "1.0",
  "timestamp": "2026-09-11T03:45:00Z",
  
  "target": {
    "semantic_id": "osc1.octave",
    "capability_key": "oscillator_field_OSC-OCTAVE",
    "vst3_name": "A Octave",
    "vst3_index": 23
  },
  
  "test_vector": {
    "semantic_value": 4,
    "semantic_domain": "[0..8]",
    "transport_value": 0.5,
    "transport_domain": "[0.0, 1.0]"
  },
  
  "generation": {
    "status": "PASS",
    "requested": 0.5,
    "readback": 0.5,
    "target_identity_verified": true,
    "issues": []
  },
  
  "persistence": {
    "P1_same_engine": "PASS",
    "P2_new_instance": "PASS",
    "P3_fresh_process": "PASS"
  },
  
  "behavior": {
    "status": "CAUSAL_VERIFIED",
    "measurement_kind": "spectral_fundamental",
    "baseline_measurement": 440.0,
    "after_measurement": 880.0,
    "effect_magnitude": "octave_up",
    "confidence": 0.95
  },
  
  "collateral": {
    "status": "PASS",
    "unexpected_changes": 0
  },
  
  "gates": {
    "generation": "PASS",
    "persistence_all_levels": "PASS",
    "behavior": "CAUSAL_VERIFIED",
    "collateral": "PASS",
    "overall": "QUALIFIED"
  }
}
```

This receipt feeds directly into the evidence/claim machinery (not reinterpretation of logs).

---

## Execution Order

1. ✅ Phase 1 complete (RESOLVED_TARGET_REGISTRY.json ready)
2. ⏳ Build A3 harness machinery (not yet done)
3. ⏳ Run A3-H0 (harness self-test)
4. ⏳ Run A3-H1 (3-target pilot)
5. ⏳ Review A3-H1 receipts
6. ⏳ If H1 PASS: run A3-Expanded (remaining 8 targets)
7. ⏳ Produce MUTATION_QUALIFICATION_REPORT

---

## Non-Goals for A3

- Declare "DawDreamer is production-ready"
- Prove 11/11 targets are universally applicable
- Establish that these 11 targets are the final semantic inventory
- Claim the reverse VST3→semantic audit is complete

A3's goal is singular: prove that our qualification machinery (harness + receipts + gates) correctly distinguishes which targets meet each gate, so that we can confidently run it on future targets and trust the result.

---

## See Also

- `RESOLVED_TARGET_REGISTRY.json` — A3 input
- `A3_PILOT_TARGETS.json` — H1 test configuration (3-target)
- `MUTATION_RECEIPT_SCHEMA.json` — machine-readable format
- ROADMAP.md 16.5.69.2 — linked execution plan
