# CLAUDE.md — Ableton + Serum 2.0.21 AI Producer

## Project Overview

This is a trustworthy AI music producer for **Serum 2.0.21** (VST3) running under **Ableton Live 12.3 Suite** on Windows. The system grounds music synthesis knowledge exclusively in measured evidence; unknown capabilities remain unknown rather than being guessed or laundered into plausibility.

## Frozen Environment

These are locked and never updated, downgraded, patched, replaced, or modified:
- **Serum 2.0.21** VST3 installation
- **DawDreamer 0.9.0** (Serum host / DAW plugin controller)
- **Python 3.14** (runtime environment)
- **Ableton Live 12.3 Suite** (when used as reference ground truth)

Environment mismatches invalidate prior evidence. Document Windows version and audio driver if running new experiments.

## Epistemic Rules

1. **Unknown stays unknown.**
   - No capability exists without admissible evidence.
   - Absence of evidence ≠ evidence of absence (15.4.3 distinction).
   - Never invent, assume, or synthesize capabilities.

2. **Serum-specific claims require measured evidence.**
   - General synthesis knowledge ("make darker") is HYPOTHESIS until Serum-specific measurement gates pass.
   - Hypothesis execution is discovery-seeking, not music-making.

3. **Evidence system layers (one-directional, never reversed):**
   ```
   EvidenceRecord → ClaimDefinition → ClaimEngine → ClaimGroup → 
   CapabilityContract → Compiler Admission
   ```
   - EvidenceRecord = observation only; no interpretation.
   - Claims/capabilities derived from admissible evidence only.
   - Findings never promote capabilities; evidence does.

4. **Preserve evidence distinctions:**
   - CAUSAL_VERIFIED (effect observed, causal gates passed)
   - STRUCTURAL_ONLY (construct + mutate + persist; causal NOT_RUN or negative)
   - NEGATIVE_EVIDENCE (gates demonstrably failed)
   - BLOCKED_CONTRADICTED (conflicting evidence; reverify required)
   - UNSUPPORTED (robust, repeated rejection)

5. **Do not launder historical evidence into current-runtime verification.**
   - A prior experiment's measurement = evidence for that experiment's context only.
   - Reuse of that evidence in a new compiler context requires independent verification.
   - Contract's prerequisites capture what the original experiment verified; caller must re-verify for their own context.

6. **Do not infer causality from uncontrolled or confounded experiments.**
   - Single-field isolation (SINGLE_FIELD) required for causal claims.
   - Confound-marked results (e.g., RandomPan) stay STRUCTURAL_ONLY even if measurement gates passed.

## Architecture

### Knowledge Loop
```
unknown → ExperimentSpec → EvidenceRecord → ClaimGroup → 
CapabilityContract (static, read-only artifact)
```

### Production Loop
```
User Intent/Goal → Semantic Target → Capability Admission → 
Compiler (→ Serum State) → Render → Measurement → Feedback
```

### Semantic IR (Authoritative)
- Semantic targets are exact capability references (e.g., `FXEQ.Freq1` → `fx_field_eq_freq1`).
- Targets live in `serum2/compiler/targets.py::SEMANTIC_TARGETS`.
- No fuzzy matching; unknown targets are refused at admission time.
- No literal numeric indices in target names (e.g., no `FXEQ.0.Freq1`).

### Compilation Layers
1. **targets.py:** Semantic target vocabulary (read-only, no indices).
2. **context.py:** Runtime context resolution (path rewriting, list-index determination).
3. **admission.py:** Capability contract queries and prerequisite verification.
4. **producer.py:** Grounding conditions and execution policy (GROUNDED, HYPOTHESIS, UNGROUNDED).
5. **structural_admission.py:** Numeric range checking for STRUCTURAL_ONLY fields.

### Contracts (Read-Only Artifacts)
- CapabilityContract = static snapshot of what evidence proved.
- Status (CAUSAL_VERIFIED, etc.) never changes after creation.
- Prerequisites encode what the original experiment established; caller responsibility to verify for new context.
- Measurement definition ID must match; wrong ID = wrong evidence = REFUSED.

## Context and Prerequisites

1. **Declared context is NOT automatically verified context.**
   - `proposed_prerequisites_verified` in `admit()` is a dict of field_path → bool.
   - Caller must independently confirm each prerequisite's value at runtime.

2. **Value-sensitive prerequisites require exact value matching.**
   - If contract.prerequisites has `must_hold_identical=True`, exact match required (e.g., 0.02, not 0.01).
   - No automatic coercion, snapping, or substitution.

3. **Use existing context-resolution architecture.**
   - `serum2/compiler/context.py::RequiredContext` for index-agnostic list membership.
   - `extract_required_context()` for path-based derivation.
   - `derive_required_context()` for probing a base state.

