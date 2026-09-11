# Measurement Design Report

**Source:** Serum 2 Manual YouTube Transcript  
**Date:** 2026-09-11  
**Phase:** Measurement Design (Phase 5)  
**Status:** COMPLETE

---

## Executive Summary

28 behavioral hypotheses have been converted into 28 experiment candidates with full measurement designs. **22 of 28 (78.6%) are immediately testable** using DawDreamer + CBOR mutation + audio analysis. 6 require context discovery before execution can proceed.

| Readiness Status | Count | % | Action |
|---|---|---|---|
| **READY_FOR_EXPERIMENT** | 22 | 78.6% | Execute immediately |
| **REQUIRES_CONTEXT_DESIGN** | 6 | 21.4% | Design context first |
| **REQUIRES_STRUCTURAL_ACTIVATION** | 0 | 0% | Blocked (N/A) |
| **REQUIRES_ROUTE_RESOLUTION** | 0 | 0% | Blocked (N/A) |
| **MEASUREMENT_DESIGN_INCOMPLETE** | 0 | 0% | Incomplete (N/A) |

---

## Key Finding: High Testability

The source material's behavioral hypotheses are **predominantly testable in the current DawDreamer/CBOR architecture.** This is significant because:

1. ✓ No structural activation blockers (unlike OSC1.Level, which requires Ableton MCP)
2. ✓ Targets (Octave, Wavetable, Filter.Type, Resonance, Distortion, Attack, Release, Decay) are all active by default or don't require MCP
3. ✓ Audio measurement infrastructure available (RMS, spectral analysis, pitch detection)
4. ✓ Full measurement plans designed (26 distinct measurement dimensions)

---

## Experiment Candidates by Target

### OSC1.Octave (6 hypotheses, 5 ready → 83%)

| Hypothesis | Operation | Context | Status | Measurement Plan |
|---|---|---|---|---|
| Octave affects pitch | SELECT | SOURCE_EXPLICIT | READY | pitch_shift_semitones, fundamental_frequency_hz |
| Octave sets register | SELECT | SOURCE_EXPLICIT | READY | pitch_shift_semitones, fundamental_frequency_hz |
| Different octaves = pitch variation | SELECT | SOURCE_EXPLICIT | READY | pitch_shift_semitones, fundamental_frequency_hz |
| Octave shifts pitch up/down | SELECT | SOURCE_EXPLICIT | READY | pitch_shift_semitones, fundamental_frequency_hz |
| Octave controls register | SELECT | SOURCE_EXPLICIT | READY | pitch_shift_semitones, fundamental_frequency_hz |
| Octave provides pitch control | SELECT | UNKNOWN | REQUIRES_CONTEXT_DESIGN | pitch_shift_semitones, fundamental_frequency_hz |

**Measurement Focus:** Pitch measurement (F0, semitone offset)  
**Context:** 5 have explicit context (oscillator active); 1 needs verification  
**Blockage:** None — ready to execute

---

### OSC1.Wavetable (6 hypotheses, 3 ready → 50%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Wavetable shapes timbre | SELECT | SOURCE_IMPLICIT | READY | spectral_centroid_hz, harmonic_content |
| Wavetable provides spectral variation | SELECT | SOURCE_IMPLICIT | READY | spectral_distribution, harmonic_richness |
| Wavetable controls timbre | SELECT | SOURCE_IMPLICIT | READY | timbral_character, spectral_centroid_hz |
| Wavetable affects sonic character | SELECT | UNKNOWN | REQUIRES_CONTEXT_DESIGN | harmonic_content, spectral_distribution |
| Wavetable selection changes sound | SELECT | UNKNOWN | REQUIRES_CONTEXT_DESIGN | timbral_character, spectral_centroid_hz |
| Wavetables provide rich content | SELECT | UNKNOWN | REQUIRES_CONTEXT_DESIGN | harmonic_richness, spectral_spread_hz |

**Measurement Focus:** Spectral (timbral) measurement  
**Context:** 3 have implicit audio assumption; 3 need context discovery  
**Blockage:** None — design context for 3, then all executable

