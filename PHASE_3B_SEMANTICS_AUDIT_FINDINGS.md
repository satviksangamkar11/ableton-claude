# Phase 3B Semantics Audit — Findings

**Date**: 2026-09-10  
**Status**: COMPLETE — Architectural gap identified  
**Branch**: 2  

---

## EXECUTIVE SUMMARY

Phase 3a successfully implemented exercise-gate plumbing (storage + generic gate mechanism). Phase 3b audit reveals that **the existing architecture cannot safely represent the target↔context↔exercise relationship required to enforce the anti-shortcut invariant**.

A new semantic relationship type (`ExerciseQualification`) is needed to bridge this gap. **No implementation yet.** Phase 3c will design its exact schema and ownership before code is written.

---

## PHASE 3B AUDIT SCOPE

Three composition questions inspected on branch `1`:

1. Can `ClaimDefinition` express exercise-context binding?
2. Can `ClaimGroup.relationships` encode exercise qualification?
3. Can `CapabilityContract.provenance` carry enforceable semantics?

**Result**: All three rejected. Gap is real and specific.

---

## THE GAP (PRECISE)

**Current state**:
```
EvidenceRecord.exercise_measurements exists
        ↓
gate("exercise") = PASS/NOT_RUN/FAIL
        ↓
ClaimDefinition.required_gate["exercise"] = PASS
        ↓
contract qualification
```

**Missing relationship**:
```
Exercise Evidence E42
        ↓ establishes behavioral context
Context Proposition C ("Filter.Enabled == 1")
        ↓ required by causal claim
Target T (Drive)
        ↓ with explicit scope
Reuse scope S
```

**Consequence**: Cannot prevent:
```
VoiceFilter.Enable exercised = PASS
        ↓ (incorrectly used to imply)
VoiceFilter.Drive causally verified
VoiceFilter.Freq causally verified
VoiceFilter.Reso causally verified
... (unproven)
```

---

## WHY EXISTING MECHANISMS FAIL

### 1. RequiredContext — Structural, not behavioral
- **What it does**: Resolves structural path queries ("can this mutation path resolve in this body?")
- **What it doesn't do**: Express behavioral context prerequisites ("is this control exercised?")
- **Problem**: Index-agnostic and deliberately separated from causal qualification
- **Verdict**: ❌ Not sufficient

### 2. ClaimGroup.relationships — Dependency analysis, not exercise binding
- **What it does**: Derives prerequisite dependencies between experiments (same mutation, different condition, isolated condition difference, different outcome)
- **What it doesn't do**: Express "exercise evidence E proves context C for target T"
- **Problem**: Only consumed by summary; not used in `_qualifying()` or contract building
- **Verdict**: ❌ Not sufficient

### 3. CapabilityContract.scope/provenance — Traceable but not enforceable
- **What it does**: Record tested context, evidence IDs, mutation target/value
- **What it doesn't do**: Enforce "this exercise evidence applies ONLY to this target"
- **Problem**: No policy/evaluator consumes the relationship; metadata without semantics
- **Verdict**: ❌ Not sufficient

### 4. ClaimDefinition — Policy, not relationship binding
- **What it does**: Define claim qualification rules (required_gate, required_measurement)
- **What it doesn't do**: Bind exercise evidence to specific targets
- **Problem**: No vocabulary for "requires context proved by evidence"
- **Verdict**: ❌ Not sufficient

---

## THE ANTI-SHORTCUT INVARIANT (NOT CURRENTLY ENFORCEABLE)

```
RULE: Exercise evidence is NEVER reusable by default.
      Reuse requires explicit, evidence-backed scope.

CURRENT STATE: No field/mechanism enforces this.

EXAMPLE OF UNSAFE GENERALIZATION:
  E42: VoiceFilter.Enable (OFF → ON) → -3.78 dB
  ✓ Proves Filter is active/in signal path
  
  But CANNOT automatically prove:
  ✗ Drive is exercisable
  ✗ Freq is exercisable
  ✗ Reso is exercisable
  ✗ Q is exercisable
  
  Each target has its own context dependencies.
```

---

## THE MINIMUM MISSING ABSTRACTION

**Type**: `ExerciseQualification` (relationship, not evidence)

