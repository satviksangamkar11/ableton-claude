# 16.5.57 Probe Summary — Host Capability Boundary

**Status**: COMPLETE (with corrections and unresolved unknowns)  
**Date**: 2026-09-07  
**Phase**: Frozen step 16.5.57 (AbletonMCP feasibility probe)

---

## Executive Summary

16.5.57 has determined the **factual host capability boundary** for Ableton Live 12.3 Suite + AbletonMCP + Serum 2.0.21.

| Capability | Status | Evidence |
|---|---|---|
| **Serum discovery** | YES | Direct navigation to Plugins → Xfer Records → Serum 2 |
| **Parameter read** | YES | get_device_parameters() returns parameter list |
| **Parameter mutation (Configure Mode)** | YES — one tested param only | OSC1.Volume/"A Level" mutated via Configure + AbletonMCP; visual Serum confirmation |
| **Parameter persistence** | UNVERIFIED | Save/reopen attempted but not directly observed |
| **Processor-state import (MCP)** | NO | No MCP tool exists |
| **Processor-state extraction (read-only)** | YES | Deterministically located in .als XML and extracted |
| **Processor-state injection** | UNTESTED | Mutation capability unknown; not attempted |
| **Audio capture (File→Export)** | BLOCKED | render_to_file() does not exist; record_section is real-time only |
| **Audio capture (real-time resampling)** | LIKELY YES | record_section mechanism exists; suitability TBD |
| **Set save/reopen** | UNKNOWN | MCP lacks save/close/open tools; user GUI only |

---

## Key Findings

### 1. Parameter Control: Configure Mode + MCP ✓

**Working**:
- Ableton's Configure Mode exposes manually-selected Serum parameters to Live's parameter list
- Once exposed (e.g., OSC1.Volume/"A Level"), AbletonMCP can read/write via `get_device_parameter()` / `set_device_parameter()`
- Serum UI responds to MCP writes (confirmed by visual inspection)

**Scope Limitation**:
- Only ONE parameter tested (OSC1.Volume/"A Level")
- Ableton documentation warns some VST3 plugins don't publish every parameter
- Full coverage unknown; per-parameter verification required

**Persistence**: UNVERIFIED
- Reported as surviving save/reopen, but save and reopen were manual GUI operations
- No direct observation that these operations occurred
- Same failure mode as Q3 (ambiguous signal misinterpreted as verified)
- **Rejected as evidence; marked UNVERIFIED**

---

### 2. Processor-State Structure: Present and Readable ✓