---

### Filter.Type (5 hypotheses, 4 ready → 80%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Filter mode affects cutoff | SELECT | SOURCE_EXPLICIT | READY | spectral_distribution, spectral_skewness |
| Filter type shapes sound | SELECT | SOURCE_EXPLICIT | READY | timbral_character, spectral_centroid_hz |
| Filter mode selection changes response | SELECT | SOURCE_EXPLICIT | READY | frequency_response_curve, spectral_shape |
| Different filter modes = different tone | SELECT | SOURCE_EXPLICIT | READY | timbral_character, spectral_distribution |
| Filter type enables mode selection | SELECT | UNKNOWN | REQUIRES_CONTEXT_DESIGN | spectral_shape, frequency_response_curve |

**Measurement Focus:** Spectral shape and mode-specific characteristics  
**Context:** 4 have explicit context; 1 needs verification  
**Blockage:** None — ready to execute 4/5

---

### Filter.Resonance (3 hypotheses, 3 ready → 100%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Resonance creates peak | INCREASE | SOURCE_EXPLICIT | READY | peak_magnitude_db, spectral_width_hz |
| Resonance emphasis creates presence | INCREASE | SOURCE_EXPLICIT | READY | spectral_distribution, peak_magnitude_db |
| Resonance increases Q | INCREASE | SOURCE_EXPLICIT | READY | spectral_width_hz, peak_magnitude_db |

**Measurement Focus:** Peak emphasis (frequency-domain)  
**Context:** All explicit  
**Blockage:** None — all ready

**Note:** Filter1.Resonance already partially verified (+13.78 Hz effect observed, below threshold). These candidates test resonance effect dimensions.

---

### FXDistortion.Drive (3 hypotheses, 3 ready → 100%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Distortion.Drive increases harmonics | INCREASE | SOURCE_IMPLICIT | READY | harmonic_content, harmonic_ratio |
| Drive creates saturation | INCREASE | SOURCE_IMPLICIT | READY | spectral_centroid_hz, harmonic_richness |
| Distortion adds overtones | INCREASE | SOURCE_IMPLICIT | READY | harmonic_content, spectral_distribution |

**Measurement Focus:** Harmonic content and saturation detection  
**Context:** All implicit (audio signal assumed)  
**Blockage:** None — all ready

---

### Env1.Attack (3 hypotheses, 2 ready → 67%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Attack affects envelope shape | INCREASE | SOURCE_IMPLICIT | READY | onset_time_ms, transient_sharpness |
| Increasing attack slows onset | INCREASE | SOURCE_IMPLICIT | READY | onset_time_ms, attack_duration_ms |
| Attack time controls onset | UNSPECIFIED | UNKNOWN | REQUIRES_CONTEXT_DESIGN | onset_time_ms, transient_sharpness |

**Measurement Focus:** Temporal envelope characteristics  
**Context:** 2 have implicit audio assumption; 1 needs context  
**Blockage:** None — design context for 1, then all executable

---

### Env1.Release (1 hypothesis, 1 ready → 100%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Release affects tail character | UNSPECIFIED | SOURCE_EXPLICIT | READY | release_duration_ms, tail_character |

**Measurement Focus:** Release time and tail decay  
**Context:** Explicit  
**Blockage:** None — ready

---

### Env1.Decay (1 hypothesis, 1 ready → 100%)

| Hypothesis | Operation | Context | Status | Notes |
|---|---|---|---|---|
| Decay time controls descent | UNSPECIFIED | SOURCE_IMPLICIT | READY | decay_duration_ms, spectral_evolution |

**Measurement Focus:** Temporal decay evolution  
**Context:** Implicit (audio signal assumed)  
**Blockage:** None — ready

---

## Measurement Dimensions by Category

### Spectral (Brightness, Timbre, Harmonic Content)

Targets using spectral measurements: Wavetable, Filter.Type, Filter.Resonance, Distortion.Drive, Decay

