# A3 H1 Pilot Manifest — FROZEN

**Phase:** A3-H1 (Mutation Qualification)

**Status:** Input specification locked. Do not modify during execution.

**Date Locked:** 2026-09-11

---

## Experiment 1: A3-H1-BOOLEAN

```
semantic_id     = OSC1.Enable
state_path      = VoiceOsc0.plainParams.kParamEnable
mutation_value  = true
experiment_id   = A3-H1-BOOLEAN-OSC1-ENABLE
```

**Classification:** Boolean parameter (enable/disable)

**Expected Observation:** State diff contains exactly `VoiceOsc0.plainParams.kParamEnable` with value change to true.

---

## Experiment 2: A3-H1-ENUM

```
semantic_id     = Filter.Type
state_path      = VoiceFilter0.plainParams.kParamType
mutation_value  = BP12
experiment_id   = A3-H1-ENUM-FILTER-TYPE
```

**Classification:** Enum parameter (discrete list of named values)

**Value Basis:** Corpus-verified enum from evidence experiments.

**Expected Observation:** State diff contains exactly `VoiceFilter0.plainParams.kParamType` with value change to "BP12".

---

## Experiment 3: A3-H1-SCALAR

```
semantic_id     = Filter.Resonance
state_path      = VoiceFilter0.plainParams.kParamReso
mutation_value  = 90.0
experiment_id   = A3-H1-SCALAR-FILTER-RESONANCE
```

**Classification:** Scalar parameter (numeric range)

**Value Basis:** High resonance value (90.0) chosen for measurement clarity.

**Expected Observation:** State diff contains exactly `VoiceFilter0.plainParams.kParamReso` with value change to 90.0.

---

## Execution Rules

1. **Do not modify** these specifications during execution.
2. **Execute in order:** BOOLEAN → audit → ENUM → audit → SCALAR → audit.
3. **Stop after each stage** for structural/causal review.
4. **No fabrication:** If a resolved target or evidence observation is missing, report the blocker.
5. **No silent retries:** Each gate either passes, fails, or remains NOT_RUN.

---

## Success Criteria per Experiment

### BOOLEAN (A3-H1-BOOLEAN)

Infrastructure/identity:
- [ ] ResolvedTarget identity correct
- [ ] ExperimentSpec mutation correct
- [ ] State path correct
- [ ] Control vs. treatment distinct
- [ ] Fine-grained diff PASS
- [ ] Top-level isolation PASS
- [ ] Load observation PASS
- [ ] Render observation PASS or NO_OBSERVED_EFFECT

Causality (independent audit):
- [ ] EFFECT_OBSERVED OR NO_OBSERVED_EFFECT (not forced)
- [ ] Behavior gate result matches actual measurement

Persistence:
- [ ] Overall persistence PASS/FAIL (not fabricated)
- [ ] P1/P2/P3 all NOT_RUN (not fabricated)

### ENUM (A3-H1-ENUM)

Same criteria as BOOLEAN, applied to Filter.Type.

### SCALAR (A3-H1-SCALAR)

Same criteria as BOOLEAN, applied to Filter.Resonance.

---

## Next Action

Run A3-H1-BOOLEAN only:

```bash
cd D:\ableton claude
python -m serum2.qualification.a3_h1_runner --target boolean
```

Capture complete output artifact.

Return all:
- ResolvedTarget
- ExperimentSpec
- EvidenceRecord
- MutationReceipt

Do NOT proceed to ENUM until BOOLEAN passes infrastructure audit.
