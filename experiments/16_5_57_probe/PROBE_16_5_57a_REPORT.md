# 16.5.57a Read-Only Probe Report

**Status: BLOCKED**

**Date**: 2026-09-07  
**Probe Version**: 16.5.57a  
**Runtime**: Ableton Live 12.3 Suite | AbletonMCP  

---

## Executive Summary

The probe has encountered a critical blocker in question 3: **Serum2 VST3 plugin is not discoverable through the AbletonMCP browser interface**, despite being physically installed on the system in the standard VST3 directory.

This blocks the ability to:
- Load Serum2 into an Ableton track (question 3)
- Read Serum2 device parameters (question 3)
- Test processor state extraction (question 4)
- Proceed to 16.5.57b bounded testing

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

### Question 3: Serum2 Locate and Load ✗ BLOCKED

**Question**: Can Ableton locate and load Serum2, enumerate and read its device parameters?

**Evidence**:
1. **Browser search**: `search_browser("serum")` returned 0 matches
2. **Instruments browser**: Only Ableton built-in instruments visible (Analog, Collision, Drift, Wavetable, etc.)
3. **System installation**: Serum2.vst3 exists in `C:\Program Files\Common Files\VST3\`
4. **Other VST3 plugins in directory**:
   - Midee Plugin.vst3 ✓
   - Scaler 3 Audio.vst3 ✓
   - Scaler 3.vst3 ✓
   - **Serum2.vst3** ✗ (not discoverable)
   - Analog Lab V.vst3 ✓
   - Massive.vst3 ✓
   - Ripchord.vst3 ✓
   - SPAN.vst3 ✓
   - Vital.vst3 ✓
5. **MCP tool limitations**: `load_instrument_or_effect()` requires a browser URI; no way to load unregistered plugins

**Status**: **BLOCKED**

**Root Cause Options**:
1. Ableton VST3 plugin scanning incomplete or misconfigured
2. Serum2 not properly registered in Windows registry for VST3
3. AbletonMCP browser API does not expose all VST3 plugins
4. Serum2 VST3 version incompatibility with Ableton 12.3 Suite

**Implication**: Cannot proceed to test Serum2 device parameter reading, processor state extraction, or any Serum-specific functionality through this interface.

---

### Questions 4–8: Processor State, MIDI, Rendering

**Status**: **BLOCKED** (Dependent on Question 3 resolution)

Unable to test:
- Processor state import/extraction (Q4)
- Serum parameter mutation/readback (57b Q5)
- Serum on tracks (57b Q6)

**Can test independently** (do not require Serum):
- Track creation: `create_midi_track()` available
- MIDI clip creation: `create_clip()` available
- MIDI note editing: `add_notes_to_clip()` available
- Rendering capabilities: (to be determined)

---

## Capability Boundary Summary

| Interface | Capability | Status |
|-----------|-----------|--------|
| **Session access** | Read Live version, tempo, tracks | ✓ YES |
| **Track creation** | Create MIDI/audio tracks | ✓ YES (untested but tools exist) |
| **MIDI editing** | Create clips, add notes | ✓ YES (tools exist) |
| **Device loading** | Load Ableton/registered instruments | ✓ YES |
| **VST3 plugins** | Load Serum2 specifically | ✗ NO |
| **Serum parameters** | Read/write via MCP | ✗ BLOCKED (can't load) |
| **Processor state** | Extract/import v8 state | ? BLOCKED (can't load) |
| **Rendering** | Master/stem export | ? UNKNOWN |

---

## Recommendation for Roadmap

**16.5.57 cannot proceed to 16.5.57b without resolving Serum2 accessibility.**

Options:
1. **Investigate Serum2 VST3 registration** — Check Windows VST3 plugin registry or Ableton's plugin cache
2. **Force plugin rescanning** — Trigger Ableton's plugin discovery explicitly (if MCP tool exists)
3. **Use alternative VST version** — Check if Serum2 VST2 is available and visible to Ableton
4. **Use direct file manipulation** — If processor state can be serialized without loading Serum, test that path
5. **Mark as system limitation** — If Ableton/VST3 combination is fundamentally incompatible with this Serum2 installation, document and move forward with what IS available

---

## Next Steps

**Do not proceed to 16.5.57b yet.**

1. Determine root cause of Serum2 VST3 discovery failure
2. If fixable: Resolve and re-run 16.5.57a Q3
3. If unfixable: Escalate to roadmap — may need to redesign vertical slice without Serum mutation testing
