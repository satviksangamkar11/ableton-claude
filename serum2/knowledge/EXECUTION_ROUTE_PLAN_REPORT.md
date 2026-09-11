# Execution Route Selection Report

**Source:** Serum 2 Manual YouTube Transcript  
**Date:** 2026-09-11  
**Phase:** Execution Route Selection (Phase 8)  
**Status:** COMPLETE

---

## Executive Summary

An execution route classification system has been implemented to determine which execution environment can satisfy each behavioral hypothesis.

**Critical Finding:** **All 28 behavioral hypotheses require ABLETON_MCP.**

| Route | Count | % | Targets |
|---|---|---|---|
| **ABLETON_MCP** | 28 | 100% | OSC1.Octave, OSC1.Wavetable, Filter.Type, Filter.Resonance, FXDistortion.Drive, Env1.Attack/Release/Decay |
| **DAWDREAMER_SUBPROCESS** | 0 | 0% | (No hypotheses qualify) |
| **BLOCKED** | 0 | 0% | (None) |

---

## Execution Routes Defined

### DAWDREAMER_SUBPROCESS
- **Use case:** Single-field CBOR mutations on default skeleton
- **Prerequisites:** No MCP activation required
- **Targets:** Filter1.Cutoff (already proven), Filter1.Resonance (partial)
- **Status:** Available but no new candidates require it

### ABLETON_MCP
- **Use case:** MCP parameter control on live Ableton session
- **Prerequisites:** Ableton Live running, Serum VST3 loaded, MCP connection
- **Targets:** All 28 behavioral hypotheses (all require OSC1 or routing activation)
- **Status:** Required for all remaining work

### BLOCKED
- **Use case:** Hypotheses with no available execution path
- **Count:** 0 (all 28 can route to ABLETON_MCP)

---

## Route Classification by Target

### OSC1.Octave (6 hypotheses)
```
Route: ABLETON_MCP
Prerequisite: OSC1.Enable (MCP Parameter 16 "A Enable")
Activation mechanism: Ableton MCP only
Reason: Oscillator must be enabled through live Ableton MCP
```

### OSC1.Wavetable (6 hypotheses)
```
Route: ABLETON_MCP
Prerequisite: OSC1.Enable (MCP Parameter 16 "A Enable")
Activation mechanism: Ableton MCP only
Reason: Oscillator must be enabled through live Ableton MCP
```

### Filter.Type (5 hypotheses)
```
Route: ABLETON_MCP
Prerequisite: OSC1 audio input (requires OSC1.Enable)
Activation mechanism: Ableton MCP Parameter 16
Reason: Filter.Type needs active oscillator input; OSC activation via MCP only
```

### Filter.Resonance (3 hypotheses)
```
Route: ABLETON_MCP
Prerequisite: OSC1 audio input (requires OSC1.Enable)
Activation mechanism: Ableton MCP Parameter 16
Reason: Resonance peak only observable with audio input; OSC activation via MCP only
```

### FXDistortion.Drive (3 hypotheses)
```
Route: ABLETON_MCP
Prerequisite: OSC1 audio input (requires OSC1.Enable)
Activation mechanism: Ableton MCP Parameter 16
Reason: Distortion needs audio input; OSC activation via MCP only
```

### Env1.Attack/Release/Decay (5 hypotheses)
```
Route: ABLETON_MCP
Prerequisite: Env0 routing + OSC1.Enable
Activation mechanism: Structural routing (unavailable via CBOR) + MCP Parameter 16
Reason: Envelopes need routing target and OSC active; both require MCP
```

---

## Critical Architectural Insight

**All 28 hypotheses depend on OSC1.Enable activation.**

This is the **fundamental blocker** that prevents DawDreamer subprocess execution:

```
OSC1.Enable
  ├─ Ableton MCP Parameter 16 ("A Enable")
  ├─ Available in: Live session only
  └─ NOT available in: DawDreamer subprocess (MCP doesn't propagate)
```

**Result:** No DAWDREAMER_SUBPROCESS candidates remain. All 28 require ABLETON_MCP.

---

## Proof-of-Concept Experiment: OSC1.Octave

**Selected:** exp_cand_000000  
**Target:** OSC1.Octave  
**Route:** ABLETON_MCP  
**Status:** READY FOR EXECUTION (if Ableton available)

### Experiment Sequence

