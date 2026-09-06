# Q7c Processor-State Offline Injection — Findings and Specification

**Status**: FINDINGS DOCUMENTED; EXPERIMENT SPECIFICATION READY; NOT YET EXECUTED  
**Date**: 2026-09-07  
**Experiment ID**: 16.5.57-Q7c  

---

## Current Status: Q7b and Q7c

### Q7b Read-Only Extraction: **PASS** ✓

Evidence from `experiments/16_5_57_probe/Q7b_PROCESSOR_STATE_READPROBE.md`:

- Serum processor state IS present in Ableton `.als` files
- Located at deterministic XML path: `/root/LiveSet/Tracks/MidiTrack/DeviceChain/DeviceChain/Devices/PluginDevice/PluginDesc/Vst3PluginInfo/Preset/Vst3Preset/ProcessorState`
- Extraction is fully deterministic (gzip decompress → XML parse → traverse → hash)
- Payload: 3,280 bytes hex-encoded XferJson format
- SHA256: `c18f5065547f5bfdc3b1f7d7ec4d23b6c7062bc0511073eaabb0aa59812e52b4`

**What Q7b proved**: Processor state is structurally present and readable.

**What Q7b did NOT prove**: That offline injection works or that Ableton applies an injected state.

### Q7c Offline Injection: **UNTESTED**

**Critical Finding**: Attempted field-level mutation (modifying OSC1.Volume within the XferJson payload) was deferred because:

1. **Payload structure is not purely JSON**
   - Top-level metadata is JSON: `{component, hash, product, productVersion, url, vendor, version}`
   - The actual synthesizer patch data (oscillators, filters, mod matrix, envelopes) is **binary-encoded within or after the JSON**
   - Mutation of individual fields requires understanding this binary encoding

2. **Safe field-level injection requires unknown information**
   - Xfer's XferJson binary format is not publicly documented
   - Naively modifying the JSON section breaks the payload's internal structure
   - Ableton requires **exact binary fidelity** to apply the state
   - Without format documentation, field-level mutation risks corrupting the state

3. **Therefore, field-level reconstruction was abandoned** in favor of a whole-state swap approach

**What remains untested**: Whether Ableton applies an injected processor state when opening a `.als` file.

---

## Why Whole-Processor-State Swap Is Valid

### Rationale

Instead of attempting to reverse-engineer Xfer's binary encoding, use two **independently saved, known-good** Ableton `.als` files that differ by exactly one parameter:

- **SET_A.als**: Serum instance with OSC1.Volume = 0.75 (known good)
- **SET_B.als**: Same instance, same configuration, OSC1.Volume = 0.50 (known good)
- **SET_A_INJECTED.als**: Copy of SET_A, with SET_A's ProcessorState payload replaced by SET_B's known-good ProcessorState

By swapping **entire valid processor states** (not surgically modifying fields), we:
- Avoid reverse-engineering Xfer's binary format
- Use only known-good payloads extracted directly from Ableton
- Keep the experiment mechanically simple (payload swap)
- Preserve the test's focus: **Does Ableton apply the injected state?**

### What This Tests

1. **File-level mutation**: Can we safely replace the ProcessorState XML element without corrupting the `.als` file structure?
2. **Payload validity**: Does Ableton accept the swapped known-good payload?
3. **State application**: Does Serum's actual state reflect the injected value?
4. **Independent verification**: Can readback (MCP + visual) confirm the injection was applied?

### What This Does NOT Test (Yet)

- Arbitrary processor-state construction from scratch
- Field-level mutation of the binary-encoded state
- Compiler-generated states (future work)

But it DOES answer the critical question: **Is processor-state transport viable as a delivery mechanism?**

---

## Experiment Specification: Whole-Processor-State Swap

### Preparation Phase (Ableton GUI)

**Step 1**: Create SET_A.als
- Open Ableton Live
- Create a new set with one MIDI track
- Load Serum 2.0.21 onto the track
- Configure Serum: OSC1.Volume = 0.75 (visually confirm in Serum UI)
- Save set as: `experiments/16_5_57c_injection/SET_A_osc1vol_075.als`
- **Do NOT close Ableton yet; proceed to Step 2 without clearing state**

**Step 2**: Create SET_B.als
- **In the same Serum instance**: Change OSC1.Volume to 0.50 (visually confirm change)
- Do NOT touch any other Serum controls
- Save set as: `experiments/16_5_57c_injection/SET_B_osc1vol_050.als`
- Close Ableton

### Extraction and Injection Phase (Automated)

**Step 3**: Hash source files
```bash
sha256sum SET_A_osc1vol_075.als
sha256sum SET_B_osc1vol_050.als
```

**Step 4**: Extract ProcessorState from SET_A.als
- Decompress gzip
- Parse XML
- Locate `<ProcessorState>` element
- Extract hex payload
- Hash it
- Store as baseline_A_payload.hex

**Step 5**: Extract ProcessorState from SET_B.als
- Decompress gzip
- Parse XML
- Locate `<ProcessorState>` element
- Extract hex payload
- Hash it
- Store as baseline_B_payload.hex