4. **Context requirement sources:**
   - Evidence baseline_overrides (authoritative observation during experiment).
   - Contract provenance.shared_context (if extended by step 16.5.48+).
   - Never invent context from target name alone.

## Safety Constraints

Unless the current task explicitly requires it:
- **Do not mutate Serum** via set_parameter or state manipulation.
- **Do not render audio** (no DawDreamer playback/record).
- **Do not create new EvidenceRecords** (no new research without explicit approval).
- **Do not modify existing evidence** (no pickle editing, no ClaimEngine rewrites).
- **Do not weaken or rewrite tests** to make implementation changes pass.
- **Do not manually edit pickle artifacts** (contract files, evidence files).
- **Do not change capability status** without the required evidence promotion path.

These are audit/analysis boundaries, not implementation laziness.

## Testing and Regression

1. **Existing passing tests are regression contracts.**
   - Never change test expectations to accommodate a new implementation.
   - If an implementation conflicts with a passing test, the implementation is wrong.

2. **A diagnostic result is not success.**
   - "The script ran" ≠ "the step is complete."
   - Verify against exact acceptance criteria.

3. **Run relevant regression tests after architectural changes.**
   - Frontier freeze tests (contract counts, hashes).
   - Admission tests (prerequisite handling, measurement matching).
   - Producer tests (grounding conditions, execution policy).

4. **Stop rather than proceeding.**
   - If a required criterion fails, report the failure.
   - Do not advance to the next step to work around the blocker.

## Change Discipline

1. **Prefer the smallest change that satisfies the requirement.**
   - Inspect existing code before designing a new abstraction.

2. **Reuse established representations.**
   - Reuse contract/claim/evidence layers instead of creating parallel mechanisms.
   - Reuse admission.py's prerequisite/measurement pathways.
   - Reuse context.py's RequiredContext for path resolution.

3. **Do not create duplicate architectures.**
   - One ClaimEngine, one CapabilityContract lookup, one admission gate.
   - New policy goes into existing layers (producer.py grounding conditions, not a parallel "reasoning loop").

4. **Do not repeat completed experiments.**
   - Unless new evidence invalidates prior results, reuse prior findings.
   - Preserve hashes and artifacts across steps.

5. **Preserve backward compatibility.**
   - Contract status, evidence fingerprints, frontier counts.
   - Only change when the task explicitly requires it and provides justification.

## Producer Behavior

1. **Capability knowledge ≠ context-safe usability.**
   - "I know Sustain works" (CAUSAL_VERIFIED) is different from "I can safely use Sustain here" (prerequisites verified).
   - Admit only when both are true.

2. **Exact semantic target matching only.**
   - No fuzzy matching, no family-name lookups, no substring matches.
   - `FXEQ.Freq1` resolves to `fx_field_eq_freq1`, not to "any FXEQ field."
   - Unknown targets produce `unknown_no_contract` refusal, not a guess.

3. **Refuse unsupported operations rather than guessing.**
   - Numeric clamping (structural bounds) only for MUTATE_NUMERIC operations.
   - Enum/boolean/structured operations return UNKNOWN if not proven.

4. **Grounding conditions (from producer.py):**
   - GROUNDED: CAUSAL_VERIFIED contract + same metric + EFFECT_OBSERVED + correct direction + generalizing coverage.
   - PARTIALLY_GROUNDED: three of four above, OR coverage=INSTANCE.
   - HYPOTHESIS: causal only, or metric-mismatch, or directional uncertainty.
   - UNGROUNDED: none of the above.
   - Execution policy: GROUNDED → NORMAL; HYPOTHESIS → CAPABILITY_DISCOVERY_NEEDED (not exploratory execution).

5. **Exploratory execution is not evidence.**
   - PARTIALLY_GROUNDED/exploratory results have `is_admissible_as_evidence = False`.
   - Can inform the producer loop only; cannot strengthen capability claims.

## Workflow for Each Task

1. **Inspect authoritative code/artifacts first.**
   - Read the actual implementation (admission.py, contract structure, semantics).
   - Do not rely on summarized architectural descriptions.

2. **Implement only what the task requires.**
   - No preemptive refactoring, no "while we're here" improvements.

3. **Verify against exact acceptance criteria.**
   - Not just "the script ran" but the specific criteria named in the task.

4. **Report failures honestly.**
   - If a criterion is not met, say so explicitly.
   - Do not reframe failure as partial success.

5. **Stop rather than proceeding.**
   - Blocking issues are not invitations to skip to the next step.
   - Fix the blocker or report it; do not work around it.

## No Temporary Rules

Do not add step numbers, experiment IDs, or temporary investigation notes to this file. GATES.md and PROOF_PLAN.md track those. CLAUDE.md is for permanent project rules only.
