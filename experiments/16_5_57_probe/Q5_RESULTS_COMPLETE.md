# Q5: Host Parameter Exposure Ladder — COMPLETE RESULTS

**Status**: ✓ ALL TESTS PASSED  
**Date**: 2026-09-07  
**Runtime**: Ableton Live 12.3 Suite | AbletonMCP | Serum 2.0.21 VST3  

---

## Executive Summary

**Host parameter control via Ableton Configure Mode is VIABLE and PROVEN — for the tested parameter.**

Configure Mode can expose Serum parameters to Ableton Live, where they become controllable via AbletonMCP's `get_device_parameter()` and `set_device_parameter()` functions. Configuration persists across save/reopen cycles.

**Important scoping note**: This investigation tested ONE parameter (OSC1.Volume / "A Level"). Full coverage of Serum's 100+ parameters requires additional verification.

This architecture opens a simpler path than processor-state transport for parameters that Live exposes.

---

## Q5a: Baseline Exposure ✓

**Observation**: Only "Device On" initially exposed by Ableton.

```json
{
  "parameter_count": 1,
  "parameters": [
    {
      "name": "Device On",
      "value": 1.0,
      "type": "boolean"
    }
  ]
}
```

**Interpretation**: Serum 2 has 100+ parameters. Ableton Live only exposes device bypass by default for >64-parameter plugins per Live documentation.

---

## Q5b: Configure Mode Availability ✓

**Finding**: Configure Mode EXISTS and is ACCESSIBLE.

- Located: Bottom-left device panel in Ableton
- Status: Green "Configure" button, clearly marked
- Instruction: "To add parameters to this panel, click on them in the plugin's window."

**Mechanism**: Manual—requires clicking desired Serum parameters while Configure is active.

---

## Q5c: OSC1.Volume Registration ✓

**Procedure**:
1. Opened Ableton's Configure Mode (green "Configure" button)
2. Clicked the LEVEL knob in Serum 2 (under OSC A section, bottom left)
3. Observed: Parameter appeared in Configure panel

**Result**:
```
Live Configure Panel showed:
  "A Level"  75% [-5.0 dB]
```

**Conclusion**: Serum 2 successfully published OSC1.Volume to Ableton's Configure system when explicitly selected.

---

## Q5d: MCP Read/Write ✓

**Test**: Write via MCP, readback via MCP, independent visual verification.

### Write Test
```
MCP Call: set_device_parameter(track=0, device=0, parameter=1, value=0.5)
Result:   "Serum 2: A Level = 50% [-12.0 dB]"
```

### Readback Test
```json
{
  "name": "A Level",
  "value": 0.5,
  "display": " 50% [-12.0 dB]"
}
```

### Independent Verification
User confirmed: Serum 2's LEVEL knob (OSC A) visually shows **50%** (changed from 75%).

**Conclusion**: 
- MCP write succeeded
- Value persisted in Live and Serum
- Independent verification confirms actual Serum state changed

---

## Q5e: Persistence ✓

**Procedure**:
1. Saved Ableton set (File → Save)
2. Closed and reopened the set
3. Queried MCP for "A Level" parameter

**Result**:
```json
{
  "parameter_count": 2,
  "parameters": [
    {"name": "Device On", "value": 1.0},
    {"name": "A Level", "value": 0.5, "display": " 50% [-12.0 dB]"}
  ]
}
```

**Conclusion**: 
- Configure configuration persisted
- "A Level" still accessible post-reopen
- Parameter value (0.5) retained

---

## Architecture Decision: HOST PARAMETER CONTROL IS VIABLE

```
Serum 2.0.21
  ├─ 100+ synthesis parameters
  │
  ├─ Ableton Live 12.3
  │  ├─ Configure Mode (manual parameter exposure)
  │  └─ Device parameters (exposed set)
  │     └─ Live LOM (Live Object Model)
  │
  ├─ AbletonMCP
  │  ├─ get_device_parameters()  [read configured params]
  │  └─ set_device_parameter()   [write configured params]
  │
  └─ Serum Producer
     ├─ Read synthesis state
     ├─ Write control parameters
     └─ NO processor-state transport for every operation
```

---

## Key Advantages of This Architecture