**Schema**:
```python
ExerciseQualification {
    exercise_evidence: str,       # E42 (reference to EvidenceRecord)
    context_proposition: str,     # "Filter.Enabled == 1" (behavioral fact)
    target_claim: str,            # Drive (reference to ClaimDefinition)
    scope: Dict[str, Any],        # reuse boundaries + justification
}
```

**Placement**: Claim/Qualification layer (between Evidence and Contract)
- NOT inside `EvidenceRecord` (would duplicate evidence model)
- NOT inside `CapabilityContract` (violates read-only downstream constraint)
- YES in Claim/qualification evaluation logic

**Purpose**: Enable enforcement of anti-shortcut invariant:
```
E42 + "Filter.Enabled" + Drive  →  Drive exercisable
E42 + "Filter.Enabled" + Freq   →  UNKNOWN (no explicit qualification)

unless scope says E42 generalizes to {Drive, Freq, Reso, ...}
with explicit evidence backing
```

---

## ARCHITECTURAL CONSEQUENCE

The existing architecture cleanly separates concerns:

```
EvidenceRecord           = raw observation (immutable)
RequiredContext          = structural path context
ExperimentSpec           = experimental setup/condition
ClaimDefinition          = claim policy
ClaimGroup               = what evidence establishes + dependencies
CapabilityContract       = derived capability (read-only)
RequiredContext (runtime)= path resolution at runtime
```

**Missing piece**:
```
ExerciseQualification    = interpretation layer binding
                          Exercise Evidence
                          → Context Proposition
                          → Target Claim
                          → Reuse Scope
```

Placing it in Claim/Qualification layer maintains the existing unidirectional dependency: Evidence → Claim → Contract, with no backward flow.

---

## PHASE 3B.8 COMPOSITION AUDIT RESULTS

| Question | Mechanism | Result |
|----------|-----------|--------|
| Can ClaimDefinition express it? | subject_pattern + required_gate | ❌ No vocabulary |
| Can relationships encode it? | ClaimGroup.relationships | ❌ Dependency-only; not consumed |
| Can provenance carry it? | CapabilityContract.scope/provenance | ❌ Metadata without enforcement |
| Existing composition sufficient? | All three together | ❌ NO |

---

## WHAT'S PROVEN SOUND

✅ Phase 3a plumbing (exercise_measurements field + gate)  
✅ Target-specific causal evidence (ClaimDefinition.required_measurement protects against e.g., Drive←Volume)  
✅ Evidence provenance (CapabilityContract.provenance traces back)  
✅ Dependency analysis (relationships derive condition prerequisites)  
✅ Structural context (RequiredContext for path resolution)  
✅ No shortcuts in existing code (admission, producer, harness unchanged)  

---

## WHAT'S MISSING

❌ Behavioral context binding (Exercise E → Context C → Target T)  
❌ Reuse-scope enforcement  
❌ Anti-shortcut invariant enforcement mechanism  

---

## PHASE 3C DESIGN MANDATE

Before any implementation, Phase 3c must answer 10 design questions:

1. Define exact `ExerciseQualification` schema
2. Define who creates it (harness? builder? evaluator?)
3. Define who validates it (gates? rules? claims?)
4. Define scope/reuse semantics (format, validation)
5. Define how `ClaimGroup` consumes it (affects qualification? coverage?)
6. Define how `CapabilityContract` exposes it (new field? method?)
7. Define how Runtime Admission checks it (prerequisites? gates? separate layer?)
8. Define invariants + negative cases (enforcement boundaries)
9. Define serialization/backward compatibility
10. Design-review kill gate before implementation

---

## NEXT STEPS

```
Phase 3a  ✅ COMPLETE (plumbing: exercise_measurements + gate)
Phase 3b  ✅ COMPLETE (audit: gap identified and proven)
Phase 3c  ⏳ DESIGN ONLY (answer 10 questions above)

Implementation: BLOCKED until 3c completes
Serum Experiments: BLOCKED until implementation
```

**CRITICAL RULE**: Exercise evidence is NEVER reusable by default. Reuse requires explicit, evidence-backed scope.

---

**Status**: Audit complete. Gap identified. No implementation. Findings locked for Phase 3c design.