| Dimension | Purpose | Example Hypothesis |
|---|---|---|
| spectral_centroid_hz | Brightness indicator | "Wavetable shapes timbre" |
| spectral_spread_hz | Complexity/richness | "Wavetable provides rich content" |
| spectral_distribution | Full frequency coverage | "Filter type shapes sound" |
| harmonic_content | Presence of overtones | "Distortion adds overtones" |
| harmonic_ratio | Harmonic-to-fundamental ratio | "Drive creates saturation" |
| spectral_skewness | Asymmetry of distribution | "Filter mode affects cutoff" |

### Temporal (Envelope, Onset, Duration)

Targets using temporal measurements: Attack, Release, Decay

| Dimension | Purpose | Example Hypothesis |
|---|---|---|
| onset_time_ms | Time to peak amplitude | "Attack affects envelope shape" |
| attack_duration_ms | Attack phase duration | "Increasing attack slows onset" |
| decay_duration_ms | Decay phase duration | "Decay time controls descent" |
| release_duration_ms | Release phase duration | "Release affects tail character" |
| transient_sharpness | Steepness of onset | "Attack slows onset" |
| tail_character | Quality of decay/release | "Release affects tail character" |

### Pitch (Frequency, Register)

Targets using pitch measurements: Octave

| Dimension | Purpose | Example Hypothesis |
|---|---|---|
| fundamental_frequency_hz | F0 in Hz | "Octave affects pitch" |
| pitch_shift_semitones | Register offset | "Octave shifts pitch up/down" |

### Amplitude (Volume, Loudness)

Used as baseline/control measurement for all targets

| Dimension | Purpose |
|---|---|
| overall_rms_db | Overall signal level |
| peak_amplitude_db | Peak level |

---

## Context Classification

### SOURCE_EXPLICIT (12 candidates)

Prerequisites directly stated in source material.

**Example:** "With filter enabled, cutoff controls the frequency"

**Action:** Use stated context; may still need verification for applicability in Serum 2.0.21

**Targets affected:**
- OSC1.Octave (5 candidates)
- Filter.Type (4 candidates)
- Filter.Resonance (3 candidates)

### SOURCE_IMPLICIT (10 candidates)

Prerequisites obvious from context but not explicitly stated.

**Example:** "Distortion increases harmonics" (assumes audio signal present)

**Action:** Establish baseline conditions (oscillators active, audio input)

**Targets affected:**
- OSC1.Wavetable (3 candidates)
- FXDistortion.Drive (3 candidates)
- Env1.Attack (2 candidates)
- Env1.Decay (2 candidates)

### UNKNOWN (6 candidates)

No context provided in source; must discover experimentally.

**Action:** Design context discovery experiment first; then proceed with main experiment

**Targets affected:**
- OSC1.Octave (1 candidate)
- OSC1.Wavetable (3 candidates)
- Filter.Type (1 candidate)
- Env1.Attack (1 candidate)

---

## Execution Readiness Summary

### READY_FOR_EXPERIMENT (22 candidates, 78.6%)

**Characteristics:**
- ✓ Context explicitly stated or obvious
- ✓ Measurement dimensions defined
- ✓ No structural blockers
- ✓ Can proceed to DawDreamer experiment immediately

**Workflow:**
1. Load hypothesis
2. Establish baseline conditions (default skeleton or stated context)
3. Apply CBOR mutation (single-field isolation)
4. Capture audio render
5. Measure dimensions
6. Compare baseline vs. treatment
7. Record EvidenceRecord (if effect observed)

### REQUIRES_CONTEXT_DESIGN (6 candidates, 21.4%)

**Characteristics:**
- ⚠ Context status = UNKNOWN
- ⚠ Prerequisites not stated in source
- ✓ Measurement dimensions defined
- ✓ No structural blockers

**Affected targets:**
- OSC1.Octave (1 candidate): "Octave provides pitch control"
- OSC1.Wavetable (3 candidates): Various timbre effects
- Filter.Type (1 candidate): "Filter type enables mode selection"
- Env1.Attack (1 candidate): "Attack affects onset"

