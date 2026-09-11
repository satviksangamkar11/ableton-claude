# A3 H1 ENUM Audit — Step 3 (ENUM variant)

**Experiment:** A3-H1-ENUM-FILTER-TYPE  
**Semantic Target:** Filter.Type  
**Mutation Value:** "BP12" (enum, not numeric)  
**Execution Date:** 2026-09-11  
**Status:** INFRASTRUCTURE PASS, PERSISTENCE PASS  

---

## Identity Verification Checklist

### Semantic Identity
- [x] semantic_id correct: `Filter.Type` ✓
- [x] capability_key correct: `filter_field_type` ✓

### VST3 Identity (Explicit)
- [x] vst3_name: `Filter 1 Type` ✓
- [x] vst3_index: `204` (explicit, from resolved registry) ✓
- [x] Index NOT inferred from state path ✓

### Experiment Specification
- [x] experiment_id: `A3-H1-ENUM-FILTER-TYPE` ✓
- [x] state_path: `VoiceFilter0.plainParams.kParamType` ✓
- [x] mutation value: `"BP12"` (string enum, not numeric) ✓
- [x] isolation_level: `single_field` ✓
- [x] provenance: `A3_H1_PILOT` ✓

---

## Generation Gate — **PASS** ✓

**Reason:** "State observation matches declared mutation intent."

**Details:**
- `top_level_ok`: true ✓
- `fine_grained_ok`: true ✓
- `diff_keys`: ["VoiceFilter0"] (correct scope)

**Interpretation:** The enum mutation was successfully applied. The state field `VoiceFilter0.plainParams.kParamType` changed to the declared value "BP12". No numeric misinterpretation occurred.

---

## Collateral Gate — **PASS** ✓

**Reason:** "Observed state diff contains only the declared mutation target(s)."

**Details:**
- `diff_keys`: ["VoiceFilter0"]
- `intended_targets`: ["VoiceFilter0.plainParams.kParamType"]

**Interpretation:** Only the declared enum parameter changed. No collateral mutations. SINGLE_FIELD isolation respected.

---

## Behavior Gate — **NOT_RUN**

**Reason:** "No causal measurements were recorded."

**Status:** EXPECTED for this stage.

---

## Persistence Gate — **PASS** ✓

**Overall Status:** PASS

**Reason:** "Persistence check passed (resave/load identity match)."

**Details:**
```json
{
  "status": "PASS",
  "checked": true,
  "exact_match": true,
  "detail": {
    "VoiceFilter0.plainParams.kParamType": true
  }
}
```

**Interpretation:**
- The mutation WAS generated (generation = PASS)
- After save/load cycle, the value was correctly restored
- The enum persisted: "BP12" survived serialization

**Contrast with BOOLEAN:**
```
BOOLEAN (OSC1.Enable):
  generation = PASS
  persistence = FAIL     ← value did not survive save/load

ENUM (Filter.Type):
  generation = PASS
  persistence = PASS     ← value correctly restored
```

This is a real difference, not a measurement artifact. Serum correctly serializes the Filter.Type enum but not the OSC1.Enable boolean.

---

## P1/P2/P3 Lifecycle Gates — **ALL NOT_RUN** ✓

- `p1_same_engine`: NOT_RUN ✓
- `p2_new_instance`: NOT_RUN ✓
- `p3_fresh_process`: NOT_RUN ✓

**Status:** EXPECTED and CORRECT. Not fabricated.

---

## Restoration Gate — **NOT_RUN** ✓

**Status:** EXPECTED. Formal restoration qualification not yet built.

---

## Derived Claims (Narrow)

```
transport_mutable:      true     (generation PASS)
generation_verified:    true     (generation PASS)
persistent_p1:          false    (p1 NOT_RUN)
persistent_p2:          false    (p2 NOT_RUN)
persistent_p3:          false    (p3 NOT_RUN)
collateral_safe:        true     (collateral PASS)
behavior_verified:      false    (behavior NOT_RUN)
```

---

## Infrastructure Audit Summary

| Criterion | Result | Status |
|-----------|--------|--------|
| Semantic identity correct | Filter.Type | ✓ |
| Capability identity correct | filter_field_type | ✓ |
| VST3 identity explicit | Filter 1 Type, index 204 | ✓ |
| State path correct | VoiceFilter0.plainParams.kParamType | ✓ |
| Enum value NOT numeric | "BP12" (string) | ✓ |
| Control/treatment distinct | enum "BP12" vs. default | ✓ |
| Fine-grained diff PASS | yes | ✓ |
| Top-level isolation PASS | yes | ✓ |
| Generation gate | PASS | ✓ |
| Collateral gate | PASS | ✓ |
| Behavior gate | NOT_RUN | ✓ |
| Persistence gate | PASS | ✓ |
| P1 NOT_RUN (not fabricated) | yes | ✓ |
| P2 NOT_RUN (not fabricated) | yes | ✓ |
| P3 NOT_RUN (not fabricated) | yes | ✓ |
| Restoration NOT_RUN | yes | ✓ |

**All infrastructure/identity checks PASS.**

---

## Key Finding: Persistence Divergence

BOOLEAN and ENUM show different persistence outcomes:

```
OSC1.Enable (boolean):
  - Mutates in-memory ✓
  - Does NOT persist across save/load ✗

Filter.Type (enum):
  - Mutates in-memory ✓
  - DOES persist across save/load ✓
```

This is legitimate data about Serum's serialization behavior. The evaluator correctly preserved the independent gates to expose this distinction.

---

## Causal Audit — Step 4

Behavior gate is NOT_RUN because no causal measurements were recorded.

This is expected and correct. The architecture remains orthogonal:
- Generation and persistence are now proven independent
- Behavior (audible/measured effect) is a separate pipeline

---

## Verdict

**ENUM H1: INFRASTRUCTURE GATE PASS, PERSISTENCE PASS** ✓

Orchestration, identity resolution, enum value handling, and gate independence all working correctly. Enum values are preserved as strings (not reinterpreted as numeric). Persistence survives save/load for Filter.Type, contrasting with OSC1.Enable's serialization failure.

**Recommendation:** Proceed to Step 6: SCALAR H1 pilot.

Note: SCALAR target (`Filter.Resonance`) is not in the Phase 1 resolved registry. This will be a registry-gap audit, not a simple persistence test like BOOLEAN/ENUM.