| Aspect | Benefit |
|---|---|
| **Scope** | Only expose needed parameters (OSC1.Volume, Filter.Resonance, Env1.Attack, etc.) |
| **Simplicity** | No parallel parameter-discovery system; uses Live's native Configure |
| **Persistence** | Configured parameter list saved with .als file |
| **Repeatability** | Same parameter set available across sessions |
| **Compatibility** | Uses standard AbletonMCP interface (get/set_device_parameter) |
| **Fallback** | Processor-state transport still available for complex initialization |

---

## Limitations and Caveats

1. **Manual Configuration Required**: Each Serum parameter must be manually clicked in Configure Mode once per set. Not automatable via current AbletonMCP.

2. **Parameter Naming**: Serum exposes parameters as "A Level", "A Octave", "B Level", etc. (section prefix + name). Producer must map semantic targets to these Live names.

3. **Not All Parameters May Be Published**: Per Ableton documentation, some VST3 plugins may not publish every parameter. Full coverage requires verification.

4. **Numeric Normalization**: Ableton normalizes parameter ranges to 0.0–1.0. Serum's native ranges (e.g., -96 to 0 dB for volume) are mapped and displayed with units (e.g., " 50% [-12.0 dB]").

---

## Recommended Producer Integration Path

1. **Semantic Target Mapping** (in `targets.py`)
   ```python
   SEMANTIC_TARGETS = {
       "OSC1.Volume": "A Level",  # Map to Live Configure name
       "OSC1.Octave": "A Octave",
       "Filter.Resonance": "RS",
       "Env1.Attack": "Attack",  # ENV 1 section
       ...
   }
   ```

2. **Prerequisite Verification** (in `admission.py`)
   - Check that required parameters exist in Live's device.parameters list
   - Verify ranges and normalization

3. **Control via MCP** (in `producer.py`)
   - Use `set_device_parameter(target_name, value)` to control Serum
   - No processor-state transport required for synthesis control

4. **One-Time Setup**
   - User opens Ableton
   - Enters Configure Mode on Serum device
   - Clicks desired parameters in Serum UI
   - Configuration saved with project

---

## Evidence Artifacts

- **Q5a_baseline**: 1 parameter (Device On only)
- **Q5c_configure_registration**: "A Level" appears in Live Configure panel
- **Q5d_write**: MCP writes 0.5, readback confirms, Serum UI shows 50%
- **Q5e_persistence**: After save/reopen, "A Level" still present and readable

---

## Important Limitation: Single-Parameter Evidence

**Scope of Testing**: This investigation tested ONE Serum parameter (OSC1.Volume / "A Level").

**What the evidence proves**:
- This specific parameter is accessible via Configure Mode
- It can be read/written via AbletonMCP
- It persists across save/reopen cycles

**What the evidence does NOT prove**:
- All 100+ Serum parameters follow the same path
- All Serum parameters are published to Live's Configure system
- Parameter exposure is uniform across different Serum control types

**Ableton documentation caveat** (per Live help):
> "Some plug-ins may not publish every parameter to the Configure system"

**Implication for producer integration**:
Each Serum parameter must be verified individually:
1. Check if it appears in Configure Mode (manual click in Serum UI)
2. Verify it becomes readable via MCP
3. Confirm MCP can write to it
4. Test persistence across save/reopen

The OSC1.Volume/"A Level" parameter serves as proof-of-concept, not proof of full coverage.

---

## Conclusion

**Host parameter control via Ableton's Configure Mode + AbletonMCP is a proven, working architecture for Serum 2 synthesis parameters — at least for the tested parameter.**

For parameters verified to be accessible via Configure Mode, no architectural redesign is needed. The path is:
1. Manual Configure Mode setup (one-time per project)
2. AbletonMCP read/write operations via semantic target mapping
3. Persistent across save/reopen

This simplifies the producer's operation flow for configured parameters compared to processor-state transport for every interaction.

**Caveat**: This path requires prior verification that each target parameter is:
- Published by Serum to Live's Configure system
- Accessible via MCP after configuration
- Persistent across save cycles

---

**Next Phase**: 
- Verify additional Serum parameters follow the same Configure → MCP → Persistent path
- Determine fallback strategy for parameters not published to Configure
- Finalize 16.5.57 closure

---

**Next Phase**: Proceed to 16.5.58 (host-path decision) or continue 16.5.57b with Q6–Q9.