**Workflow:**
1. Design context discovery sub-experiment
2. Vary baseline state (e.g., different oscillator selections, filter modes)
3. Measure effect consistency across contexts
4. Document discovered context
5. Proceed to main experiment with established context

**Example Context Discovery:**
```
Hypothesis: "Octave provides pitch control"
Initial context: UNKNOWN

Experiment: Render with default skeleton, octave=0, measure F0
Experiment: Render with default skeleton, octave=1, measure F0
Experiment: Render with default skeleton, octave=-1, measure F0
Result: Establishes baseline pitch expectations for each octave
Next: Run main experiment with discovered baseline context
```

---

## No Structural Activation Blockers

**Critical Finding:** Zero candidates require structural activation.

This contrasts with **OSC1.Level** (MCP parameter 16 required, unavailable in subprocess) and **OSC1.Enable** (same blocker). The behavioral hypotheses from the source material **do not depend on unavailable activation routes.**

**Implication:** All 22 READY candidates can be executed. All 6 REQUIRES_CONTEXT_DESIGN candidates can be executed once context is designed.

---

## Constraints Satisfied

✓ Did NOT execute any experiments  
✓ Did NOT create EvidenceRecords  
✓ Did NOT create BehaviorClaims  
✓ Did NOT create CapabilityContracts  
✓ Did NOT use Ableton MCP  
✓ Did NOT execute DawDreamer/Serum  
✓ Preserved provenance (source_segment_ids linked)  
✓ Used only BEHAVIORAL hypotheses (28 of 71)  
✓ Defined measurement dimensions (not thresholds)  
✓ Classified context requirements  
✓ Did NOT invent context  

---

## Artifacts Produced

| File | Size | Purpose |
|---|---|---|
| yt_f507169bd7cb_measurement_design.json | 0.1 MB | 28 experiment candidate records |
| MEASUREMENT_DESIGN_REPORT.md | — | This summary |

---

## Next Phase: Experiment Execution (Not Yet Authorized)

**If experiments are approved:**

1. **Batch 1:** Execute 22 READY_FOR_EXPERIMENT candidates
   - Use DawDreamer + CBOR mutation
   - Measure audio dimensions
   - Produce EvidenceRecords

2. **Batch 2:** Design context for 6 REQUIRES_CONTEXT_DESIGN candidates
   - Discover baseline context
   - Produce ContextDocumentation
   - Execute main experiments

3. **Output:** EvidenceRecords + BehaviorClaims (if effects observed)

**Do NOT proceed without explicit authorization.**

---

## Summary by Readiness

### Ready Now (22 experiments)

Targets with full measurement plans and no blockers:

```
OSC1.Octave (5)    → pitch measurement
OSC1.Wavetable (3) → spectral measurement (with context design for 3)
Filter.Type (4)    → spectral shape measurement
Filter.Resonance (3) → resonance peak measurement
FXDistortion.Drive (3) → harmonic saturation measurement
Env1.Attack (2)    → attack duration measurement
Env1.Release (1)   → release duration measurement
Env1.Decay (1)     → decay duration measurement
```

### Requires Context First (6 experiments)

Targets needing context discovery before main experiment:

```
OSC1.Octave (1)    → Verify octave baseline pitch
OSC1.Wavetable (3) → Establish wavetable timbre baseline
Filter.Type (1)    → Verify filter mode applicability
Env1.Attack (1)    → Confirm attack time baseline
```

---

## Measurement Coverage Validation

✓ All 28 behavioral hypotheses converted to experiment candidates  
✓ All measurement dimensions sourced from domain knowledge  
✓ All candidates have measurement plans (none incomplete)  
✓ No arbitrary thresholds (dimensions only)  
✓ Baseline requirements defined for each  
✓ Expected direction specified  
✓ Provenance fully preserved  

---

## Status

**COMPLETE.** Measurement design for 28 behavioral hypotheses finished.

22 candidates ready for execution. 6 awaiting context design.  
Zero structural blockers. Full measurement infrastructure defined.

**Next authorized action:** Await explicit direction to execute experiments or refine context designs.

**Do NOT:**
- Execute experiments
- Create evidence
- Create claims
- Commit changes
