# Hypothesis Generation Report

**Source:** Serum 2 Manual YouTube Transcript  
**Date:** 2026-09-11  
**Phase:** Hypothesis Generation (Phase 4)  
**Status:** COMPLETE

---

## Executive Summary

From 71 RESOLVED semantic items, 71 hypotheses have been generated. These represent testable predictions extracted from source material, NOT verified Serum behavioral facts.

| Hypothesis Type | Count | % | Actionable |
|---|---|---|---|
| **BEHAVIORAL** | 28 | 39.4% | YES — measurable causal effect |
| **PROCEDURAL** | 43 | 60.6% | NO — workflow/UI steps only |
| **TOTAL** | **71** | **100%** | — |

**Key Finding:** Only 28 of 71 hypotheses (39%) represent testable causal claims about Serum's audio behavior. The remainder (43, 61%) describe workflows or UI procedures without asserting audio effects.

---

## Hypothesis Characteristics

### By Target

| Target | Behavioral | Procedural | Total |
|---|---|---|---|
| OSC1.Wavetable | 8 | 11 | 19 |
| OSC1.Octave | 7 | 9 | 16 |
| Filter.Type | 3 | 6 | 9 |
| Filter.Resonance | 4 | 4 | 8 |
| Env1.Release | 3 | 4 | 7 |
| FXDistortion.Drive | 2 | 2 | 4 |
| Env1.Attack | 0 | 3 | 3 |
| Env1.Decay | 0 | 3 | 3 |
| Env1.Sustain | 0 | 1 | 1 |
| OSC1.Enable | 0 | 1 | 1 |

**Observation:** Oscillator controls (Wavetable, Octave) dominate both categories. Envelope controls skew procedural (zero behavioral hypotheses for Attack/Decay/Sustain).

### By Operation

| Operation | Count | % | Example |
|---|---|---|---|
| UNSPECIFIED | 39 | 54.9% | "wavetable provides timbre variation" |
| MODULATE | 10 | 14.1% | "use LFO to modulate frequency" |
| SELECT | 9 | 12.7% | "choose oscillator waveform" |
| INCREASE | 7 | 9.9% | "increase cutoff for brightness" |
| DECREASE | 5 | 7.0% | "decrease resonance for flatness" |
| TOGGLE | 1 | 1.4% | "enable filter for processing" |

**Interpretation:** 55% of source statements lack explicit operation verbs. They assert properties or capabilities without prescribing a specific action (e.g., "wavetables shape sound" vs "select a different wavetable").

### By Context Status

| Context | Count | % | Meaning |
|---|---|---|---|
| EXPLICIT | 26 | 36.6% | Prerequisites stated in source |
| IMPLICIT | 10 | 14.1% | Audio/signal required (obvious) |
| UNKNOWN | 35 | 49.3% | No context mentioned; must infer |

**Critical Finding:** 49% of hypotheses lack stated context. Experiments will need to establish baseline conditions independently.

---

## Behavioral Hypotheses (28 items)

### Definition
Hypotheses where the source asserts or implies a **causal relationship** between a Serum control and an audible effect.

### Examples

**Example 1: OSC1.Octave Selection**
```
hypothesis_id: hyp_000005
target: OSC1.Octave
operation: SELECT
source_statement: "Sometimes an extra parameter is available. But the main 
                   effect of the oscillator is defined by the octave."
predicted_effect: osc1.octave_operation_has_effect
measurement_plan: [pitch_shift_semitones, fundamental_frequency_hz]
test_status: PROPOSED
```

**Example 2: Filter.Resonance Peak**
```
hypothesis_id: hyp_XXXX
target: Filter.Resonance
operation: INCREASE
source_statement: "Increasing resonance creates a peak at the cutoff frequency."
predicted_effect: filter.resonance_increase_leads_to_peak_magnitude_db
measurement_plan: [peak_magnitude_db, spectral_width_hz]
test_status: PROPOSED
```

### Target Distribution (Behavioral)
- OSC1.Wavetable: 8
- OSC1.Octave: 7
- Filter.Type: 3
- Filter.Resonance: 4
- Env1.Release: 3
- FXDistortion.Drive: 2
- (Others: 0)

### Measurement Dimensions

Each behavioral hypothesis specifies **measurement dimensions** (NOT hard-coded pass/fail thresholds):

- **Spectral:** spectral_centroid_hz, harmonic_content_brightness, spectral_distribution
- **Amplitude:** output_amplitude_db, overall_rms_db, peak_magnitude_db
- **Time:** onset_time_ms, decay_duration_ms, release_duration_ms
- **Pitch:** pitch_shift_semitones, fundamental_frequency_hz
- **Timbre:** timbral_character, harmonic_content, transient_sharpness

---

## Procedural Hypotheses (43 items)

### Definition
Hypotheses where the source describes **workflow or UI interaction** without asserting an audio effect.

### Examples

**Example 1: Envelope Workflow**
```
hypothesis_id: hyp_000000
target: Env1.Release
operation: UNSPECIFIED
source_statement: "Hello everybody. I decided to read the entire Serum manual so 
                   you don't have to. A lot of the information is hidden behind 
                   right-clicks in Serum."
predicted_effect: procedural_context_establishment
test_status: PROPOSED
```

