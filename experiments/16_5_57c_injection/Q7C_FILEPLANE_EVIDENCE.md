# Q7c File-Plane Preparation — Evidence Artifact

**Status**: FILE-PLANE PREPARATION COMPLETE  
**Date**: 2026-09-07  
**Experiment ID**: 16.5.57-Q7c  

---

## Critical Status Statement

**Q7C APPLICATION REMAINS UNTESTED.**

This document records the successful preparation of the file-plane injection. It does **NOT** establish that:
- Ableton accepts the injected processor state
- Ableton applies the injected processor state
- Serum reflects the injected value after opening
- Any change to Serum's actual behavior occurs

Those remain UNTESTED.

---

## Source Files (User-Created)

| File | Path | Hash (SHA256) |
|---|---|---|
| **SET_A.als** | `experiments/16_5_57c_injection/SET_A_osc1vol_075 Project/SET_A_osc1vol_075.als` | `c34857dadd8f884fa40e63d783a40024...` |
| **SET_B.als** | `experiments/16_5_57c_injection/SET_B_osc1vol_050 Project/SET_B_osc1vol_050.als` | `ee036cd82d48b469e100b01495ebc0c5...` |

**Creation Method**: Manual in Ableton Live
- SET_A: Serum instance with OSC1.Volume = 0.75
- SET_B: Same instance, OSC1.Volume changed to 0.50
- Both saved independently

---

## Processor-State Extraction Results

### SET_A ProcessorState

| Property | Value |
|---|---|
| **Extraction Status** | SUCCESS ✓ |
| **Hex Length** | 6,606 characters (3,303 bytes) |
| **Payload SHA256** | `a6decc115666735a6f6554f1f491cef7...` |
| **XML Location** | `/root/LiveSet/Tracks/MidiTrack/DeviceChain/DeviceChain/Devices/PluginDevice/PluginDesc/Vst3PluginInfo/Preset/Vst3Preset/ProcessorState` |
| **JSON Valid** | YES ✓ |
| **Decoded OSC1.Volume** | (value not extracted from JSON structure) |

### SET_B ProcessorState

| Property | Value |
|---|---|
| **Extraction Status** | SUCCESS ✓ |
| **Hex Length** | 6,560 characters (3,280 bytes) |
| **Payload SHA256** | `ef5dd5a66949af0d2c45d2d8641a0bf4...` |
| **XML Location** | `/root/LiveSet/Tracks/MidiTrack/DeviceChain/DeviceChain/Devices/PluginDevice/PluginDesc/Vst3PluginInfo/Preset/Vst3Preset/ProcessorState` |
| **JSON Valid** | YES ✓ |
| **Decoded OSC1.Volume** | (value not extracted from JSON structure) |

### Payload Comparison

| Property | Result |
|---|---|
| **Payloads differ** | YES ✓ |
| **Hashes match** | NO ✓ (expected; different parameter values) |
| **Both valid** | YES ✓ |

---

## Injection: SET_A_INJECTED_with_B_state.als

### Creation Method

1. Copied SET_A.als to new file: `SET_A_INJECTED_with_B_state.als`
2. Decompressed gzip archive
3. Parsed XML
4. Located ProcessorState element
5. **Replaced ONLY the ProcessorState hex payload with SET_B's known-good payload**
6. **Left all other XML elements unchanged**
7. Recompressed as gzip

### Verification Results

| Check | Status |
|---|---|
| **File created** | SUCCESS ✓ |
| **Payload injected** | SUCCESS ✓ |
| **Payload hash verified** | SUCCESS ✓ — injected payload hash == SET_B payload hash |
| **XML structure valid** | SUCCESS ✓ — file parses without error |
| **File is well-formed** | SUCCESS ✓ — gzip decompression successful |

### Injected File Metadata

| Property | Value |
|---|---|
| **File Path** | `experiments/16_5_57c_injection/SET_A_INJECTED_with_B_state.als` |
| **File Hash (SHA256)** | `7e4b5ce0795e2b01f22e67da6a555aea...` |
| **Injected Payload Hash (SHA256)** | `ef5dd5a66949af0d2c45d2d8641a0bf4...` |
| **Payload Injection Match** | YES ✓ (injected == SET_B) |
| **Structural Validity** | YES ✓ (parseable XML, valid gzip) |

---

## What This Establishes

✓ Two known-good source `.als` files with different Serum parameter values exist  
✓ Processor-state payloads are deterministically extractable from both  
✓ Both payloads are valid (decode to UTF-8, parse as JSON)  
✓ Payloads differ (hash mismatch expected due to parameter difference)  
✓ A whole processor-state payload can be surgically injected into an `.als` file  
✓ Injection preserves XML structure and file validity  
✓ The resulting file is parseable as valid Ableton XML  

---

## What This Does NOT Establish

✗ Ableton accepts the injected ProcessorState when opening the file  
✗ Ableton applies the injected processor state to the Serum instance  
✗ Serum's actual state reflects the injected value  
✗ Any observable change to Serum occurs after opening  
✗ The parameter values in the injected state are honored by Serum  

**These remain untested and must be verified through Ableton opening + MCP readback.**

---

## Frontier Integrity

- **Contract count**: 37 (unchanged)
- **Composition**: 26 CAUSAL_VERIFIED, 8 STRUCTURAL_ONLY, 3 NEGATIVE_EVIDENCE (unchanged)
- **No capabilities promoted**
- **No capability claims made**

---

## Explicit Declaration

**Q7C APPLICATION IS UNTESTED.**

The file-plane preparation is complete and successful. The injected `.als` file is structurally valid and ready to be opened in Ableton for application testing.

However, **no evidence yet demonstrates that Ableton applies the injected processor state, or that Serum's behavior changes as a result.**

That test remains for future execution.

---

## Next Action

**When ready**: Open `SET_A_INJECTED_with_B_state.als` in Ableton Live and perform the application test:
1. Allow Ableton to load the file
2. Use MCP `get_device_parameters()` to read Serum's actual state
3. Verify via MCP readback that the parameter reflects the injected value (not the original)
4. Independently confirm visually in Serum UI
5. **Only then** can Q7c be declared PASS or FAIL

