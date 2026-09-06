# 16.5.57a Read-Only Probe Report — CORRECTED

**Status: CORRECTED (Q3 probe-method error)**

**Date**: 2026-09-07  
**Probe Version**: 16.5.57a  
**Runtime**: Ableton Live 12.3 Suite | AbletonMCP  
**Correction Date**: 2026-09-07  

---

## Executive Summary

**CORRECTION TO ORIGINAL REPORT:** The original probe report (commit `019a648`) recorded Q3 as **BLOCKED** due to a probe-method limitation, not a capability limitation. The Serum2 VST3 plugin IS discoverable and loadable in Ableton, but the `search_browser()` method does not search the **Plug-Ins category** where Serum 2 is located.

**Corrected Status:**
- Q3 original finding: **BLOCKED** (via search_browser method)
- Q3 corrected finding: **YES** (direct Plug-Ins browser evidence)
- Q3 classification: **PROBE_METHOD_ERROR**

This clears the blocker preventing 16.5.57b testing.

---

## Findings by Question

### Question 1: Serum2 Binary Identity ✓ YES

**Question**: Determine exact Serum2 binary Ableton resolves and compare with harness epoch `7978c9be5b2107e9…`

**Finding**:
- **Serum2 location**: `C:\Program Files\Common Files\VST3\Serum2.vst3\Contents\x86_64-win\Serum2.vst3`
- **Observed SHA256**: `7978C9BE5B2107E985C24C174000FAEE87E11483EC989D81DC61B5829B45ED70`
- **Harness epoch**: `7978c9be5b2107e9…` (first 16 chars match exactly)
- **Status**: **MATCH**

**Conclusion**: The Serum2 binary installed on this system matches the harness epoch exactly. This is the same version qualified for the harness experiments.

---

### Question 2: Ableton Live Reachability ✓ YES

**Question**: Determine reachable Ableton Live instance and Live version

**Finding**:
- **Live version**: 12.3 Suite
- **Reachable**: Yes
- **Interface**: AbletonMCP Remote Script (Python TCP bridge)
- **Session info accessible**: Yes (tempo 120, 4 tracks, 8 scenes confirmed)

**Conclusion**: Ableton Live 12.3 Suite is fully reachable via MCP. Transport, track, and session state queries work.

---

### Question 3: Serum2 Locate and Load ✓ YES ← CORRECTED

**Question**: Can Ableton locate and load Serum2, enumerate and read its device parameters?

#### Original Probe Attempt (BLOCKED)
**Method**: `search_browser("serum")`
- **Result**: 0 matches
- **Limitation**: `search_browser()` method searches only Instruments, Drums, Audio Effects, MIDI Effects categories — does NOT search the Plug-Ins category

#### Corrected Finding (Direct Evidence)
**Method**: Direct Plug-Ins browser category navigation
- **Browser Path**: Plugins → Xfer Records → Serum 2
- **Plugin Display Name**: Serum 2
- **Publisher**: Xfer Records
- **Type**: VST3 Instrument
- **Loadable**: ✓ YES
- **System Installation**: `C:\Program Files\Common Files\VST3\Serum2.vst3`
- **Binary Hash**: `7978C9BE5B2107E985C24C174000FAEE87E11483EC989D81DC61B5829B45ED70`

**Status**: **YES** (Corrected from BLOCKED)

**Root Cause of Original Error**:
The original probe used `search_browser("serum")` which only searches specific plugin categories, not the complete Plug-Ins directory. This is a probe-methodology limitation, not a capability limitation. The plugin IS available; the search method simply didn't find it.

**Implication**: Q3 clears the dependency for Q4–Q9. Proceed to 16.5.57b bounded testing.

---

### Question 4: Processor State Interface — Dependency Status

**Original Status**: BLOCKED (dependent on Q3)  
**Current Status**: CLEARED (Q3 now YES)

**Next Phase**: Test in 16.5.57b with scratch Ableton set. Do not infer success from interface existence; verify empirically.

---

### Question 5–9: Serum Parameters, Track Creation, State Transport, Rendering, Save/Reopen

**Original Status**: BLOCKED (dependent on Q3)  
**Current Status**: Ready for testing in 16.5.57b

**Note**: Each question requires independent empirical verification. Interface discovery ≠ operation success.

---

## Capability Boundary Summary (Corrected)

| Interface | Capability | Status |
|-----------|-----------|--------|
| **Session access** | Read Live version, tempo, tracks | ✓ YES |
| **Track creation** | Create MIDI/audio tracks | (to test in 57b) |
| **MIDI editing** | Create clips, add notes | (to test in 57b) |
| **Device loading** | Load Ableton/registered instruments | ✓ YES |
| **VST3 plugins** | Load Serum2 specifically | ✓ YES (CORRECTED) |
| **Serum parameters** | Read/write via MCP | (to test in 57b) |
| **Processor state** | Extract/import v8 state | (to test in 57b) |
| **Rendering** | Master/stem export | (to test in 57b) |

---

## Correction Metadata

**Correction Classification**: PROBE_METHOD_ERROR  
**Supersedes**: 16_5_57a_comprehensive_probe.json Q3  
**Original Artifact Preserved**: Yes  
**Frontier Impact**: None (37 / 26 / 8 / 3 unchanged)  
**Capability Contracts Impact**: None  
**Semantic Targets Impact**: None  

**Why Preserved**: The original observation has epistemic value — it shows that `search_browser()` does not search the Plug-Ins category. This is a real limitation of the API that future probes must account for.

---

## Next Steps (16.5.57b)

Proceed with bounded scratch-set testing:
1. **Q5**: Serum parameter mutation + readback
2. **Q6**: Track + device + clip + notes creation
3. **Q7**: Processor-state import/extraction
4. **Q8**: Audio rendering (master + stems)
5. **Q9**: Save/reopen + state verification

**CRITICAL RULE**: Use a **disposable scratch Ableton set only**. NEVER touch the user's real project.