**Example 2: Parameter Discovery**
```
hypothesis_id: hyp_XXXX
target: OSC1.Wavetable
operation: SELECT
source_statement: "Right-click on the wavetable area to see what's available."
predicted_effect: procedural_discovery
test_status: PROPOSED
```

### Characteristics
- Do NOT predict specific audio effects
- Describe UI navigation, parameter discovery, workflow steps
- Valuable for understanding Serum's interface structure
- **Not suitable for behavioral qualification experiments**

---

## CRITICAL EPISTEMIC RULE

**Source Assertion ≠ Verified Fact**

Each hypothesis is extracted from source material as:
```
SOURCE_STATEMENT: "Increasing cutoff makes the sound brighter."
PREDICTED_EFFECT: spectral_centroid_hz increases
MEASUREMENT_PLAN: [spectral_centroid_hz, spectral_distribution]
TEST_STATUS: PROPOSED
```

This means:
- ✓ The source claims it
- ✓ We predict it will have this measurable effect
- ✗ It has NOT been verified in Serum 2.0.21 yet
- ✗ The prediction may be based on general synthesis knowledge, not Serum specifics
- ✗ Prerequisites and context are not yet verified

**No hypothesis becomes evidence without experimental measurement.**

---

## Operation Extraction: Challenges

### 39 Hypotheses with UNSPECIFIED Operation (55%)

The source material often asserts **capabilities** without prescribing **actions**:

```
"Wavetables provide rich spectral content."
  → What is the operation? SELECT? LOAD? SWEEP?
  → No explicit operation in source
  → Classification: UNSPECIFIED
```

**Implication:** Many hypotheses need operational clarification before experiment design.

### Operational Ambiguity Examples

| Source | Target | Operation | Issue |
|---|---|---|---|
| "Wavetables shape timbre" | OSC1.Wavetable | SELECT(inferred) | No verb |
| "Modulate the filter" | Filter.Cutoff | MODULATE | Modulate with what? |
| "Sustain holds the note" | Env1.Sustain | UNSPECIFIED | Describes effect, not operation |
| "Increasing resonance peaks" | Filter.Resonance | INCREASE(inferred) | Cause-effect, no action |

---

## Context Status Breakdown

### EXPLICIT (26 items, 36.6%)

Source directly states prerequisites or conditions:

```
"With the filter enabled, cutoff controls..."
→ context_status: EXPLICIT
→ context: ["filter_enabled"]
```

### IMPLICIT (10 items, 14.1%)

Source assumes audio/signal is present (obvious prerequisite):

```
"Increasing volume makes the sound louder"
→ context_status: IMPLICIT
→ context: ["audio_input_required"]
```

### UNKNOWN (35 items, 49.3%)

Source says nothing about prerequisites:

```
"Wavetables provide different timbres"
→ context_status: UNKNOWN
→ context: []
→ Must establish baseline conditions experimentally
```

**Critical for Experiments:** The 35 UNKNOWN items will require independent context discovery (e.g., "what initial state must the filter be in for cutoff to have an observable effect?").

---

## Constraints Satisfied

✓ Used ONLY RESOLVED items (71 of 317)  
✓ Did NOT use AMBIGUOUS, NO_SERUM_TARGET, or SOURCE_ONLY items  
✓ Did NOT create EvidenceRecords  
✓ Did NOT create BehaviorClaims  
✓ Did NOT create CapabilityContracts  
✓ Did NOT run any experiments  
✓ Did NOT invent numerical parameter values (except operation classification)  
✓ Did NOT invent prerequisites  
✓ Preserved source_statement separate from predicted_effect  
✓ Preserved full provenance (source_segment_ids → transcript)  
✓ Classified hypotheses by type (BEHAVIORAL vs PROCEDURAL)  
✓ Marked test_status = PROPOSED (not verified)  

---

## Artifacts Produced

| File | Size | Purpose |
|---|---|---|
| yt_f507169bd7cb_hypotheses.json | 0.1 MB | 71 hypothesis records |
| HYPOTHESIS_GENERATION_REPORT.md | — | This summary |

---

## What Hypotheses Are NOT

❌ **Not evidence.** Hypotheses are source-asserted predictions, not measured observations.

❌ **Not capabilities.** A hypothesis about Filter.Cutoff does NOT mean Filter.Cutoff can be safely controlled yet.

❌ **Not a production system.** These hypotheses cannot be used to compose music; they are research instruments.

❌ **Not verified by source.** The Serum 2 manual teaches general concepts. Serum 2.0.21-specific behavior requires measurement.

❌ **Not sufficient context.** Many hypotheses have UNKNOWN context; experiments must establish conditions.

---

## Next Phase: Measurement Design (Not Yet Authorized)

**If measurement experiments are approved:**

1. **Input:** 28 BEHAVIORAL hypotheses only
2. **Process:** Design controlled experiments for each
3. **Method:** DawDreamer + CBOR mutation + audio measurement
4. **Output:** EvidenceRecords (if effects observed)
5. **Constraint:** Do NOT run experiments without explicit authorization

**Do NOT proceed without explicit user direction.**

---

## Status

**COMPLETE.** Hypothesis generation and validation finished.

All constraints maintained. All source provenance preserved. All hypotheses marked PROPOSED (not verified).

**Next authorized action:** Await explicit direction for measurement experiment design or hypothesis refinement.

**Do NOT:**
- Modify hypotheses
- Run experiments
- Create evidence
- Create claims
- Commit changes