**Step 6**: Verify both payloads
- Both payloads must be valid (decode to UTF-8 without errors)
- Both must contain the XferJson magic header
- Both must be parseable as valid processor-state structures

**Step 7**: Confirm payloads differ
- Payload hashes must NOT match
- `baseline_B_payload.hex != baseline_A_payload.hex`

**Step 8**: Create SET_A_INJECTED.als
- Copy SET_A_osc1vol_075.als to SET_A_INJECTED_with_B_state.als
- **Do NOT modify the original SET_A.als**

**Step 9**: Inject SET_B's ProcessorState into SET_A_INJECTED.als
- Decompress the copy
- Parse XML
- Locate `<ProcessorState>` element
- Replace its text content with `baseline_B_payload.hex`
- **Replace only the hex string; do NOT touch any other XML elements**
- Recompress as gzip

**Step 10**: Verify injection result
- Hash the modified .als: `injected_als_hash`
- Hash the injected payload: `injected_payload_hash`
- Confirm `injected_payload_hash == baseline_B_payload.hex` (hash match proves injection succeeded)
- Confirm `injected_als_hash != source_hash` (file changed due to payload replacement)

### Testing Phase (Future Work — Do NOT Execute Yet)

**Step 11**: Open SET_A_INJECTED.als in Ableton
- Open the injected .als in Ableton Live
- **Do NOT manually adjust any Serum parameters after opening**
- Allow Ableton to load the file and apply the processor state

**Step 12**: Verify Ableton Applied the Injected State
- Use MCP `get_device_parameters()` to read Serum's OSC1.Volume parameter
- MCP must return: `0.50` (the injected value from SET_B)
- Independently verify visually in Serum UI: knob should show 0.50
- If both readback and visual confirm 0.50 (not 0.75), **Q7c PASSES**

---

## Pass Criteria for Q7c

**Q7c = PASS** only if ALL are true:

1. ✓ SET_A.als and SET_B.als are created with Serum in known-good states
2. ✓ Both ProcessorState payloads are extracted and valid
3. ✓ Payloads differ (hashes do not match)
4. ✓ SET_A_INJECTED.als is created with payload from SET_B injected
5. ✓ SET_A_INJECTED.als opens successfully in Ableton
6. ✓ Serum instance is loaded without error
7. ✓ **MCP readback reports OSC1.Volume = 0.50** (the injected value)
8. ✓ **Visual Serum UI confirms 0.50** (independent verification)
9. ✓ No manual parameter adjustment after opening was used to create the observed value

### Fail Criteria

**Q7c = FAIL** if:
- SET_A_INJECTED.als cannot be opened (injection corrupted the file)
- Ableton opens the file but Serum shows 0.75 (injection ignored, original state loaded)
- Ableton opens but Serum state is corrupted/invalid
- MCP readback reports 0.75 or an unexpected value
- Visual UI shows 0.75

### Inconclusive

**Q7c = INCONCLUSIVE** if:
- File opens, Serum loads, but state is ambiguous (e.g., parameter appears changed but cause is unclear)
- Readback conflicts with visual inspection

---

## Frontier Integrity

- **Contract count**: 37 (unchanged)
- **Composition**: 26 CAUSAL_VERIFIED, 8 STRUCTURAL_ONLY, 3 NEGATIVE_EVIDENCE (unchanged)
- **No capabilities promoted** — Q7c is an infrastructure test, not a capability claim
- **Hybrid architecture remains PROVISIONAL** pending Q7c outcome

---

## Explicit Status

**Q7C IS UNTESTED.**

- Q7b proved processor state is present and extractable ✓
- Q7c specification is designed and ready
- Q7c has NOT been executed
- No Ableton application of an injected processor state has yet been demonstrated
- The Hybrid architecture's viability depends on Q7c outcome

---

## Artifacts and Paths

| Artifact | Path | Status |
|---|---|---|
| Q7b Read-Only Probe | `experiments/16_5_57_probe/Q7b_PROCESSOR_STATE_READPROBE.md` | COMPLETE |
| Q7c Findings & Spec | `experiments/16_5_57c_injection/Q7C_FINDINGS_AND_SPECIFICATION.md` | THIS DOCUMENT |
| SET_A.als (to be created) | `experiments/16_5_57c_injection/SET_A_osc1vol_075.als` | PENDING USER CREATION |
| SET_B.als (to be created) | `experiments/16_5_57c_injection/SET_B_osc1vol_050.als` | PENDING USER CREATION |
| SET_A_INJECTED.als (automated) | `experiments/16_5_57c_injection/SET_A_INJECTED_with_B_state.als` | PENDING STEPS 3-10 |
| Extraction metadata | `experiments/16_5_57c_injection/Q7C_extraction_metadata.json` | PENDING STEPS 3-10 |

---

## Next Action

**Immediate**: User creates SET_A.als and SET_B.als in Ableton as per Preparation Phase steps 1-2.

**After user provides files**: Execute Extraction and Injection Phase (steps 3-10 automated).

**Testing Phase**: Open SET_A_INJECTED.als in Ableton and perform verification per step 12.

**Result**: Q7c PASS, FAIL, or INCONCLUSIVE → Gates Hybrid architecture viability.