**Working**:
- Serum processor state IS embedded in `.als` files
- Located at deterministic XML path: `/root/LiveSet/Tracks/MidiTrack/DeviceChain/DeviceChain/Devices/PluginDevice/PluginDesc/Vst3PluginInfo/Preset/Vst3Preset/ProcessorState`
- Extraction requires only gzip decompression + XML parsing (no special Ableton APIs)
- Payload is 3,280 bytes of hex-encoded XferJson (Xfer's processor state format)
- Extraction is fully deterministic and repeatable

**Not Working (Yet Untested)**:
- Offline injection: Can a modified `<ProcessorState>` be written back to .als? (UNTESTED)
- Ableton application: Does Ableton apply an injected state when opening the `.als`? (UNTESTED)
- Reverse automation: Can the full cycle (extract → modify → inject → reopen → re-extract) complete end-to-end? (UNTESTED)

---

### 3. Audio Rendering: No Direct Export Tool

**Blocked**: `render_to_file(set_path, master_path, stem_paths)` **does not exist** in AbletonMCP

**Alternative**: `record_section()` (real-time resampling)
- Captures audio by routing Main output to a resampling track
- Records in real time; capped at ~5 minutes per MCP docs
- **Not equivalent to File → Export Audio** (which is batch export, not real-time transport)
- Suitability for 16.6's "render automatically" requirement unclear

---

### 4. Save / Reopen / Session Control: No Automation

**Missing**:
- `save_live_set()` — no confirmed tool to save the active set
- `close_live_set()` — no tool to close without saving (or to close + save)
- `load_live_set()` / `open_live_set()` — no tool to reopen a saved set

**Manual Only**:
- Save/close/reopen cycle requires user GUI interaction
- Any automation of this cycle must be done outside AbletonMCP

---

## Corrections Made in This Run

### R1: Fabrication Retraction
**Problem**: Committed test plan referenced `render_to_file(set_path, master_path, stem_paths)`, which does not exist.  
**Fix**: Q8 section rewritten to document the absence and describe the actual `record_section()` mechanism with its limitations.

### R1: Q5e Persistence Downgraded
**Problem**: Q5e reported as VERIFIED, but save/reopen steps were manual and unobserved.  
**Fix**: Downgraded to UNVERIFIED. Only Q5a-Q5d remain verified.

### R1: Q1 Hash Not Re-Verified
**Problem**: Binary hash verification from prior session (019a648) cannot be inherited without current-runtime re-verification per CLAUDE.md § Rule 5.  
**Fix**: Marked as NOT_RE_VERIFIED_RUNTIME; if 16.5.60A gate depends on it, gate must be re-gated on fresh observation.

---

## Architecture Implications

The evidence now separates two planes:

### State Plane (Processor State)
- **Structural**: Present in `.als` XML, deterministically extractable
- **Functional**: Offline injection unknown, Ableton application unknown
- **Automated**: No MCP tool to import; write/open cycle manual or script-based

### Control Plane (Parameters + MIDI + Arrangement)
- **Configure Mode + MCP**: Working for tested parameter only
- **MIDI/Track/Clip Creation**: AbletonMCP tools exist; untested in this probe
- **Real-Time Audio Capture**: `record_section()` available; export-equivalent TBD

The three candidate architectures from pre-16.5.57 framing (A: Configure, B: State, C: Hybrid) are now more nuanced:

```
A (Configure Mode only)
  ✓ Works for manually configured parameters (one tested)
  ✗ Cannot handle mod-matrix or unmapped parameters
  ? Persistence across save/reopen unverified
  
B (Processor-state only)
  ✓ Structurally present, readable
  ? Offline injection untested
  ? Ableton application untested
  ✗ No MCP import tool; requires script-based injection
  
C (Hybrid)
  ✓ Use state plane for full Serum initialization
  ✓ Use Configure/MCP for run-time tweaking
  ? State injection mechanism unproven
  ? Requires both Q7c success and custom automation layer
```

---

## Unknowns Preserved (Properly Scoped)

| Question | Status | Why |
|---|---|---|
| Do all Serum parameters publish to Configure Mode? | UNKNOWN | Only OSC1.Volume tested |
| Does Configure parameter config survive save/reopen? | UNVERIFIED | Save/reopen not directly observed |
| Can offline .als injection work? | UNTESTED | Requires file mutation; not attempted |
| Does Ableton apply injected processor state on open? | UNTESTED | Would require Live-opening; not attempted |
| Can audio rendering achieve "render automatically" with record_section? | UNKNOWN | Mechanism exists but suitability unclear |
| Can save/close/reopen be automated? | UNKNOWN | No MCP tools; manual workaround only |

---

## Gateway for 16.5.58

16.5.58 (Host Architecture + Automation Boundary Decision) must answer:

1. **Is processor-state transport necessary for 16.6?**
   - If YES: Proceed to Q7c (offline injection test) and Q7d (reverse automation)
   - If NO: Fall back to Configure Mode + MCP for parameter control; use alternative for full-state initialization

2. **Is Configure Mode parameter persistence sufficient?**
   - If YES: Simplify architecture; no state-plane work needed
   - If NO: State plane becomes mandatory; Q7c/Q7d must complete

3. **What renders the final Serum audio?**
   - record_section (real-time)? ← Requires transport running
   - File→Export analogue (batch)? ← Not found in MCP
   - Manual export? ← Not "automatic"

4. **What automates save/close/reopen?**
   - Custom script? ← Adds complexity
   - User GUI? ← Violates "automatically" requirement
   - Unknown path? ← Must be discovered

---

## Frontier Integrity

- **Count**: 37 contracts (26 CAUSAL_VERIFIED, 8 STRUCTURAL_ONLY, 3 NEGATIVE_EVIDENCE) — **UNCHANGED**
- **Provenance**: No new capabilities promoted; corrections only
- **Runtime**: Ableton 12.3 Suite confirmed present; Serum hash NOT_RE_VERIFIED this session

---

## Artifacts and Paths

| Artifact | Path | Status |
|---|---|---|
| Q3 Correction | Q3_CORRECTION.json | COMPLETE |
| Q5 Results (A-D verified, E unverified) | Q5_RESULTS_COMPLETE.md | CORRECTED |
| Q5 Test Plan | Q5_HOST_PARAMETER_LADDER.md | (record only) |
| Q7b Read-Only Probe | Q7b_PROCESSOR_STATE_READPROBE.md | COMPLETE |
| Test Plan (Q6-Q9) | 16_5_57b_TEST_PLAN.md | CORRECTED (Q8) |
| Binary Hash Correction | Q1_BINARY_HASH_CORRECTION.md | NEW |
| Final Results | 16_5_57b_test_results.json | UPDATED |

---

## Commits This Session

| Commit | Message | Changes |
|---|---|---|
| 2c80be1 | 16.5.57-R1: Corrections to render_to_file, Q5e, Q1 | Retracted fabrication; downgraded claims; marked hash unverified |
| 7d03ac7 | 16.5.57-Q7b: Read-only processor-state probe | Q7b PASS; extracted processor state; confirmed structure |

---

## Conclusion

**16.5.57 is COMPLETE as a boundary audit.** It has determined:

1. What AbletonMCP **can** do (parameter read/write after manual Configure)
2. What it **cannot** do (no processor-state import tool)
3. What remains **untested** (processor-state injection, audio automation, save/reopen)
4. What is **structurally possible** (processor state is readable, embeddable, machine-processable)

The evidence now supports **not a decision**, but a **structured decision agenda** for 16.5.58:

> "Given that processor state is readable but injection untested, and Configure Mode works for one parameter only, and render automation is unresolved — what is the minimal viable host architecture for 16.6?"

That is the right question to answer next, with full awareness of unknowns and constraints.

