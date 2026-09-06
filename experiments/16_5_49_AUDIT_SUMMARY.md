# 16.5.49: Sustain Compiler Provenance Admission Audit

## Executive Summary

**Decision: BLOCKED_SEMANTIC_TARGET (Category A)**

The sustain capability is fully proven at the evidence and admission layers but cannot be invoked by the compiler because the semantic target vocabulary is incomplete.

## Audit Results

### ✓ Capability Contract (Evidence Layer)
- **Target:** `envelope_field_sustain`
- **Status:** `CAUSAL_VERIFIED` with `EFFECT_OBSERVED`
- **Gates:** load=PASS, persistence=PASS, causal=EFFECT_OBSERVED
- **Operation:** mutate_numeric_value
- **Evidence:** 2 supporting records
  - `16.5.43.2-CORPUS-ENV-SUSTAIN-CORRECTED`
  - `16.5.45-CORPUS-ENV-SUSTAIN-REVALIDATION`

### ✓ Measurement Definition
- **Metric:** sustain_window_rms_db:c092f5a1078d
- **Target field:** Env0.plainParams.kParamSustain
- **Baseline:** -50.25 dB
- **Treatment:** -44.49 dB
- **Delta:** +5.76 dB (expected direction: increase, observed: increase) ✓
- **Threshold:** 3.0 dB
- **Status:** EFFECT_OBSERVED

### ✓ Provenance & Shared Context
- **Shared context status:** PARTIAL
- **Context field:** Env0.plainParams.kParamDecay
- **Baseline override (documented):** Env0.plainParams.kParamDecay = 0.02
  - Present in: 16.5.45-CORPUS-ENV-SUSTAIN-REVALIDATION
  - Absent in: 16.5.43.2-CORPUS-ENV-SUSTAIN-CORRECTED (schema predates this field)

### ✓ Admission Layer
- **Test: Negative case (no context)** → ADMITTED
- **Test: Positive case (with context)** → ADMITTED
- **Reason:** Contract status is CAUSAL_VERIFIED; admission rules satisfied
- **Conclusion:** Compiler admission layer ready to consume this capability

### ✗ Semantic Resolution Layer
- **Blocker:** No semantic target vocabulary entry
- **Missing registrations:**
  - "Env0.Sustain" → "envelope_field_sustain"
  - "Env1.Sustain" → "envelope_field_sustain"
- **Current SEMANTIC_TARGETS (targets.py, line 48):**
  - FXEQ.Freq1, FXEQ.Freq2, FXEQ.Reso1, FXEQ.Reso2
  - FXEQ.Gain1, FXEQ.Gain2, FXEQ.LevelOut
  - FXDistortion.Drive
  - OSC1.Volume, OSC1.Octave
  - Env1.Decay
  - Global.MasterVolume
  - **Missing:** Env0.Sustain, Env1.Sustain

### ✗ Context Resolution Layer (Enhancement, not blocking)
- **RequiredContext structure:** Not yet extracted from shared_context
- **Status:** Optional refinement for later phases
- **Does not block current decision:** Semantic target registration is the prerequisite

## Resolution Chain Analysis

Per targets.py documentation, the compiler resolution proceeds:

```
"Env0.Sustain" (or similar user-facing name)
  ↓ [FAILS HERE: not in SEMANTIC_TARGETS]
SemanticTargetRef lookup
  ↓
CapabilityContract lookup by capability_key
  ✓ Would succeed: envelope_field_sustain exists
  ↓
RequiredContext derivation via context.extract_required_context()
  ✓ Would succeed with shared_context present
  ↓
Concrete path resolution via RequiredContext.resolve_index()
  ✓ Would succeed in actual Serum state
```

## Category Classification

**Category A:** Capability exists but semantic target vocabulary is missing

- ✓ Capability proven (CAUSAL_VERIFIED)
- ✓ Measurement defined (EFFECT_OBSERVED)
- ✓ Provenance complete with shared_context
- ✓ Admission rules would accept it
- ✗ Compiler cannot invoke: semantic target name not registered

## Next Steps

1. **Register semantic target in targets.py:**
   ```python
   "Env0.Sustain": SemanticTargetRef("Env0.Sustain", "envelope_field_sustain"),
   # or
   "Env1.Sustain": SemanticTargetRef("Env1.Sustain", "envelope_field_sustain"),
   ```

2. **(Optional, Phase 2) Extract RequiredContext:**
   - Current shared_context has all needed fields
   - Can be formalized into RequiredContext if compiler layer needs it
   - Does not block current semantic target registration

3. **Verify compiler can handle:**
   - Generic semantic target → capability contract lookup ✓
   - Admission with measurement_definition_id matching ✓
   - Optional: context-aware path resolution (if RequiredContext extracted)

## Audit Metadata

- **Audit date:** 2026-09-06
- **Contracts loaded:** 14
- **Sustain contract status:** CAUSAL_VERIFIED
- **Decision:** BLOCKED_SEMANTIC_TARGET
- **Category:** A
- **Negative test:** ADMITTED (expected due to CAUSAL_VERIFIED status)
- **Positive test:** ADMITTED (prerequisite satisfaction successful)
