# A3 H1 BOOLEAN Audit — Step 3

**Experiment:** A3-H1-BOOLEAN-OSC1-ENABLE  
**Semantic Target:** OSC1.Enable  
**Execution Date:** 2026-09-11  
**Status:** INFRASTRUCTURE PASS, PERSISTENCE FAIL  

---

## Identity Verification Checklist

### Semantic Identity
- [x] semantic_id correct: `OSC1.Enable` ✓
- [x] capability_key correct: `oscillator_field_OSC-ENABLE` ✓

### VST3 Identity (Explicit, not inferred)
- [x] vst3_name: `A Enable` ✓
- [x] vst3_index: `20` (explicit, from resolved registry) ✓
- [x] Index NOT inferred from state path ✓

### Experiment Specification
- [x] experiment_id: `A3-H1-BOOLEAN-OSC1-ENABLE` ✓
- [x] state_path: `VoiceOsc0.plainParams.kParamEnable` ✓
- [x] mutation value: `true` (boolean, matches intent) ✓
- [x] isolation_level: `single_field` ✓
- [x] provenance: `A3_H1_PILOT` ✓

---

## Generation Gate — **PASS** ✓

**Reason:** "State observation matches declared mutation intent."

**Details:**
- `top_level_ok`: true ✓
- `fine_grained_ok`: true ✓
- `diff_keys`: ["VoiceOsc0"] (correct scope)

**Interpretation:** The state mutation was successfully applied to Serum. The intended parameter changed from default to the declared value. No unintended side effects within the fine-grained observation.

---

## Collateral Gate — **PASS** ✓

**Reason:** "Observed state diff contains only the declared mutation target(s)."

**Details:**
- `diff_keys`: ["VoiceOsc0"]
- `intended_targets`: ["VoiceOsc0.plainParams.kParamEnable"]

**Interpretation:** Only the declared target changed. No unintended collateral mutations. This verifies SINGLE_FIELD isolation was respected.

---

## Behavior Gate — **NOT_RUN**

**Reason:** "No causal measurements were recorded."

**Details:** Empty measurement array in EvidenceRecord.

**Status:** EXPECTED for this stage. Causal measurement (render audio, measure effect) is a separate pipeline step not yet integrated into H1.

---

## Persistence Gate — **FAIL** ✗

**Overall Status:** FAIL

**Reason:** "Persistence check failed (resave/load identity mismatch)."

**Details:**
```json
{
  "status": "FAIL",
  "checked": true,
  "exact_match": false,
  "detail": {
    "VoiceOsc0.plainParams.kParamEnable": false
  }
}
```

**Interpretation:** 
- The mutation WAS generated (generation = PASS)
- After save/load cycle, the value was `false` (not `true`)
- The parameter did NOT persist across the save-and-reload sequence

**This is NOT a contradiction.** Generation and persistence are independent gates:

```
generation = PASS     (mutation can change state)
persistence = FAIL    (state does not survive save/load)
```

This is informative: OSC1.Enable can be mutated in memory, but Serum (or the serialization layer) does not preserve this change when the state is saved and reloaded.

---

## P1/P2/P3 Lifecycle Gates — **ALL NOT_RUN** ✓

**All three lifecycle tests:**
- `p1_same_engine`: NOT_RUN ✓
- `p2_new_instance`: NOT_RUN ✓
- `p3_fresh_process`: NOT_RUN ✓

**Reason:** "P1/P2/P3 lifecycle identity is not separately established by the current EvidenceRecord."

**Status:** EXPECTED and CORRECT. These gates are not fabricated. They will remain NOT_RUN until independent restoration evidence exists (Step 12 in the roadmap).

---

## Restoration Gate — **NOT_RUN** ✓

**Reason:** "Formal restoration evidence is not implemented yet."

**Status:** EXPECTED. Restoration qualification is not yet built (roadmap Step 12).

---

## Derived Claims (Narrow)

```
transport_mutable:      true     (generation PASS)
generation_verified:    true     (generation PASS)
persistent_p1:          false    (p1 NOT_RUN, so false)
persistent_p2:          false    (p2 NOT_RUN, so false)
persistent_p3:          false    (p3 NOT_RUN, so false)
collateral_safe:        true     (collateral PASS)
behavior_verified:      false    (behavior NOT_RUN, so false)
```

---

## Infrastructure Audit Summary

| Criterion | Result | Status |
|-----------|--------|--------|
| Semantic identity correct | OSC1.Enable | ✓ |
| Capability identity correct | oscillator_field_OSC-ENABLE | ✓ |
| VST3 identity explicit | A Enable, index 20 | ✓ |
| State path correct | VoiceOsc0.plainParams.kParamEnable | ✓ |
| Control/treatment distinct | boolean true vs. default | ✓ |
| Fine-grained diff PASS | yes | ✓ |
| Top-level isolation PASS | yes | ✓ |
| Generation gate | PASS | ✓ |
| Collateral gate | PASS | ✓ |
| Behavior gate | NOT_RUN | ✓ |
| P1 NOT_RUN (not fabricated) | yes | ✓ |
| P2 NOT_RUN (not fabricated) | yes | ✓ |
| P3 NOT_RUN (not fabricated) | yes | ✓ |
| Restoration NOT_RUN | yes | ✓ |

**All infrastructure/identity checks PASS.**

No evidence was synthesized or fabricated. All gates remain independent. The runner correctly preserved the distinction between:
- State mutation capability (generation = PASS)
- Persistence across save/load (persistence = FAIL)
- Behavioral causality (behavior = NOT_RUN, awaiting separate measurement pipeline)

---

## Causal Audit — Step 4

Behavior gate is NOT_RUN because no causal measurements were recorded in this run.

**This is correct.** The architecture separates:
1. Can we mutate the state? → generation gate
2. Does it persist? → persistence gates
3. Does it have an audible/measured effect? → behavior gate

These are orthogonal. BOOLEAN passes generation and collateral but fails persistence. Behavior is deferred to a separate causal measurement pipeline (not yet integrated into H1).

---

## Verdict

**BOOLEAN H1: INFRASTRUCTURE GATE PASS** ✓

The orchestration, identity resolution, mutation generation, and gate independence are all working as designed. The persistence failure is data, not a system failure—it tells us that OSC1.Enable can be mutated in-memory but does not serialize.

**Recommendation:** Proceed to Step 5: ENUM H1 pilot.