```
1. READ: A Enable (MCP Param 16)
   └─ Record baseline state

2. SET: A Enable = 1.0 (if not already 1.0)
   └─ COMMAND → OBSERVED → EVIDENCE

3. ESTABLISH BASELINE
   └─ Render audio with OSC1 active
   └─ Measure fundamental frequency (F0)
   └─ Record: f0_baseline_hz, rms_baseline_db

4. INTERVENE: OSC1.Octave += 1
   └─ Read current octave via MCP
   └─ Set octave to (current + 1)
   └─ COMMAND → OBSERVED → EVIDENCE

5. ESTABLISH TREATMENT
   └─ Render audio with OSC1 at new octave
   └─ Measure fundamental frequency (F0)
   └─ Record: f0_treatment_hz, rms_treatment_db

6. CALCULATE EFFECT
   └─ delta_f0_hz = f0_treatment_hz - f0_baseline_hz
   └─ delta_semitones = 12 * log2(f0_treatment_hz / f0_baseline_hz)
   └─ Expected: +12 semitones (one octave)

7. RESTORE: Octave to baseline
   └─ Set octave back to original value
   └─ COMMAND → OBSERVED → EVIDENCE

8. RESTORE: A Enable to baseline
   └─ Set A Enable back to original state
   └─ COMMAND → OBSERVED → EVIDENCE

9. VERIFY: Read both values
   └─ Confirm octave = baseline
   └─ Confirm A Enable = baseline
```

### Measurement Plan

| Dimension | Baseline | Treatment | Delta | Expected |
|---|---|---|---|---|
| fundamental_frequency_hz | Read | Read | Δf0 | +double (12 semitones) |
| pitch_shift_semitones | 0 | Calculate | Δ12 | +12 |
| overall_rms_db | Read | Read | ΔdB | minimal (level unchanged) |

### Constraints

✓ **NO DawDreamer subprocess** — would create separate Serum instance  
✓ **ONLY Ableton Live MCP** — live session control  
✓ **FULL FORENSIC LOGGING** — every command, every readback  
✓ **PRESERVE ALL EVIDENCE** — no simulated results  

---

## Ableton MCP Requirements

To execute the OSC1.Octave proof:

1. **Ableton Live running**  
2. **Serum VST3 loaded in an audio track**  
3. **MCP connection active** (Remote Script running)  
4. **MIDI note playing** (to hear pitch change, optional for measurement)  

---

## Artifacts Produced

| File | Purpose |
|---|---|
| yt_f507169bd7cb_execution_route_plan.json | Route classification + proof plan |
| EXECUTION_ROUTE_PLAN_REPORT.md | This report |

---

## Status Report

### Route Classification
✓ Complete. All 28 mapped to ABLETON_MCP.

### MCP Infrastructure
⚠ Not available in current environment (ableton_mcp_tools not found).

### Proof Experiment Plan
✓ Designed. exp_cand_000000 (OSC1.Octave) ready for execution.

### Readiness
- **If Ableton Live available:** Execute OSC1.Octave proof immediately
- **If Ableton unavailable:** Plan preserved; can execute when Ableton starts

---

## Key Insight: Route Selection Determines Execution Environment

| Scenario | Experiment | Route | Execute | Notes |
|---|---|---|---|---|
| Current (subprocess only) | OSC1.Octave | ABLETON_MCP | NOT_YET | Ableton not available |
| With Ableton running | OSC1.Octave | ABLETON_MCP | YES | Use live session |
| Previous (subprocess only) | Filter1.Cutoff | DAWDREAMER | YES | Can still test in subprocess |

---

## Next Authorized Actions

**When Ableton becomes available:**
1. Launch execution script with Ableton Live running
2. Execute OSC1.Octave proof with full forensic logging
3. Measure pitch shift and RMS
4. Record evidence

**Do NOT (any time):**
- Execute other 27 hypotheses (only proof-of-concept authorized)
- Rerun blocked DawDreamer experiments
- Create BehaviorClaims or CapabilityContracts
- Modify source/semantic/hypothesis artifacts

---

## Summary

**Execution route classification complete.** All 28 behavioral hypotheses require **ABLETON_MCP.**

**Proof experiment designed:** OSC1.Octave (exp_cand_000000)  
**Status:** Ready for execution when Ableton Live available.

**Forensic integrity:** Full COMMAND → OBSERVED → EVIDENCE logging planned.

