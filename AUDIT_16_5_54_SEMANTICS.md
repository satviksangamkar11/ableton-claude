# AUDIT 16.5.54: Producer Verification Semantics

## Goal
Ensure ProducerResult semantics are precise and distinguish between six independent success criteria before expanding producer coverage.

## Critical Semantic Distinctions

### 1. **Admission Success**
- **Definition**: Can the semantic target be called at all?
- **Evidence**: `refusal_reason is None`
- **Context**: Checked BEFORE any Serum execution
- **Examples of admission failure**:
  - `resolved_ref is None` → semantic target unknown
  - `resolved_path is None` → context not satisfied in supplied body
  - `structural_status in (REFUSE, UNKNOWN)` (STRUCTURAL_BIND_MODE only) → structural validation failed
  - Dry run refused → prerequisite incompatibility, cross-contract conflict

### 2. **Construction/Load Success**
- **Definition**: Did Serum load the ExperimentSpec and accept the mutation?
- **Evidence**: `load_status == "PASS"`
- **Caution**: This is about *construction acceptance*, NOT about whether the field works.
- **Relationship to admission**: Admission passes, load fails = Serum rejected the spec or plugin failed to initialize
- **Never implies field-specific causal verification**

### 3. **Persistence Success**
- **Definition**: Did Serum retain the set value in its saved state?
- **Evidence**: `persistence_status == "PASS"`
- **Caution**: Value persisted ≠ field is causal for the goal
- **Relationship to load**: Load can pass while persistence fails (value was set in memory but not stored)
- **Relationship to causality**: Required but not sufficient for causal verification
- **Examples**:
  - Persistence PASS + NO_OBSERVED_EFFECT → structural mutation confirmed, no causal effect (yet)
  - Persistence FAIL + EFFECT_OBSERVED → the measurement effect is spurious (mutation didn't actually happen)

### 4. **Execution-Level Effect Observed**
- **Definition**: Did the overall_rms_db (or other measured output) change between control and treatment?
- **Evidence**: Measurement from EvidenceRecord.causal_measurements[0]
- **Status field values**:
  - `EFFECT_OBSERVED` → delta met expected direction, absolute magnitude ≥ threshold
  - `NO_OBSERVED_EFFECT` → absolute delta < threshold OR threshold not set
  - `WRONG_DIRECTION` → absolute delta ≥ threshold BUT direction wrong
- **Critical**: This is OVERALL effect (usually overall_rms_db), not field-specific causal proof
- **Never confuse with causality claim**: Effect on overall mix ≠ field caused it

### 5. **Field-Specific Causal Verification**
- **Definition**: Is there evidence this field specifically caused the observed effect?
- **Evidence**: NOT in ProducerResult alone — requires:
  - CapabilityContract.status == CAUSAL_VERIFIED
  - CapabilityContract.measurement metric matches requested metric
  - CapabilityContract.measurement.status == EFFECT_OBSERVED
  - Producer loop checked claim coverage (form_prediction grounding logic)
- **Architectural truth**: One ExperimentSpec / one EvidenceRecord cannot isolate per-field causality
- **Producer constraint**: `per_field_causal_isolation would require N separate renders -- not done here`
- **What measurement IS**: Execution observation; what it's NOT: capability claim

### 6. **Goal Success**
- **Definition**: Did we achieve the musical/musical-production goal?
- **Evidence**: Producer verdict (producer.py logic), not raw result
- **Examples**:
  - `succeeded()` = True: all gates passed AND no refusal AND causal_status EFFECT_OBSERVED
  - `succeeded()` = False: any gate NOT_RUN/FAIL OR refusal_reason is not None

## Field-Level Semantics

### ProducerResult.resolved_ref
- **Definition**: Semantic target successfully resolved to a CapabilityContract reference?
- **Values**: SemanticTargetRef or None
- **Meaning of None**: Semantic resolution failed (unknown name or not in SEMANTIC_TARGETS)
- **Prerequisite for**: All downstream gates

### ProducerResult.resolved_path
- **Definition**: Concrete path in supplied body context matched the semantic requirement?
- **Values**: Concrete path string or None
- **Meaning of None**: Context not satisfied (required container/list element missing in body)
- **Prerequisite for**: Structural admission and construct_and_verify

### ProducerResult.structural_status
- **Definition**: Does the requested value fit the field's numeric/enum bounds?
- **Values**: "ACCEPT" | "REFUSE" | "UNKNOWN" | "NOT_CHECKED"
- **NOT_CHECKED**: WITNESS_MODE (requested_value is None) — no structural validation
- **UNKNOWN**: No structural records available to validate (data-driven lower bound check)
- **ACCEPT**: Value is within provable bounds
- **REFUSE**: Value violates provable bounds
- **Enforcement in STRUCTURAL_BIND_MODE**: REFUSE or UNKNOWN → result refuses before dry_run

### ProducerResult.load_status
- **Definition**: Did DawDreamer/Serum successfully execute render_arm() for control and treatment?
- **Values**: "PASS" | "FAIL" | "NOT_RUN"
- **PASS**: Both control and treatment arms rendered (audio produced)
- **FAIL**: At least one arm failed to load/render
- **NOT_RUN**: construct_and_verify was not called (pre-execution refusal)
- **Semantics of PASS**: Serum accepted the ExperimentSpec, not a proof the field works

### ProducerResult.persistence_status
- **Definition**: Did Serum persist the mutation to saved state?
- **Values**: "PASS" | "FAIL" | "NOT_RUN"
- **PASS**: All mutations stored exactly in resaved state
- **FAIL**: At least one mutation's value differed (clamped, rejected, or not set)
- **NOT_RUN**: construct_and_verify was not called OR persistence check was not run
- **Semantics of PASS**: Value was stored, not that it has the intended musical effect

### ProducerResult.causal_status
- **Definition**: Did measurement show an effect in the expected direction?
- **Values**: "EFFECT_OBSERVED" | "NO_OBSERVED_EFFECT" | "WRONG_DIRECTION" | "NOT_RUN"
- **Source**: EvidenceRecord.causal_measurements[0] (single overall_rms_db measurement, typically)
- **EFFECT_OBSERVED**: Delta ≥ threshold, direction matches expected
- **NO_OBSERVED_EFFECT**: Delta < threshold (no substantial change)
- **WRONG_DIRECTION**: Delta ≥ threshold but opposite direction to expected
- **NOT_RUN**: No measurement was taken (construct_and_verify not called)
- **Critical semantics**: This is the overall measurement result, not field-specific causality
  - Possible: persistence PASS + causal NO_OBSERVED_EFFECT (mutation applied, no measured effect)
  - Possible: persistence FAIL + causal EFFECT_OBSERVED (spurious measurement, mutation didn't actually happen)

### ProducerResult.measurement
- **Definition**: Snapshot of the measurement (overall_rms_db typically)
- **Values**: Dict with keys (metric, baseline, treatment, delta, status) or None
- **NOT a causal claim**: This is execution observation
- **Required for evaluation but not sufficient for capability claim**: Needs CapabilityContract evidence

### ProducerResult.record
- **Definition**: EvidenceRecord from construct_and_verify, or None if not called
- **Values**: EvidenceRecord or None
- **Meaning of None**: construct_and_verify was not called (pre-execution refusal)
- **Meaning of EvidenceRecord**: Observation of this specific execution; not a contract
- **Provenance tracking**: Every measurement comes with:
  - experiment_id (who made this observation)
  - measurement_condition_signature (under what conditions)
  - measurement_definition_id (which algorithm measured it)

### ProducerResult.succeeded()
- **Definition**: All required gates passed and no refusal?
- **Criteria**:
  - load_status == "PASS"
  - persistence_status == "PASS"
  - refusal_reason is None
- **NOT checked**: causal_status (load/persistence success ≠ causal claim)
- **Why this design**: Separates "did we execute?" from "did we prove the field works?"
- **Danger zone**: Calling succeeded() and then assuming measurement proves causality
  - Wrong: "succeeded() is True, therefore overall_rms_db change proves this field is causal"
  - Right: "succeeded() is True, therefore the mutation was applied; measurement shows what happened"

## Architectural Constraints

### EvidenceRecord Provenance
- One construct_and_verify call = one ExperimentSpec = one EvidenceRecord
- That record captures load/persistence/measurement from that one execution
- Multiple fields in one goal share ONE measurement (not per-field isolation)
- Example: OSC1.Volume + OSC2.Volume in one goal → both fields in ONE spec, one overall_rms measurement
- Consequence: Cannot prove "OSC1 caused the delta" by examining causal_status alone

### Measurement vs. Causality
- Producer measures overall effect (overall_rms_db by default)
- Capability claim requires field-specific causality (CapabilityContract evidence from knowledge loop)
- These are at different layers:
  - **Execution observation** (this step): "I set field X, and overall_rms changed by Y dB"
  - **Capability claim** (evidence layer): "Field X causes overall_rms to change in Z way (across N conditions)"
- Producer verdict uses measurement to inform goal success, not to create capability claims

### Refusal Semantics
- Pre-execution refusals (resolved_ref, resolved_path, structural_status, admission) → record is None
- Execution refusals (construct_and_verify raised) → would not reach result packaging
- Producer goal composition: ANY field pre-execution refusal → entire goal refused
- Result never represents "partial execution"

## Danger Zones: What NOT to Do

1. **Do NOT treat overall_rms_db delta as field-specific causal proof**
   - It's a side-effect observation, not a field causality claim
   - Wrong: `measurement["delta"] > 0 → field works`
   - Right: `measurement["delta"] > 0 AND contract.status == CAUSAL_VERIFIED → field effect confirmed in this context`

2. **Do NOT confuse success() == True with "field is causal"**
   - True = gates passed, mutation was applied
   - Causality = CapabilityContract evidence from knowledge loop

3. **Do NOT assume persistence PASS implies effect is meaningful**
   - Value persisted ≠ value has intended effect
   - May be: structural mutation only (STRUCTURAL_ONLY contract)

4. **Do NOT treat measurement as independent per-field evidence**
   - One spec, one render, one overall measurement
   - Per-field isolation requires separate specs (not done in producer)

5. **Do NOT launder execution observation into capability claims**
   - This execution's EvidenceRecord is specific to this context
   - Capability contract evidence comes from knowledge loop (isolation, repeated conditions, etc.)
   - Producer does NOT create new capability evidence

## Test Matrix (16.5.54 Requirements)

| Scenario | Load | Persistence | Effect | Record | Interpretation |
|----------|------|-------------|--------|--------|-----------------|
| A: Normal construction | PASS | PASS | EFFECT_OBSERVED | Present | Mutation applied, effect measured |
| B: Structural only | PASS | PASS | NO_OBSERVED_EFFECT | Present | Mutation applied, no measured effect |
| C: Admission refused | N/A | N/A | N/A | None | Pre-execution refusal, no Serum touch |
| D: Structural UNKNOWN | N/A | N/A | N/A | None | Pre-execution refusal (STRUCTURAL_BIND_MODE) |
| E: Persistence fail | PASS | FAIL | May vary | Present | Mutation not stored, measurement is spurious |

## Acceptance Criteria for 16.5.54

1. ✓ Code comments document each field's exact meaning
2. ✓ Tests A-E prove semantic distinctions hold
3. ✓ No automatic overall_rms measurement laundered into field causality
4. ✓ EvidenceRecord provenance distinguishes execution from capability
5. ✓ Producer result fields cannot accidentally imply capabilities
6. ✓ All existing tests still pass
7. ✓ Frontier unchanged: 37 contracts (26/8/3)
