# 16.5.58 — Host Architecture Decision

**Status**: PROVISIONAL  
**Date**: 2026-09-07  
**Decision Basis**: 16.5.57 host capability boundary audit  
**Scope**: Architecture selection for Ableton Live 12.3 + Serum 2.0.21 integration  

---

## Established Facts (16.5.57 Evidence)

1. **Configure/MCP is the host parameter plane.**
   - Ableton's Configure Mode exposes manually-selected VST3 parameters to Live's parameter list
   - Once exposed, AbletonMCP can read/write via `get_device_parameter()` / `set_device_parameter()`
   - Tested on one parameter: OSC1.Volume/"A Level" (VERIFIED)

2. **Serum mod-matrix source/destination topology is NOT exposed through the VST3 parameter plane.**
   - Per PROOF_PLAN.md: "Serum's mod matrix (source/destination assignment) is **not** host-exposed via VST3 — only `Mod N Amount`/`Mod N Out` are automatable."
   - Deep mod topology creation "genuinely requires the file/state plane"
   - This is a structural boundary, not a coverage gap

3. **Therefore Configure/MCP cannot construct arbitrary Serum mod topology.**
   - Logical consequence of facts 1 and 2
   - No amount of additional parameter exposure will change this

4. **Q7a: MCP processor-state import = NO**
   - Exhaustive search of AbletonMCP surface
   - No `set_device_processor_state()` or equivalent exists
   - No tool to import processor state programmatically

5. **Q7b: processor-state extraction from .als = READ-ONLY PASS**
   - Serum processor state deterministically located in `.als` XML
   - Path: `/root/LiveSet/Tracks/MidiTrack/DeviceChain/DeviceChain/Devices/PluginDevice/PluginDesc/Vst3PluginInfo/Preset/Vst3Preset/ProcessorState`
   - Extraction: 3,280 bytes hex-encoded XferJson format
   - Deterministic: Same input always produces same output (gzip decompress → XML parse → traverse → hash)

6. **Q7c: offline processor-state injection + Ableton application = UNTESTED**
   - Can a modified `<ProcessorState>` be written back to `.als`? UNTESTED
   - Can Ableton apply that injected state when opening the `.als`? UNTESTED
   - This is the critical unknown

7. **Q5e: save/reopen persistence = UNVERIFIED**
   - Reported as surviving save/reopen, but save and reopen were manual GUI operations
   - No direct observation that these operations occurred
   - Marked as UNVERIFIED per CLAUDE.md § Rule 5

8. **`render_to_file()` is NOT an available MCP operation.**
   - Previously claimed in test plan; does not exist in AbletonMCP
   - Only available mechanism: `record_section()` (real-time resampling, max ~5 min)
   - Not equivalent to File→Export Audio (batch export)

9. **`record_section()` is real-time capture, NOT equivalent to File→Export.**
   - Routes Main output to a resampling track
   - Records in real time while transport runs
   - Fundamentally different from batch export of mixed audio
   - Suitability for "render automatically" requirement TBD

---

## Architecture Options

### Option A: Configure/MCP Only

**Definition**:
- Use Ableton's Configure Mode to expose selected Serum parameters
- Use AbletonMCP to read/write those parameters at runtime
- No processor-state transport

**Advantages**:
- Works for parameters Ableton publishes
- Simpler integration (no offline file manipulation)
- Tested mechanism (one parameter verified)

**Disadvantages**:
- **Cannot construct mod topology** (facts 1-3)
- Cannot construct any patch requiring deep topology or unmapped parameters
- Persistence across save/reopen unverified
- Coverage limited to what VST3 exposes + what Ableton publishes

**Verdict**: INSUFFICIENT for 16.6 requirement of "three Serum roles" (bass, pad, lead). Professional Serum patches require custom mod topology, which this architecture cannot provide.

**Status**: **REJECTED_AS_SUFFICIENT**

---

### Option B: Processor-State Transport Only

**Definition**:
- Use processor-state/file plane as the sole initialization mechanism
- Compiler generates state → inject into `.als` → Ableton opens and applies
- No runtime parameter control via Configure/MCP

**Advantages**:
- Can theoretically construct arbitrary Serum state including mod topology
- Q7b proves state is present and readable
- Deterministic extraction path established

**Disadvantages**:
- **Q7c (offline injection + Ableton application) is UNTESTED**
- No MCP tool for state import; requires custom script/offline manipulation
- Runtime parameter control not available (all control is pre-initialization)
- Requires Ableton to apply injected state on open (unproven)
- Failure of any step collapses the entire pipeline

**Verdict**: REQUIRED if deep Serum state construction is necessary, BUT NOT YET PROVEN VIABLE. Q7c is the critical validation gate.

**Status**: **REQUIRED_CANDIDATE** (conditional on Q7c success)

---

### Option C: Hybrid (Processor-State Initialization + Configure/MCP Runtime Control)

**Definition**:
- Processor-state/file plane for deep Serum initialization (full topology, mod matrix, etc.)
- Configure/MCP parameter plane for runtime host-visible tweaking
- Compiler generates state → inject into `.als` → Ableton opens → MCP controls parameters

**Advantages**:
- Separates concerns: deep state construction (file plane) from runtime control (parameter plane)
- Allows runtime parameter automation via MCP (if persistence is verified)
- Configure Mode persistence is irrelevant if initialization handles all state
- Fallback to Configure-only if processor-state fails

**Disadvantages**:
- Requires BOTH processor-state injection (Q7c) AND Configure Mode setup (manual or automated)
- More complex integration (file manipulation + parameter configuration)
- Requires custom automation layer to coordinate both planes
- Depends on Q7c success

**Verdict**: PROVISIONALLY SELECTED. Represents the most complete architecture if Q7c succeeds. If Q7c fails, reverts to Option A (Configure-only) with constrained scope.

**Status**: **PROVISIONAL**

---

## Architecture Decision

### Rejected

**Option A (Configure/MCP Only)**: REJECTED_AS_SUFFICIENT

**Reason**: The demonstrated plane boundary (fact 2-3) means Configure/MCP cannot construct Serum mod topology. Any 16.6 arrangement requiring deep Serum patches will fail. This is architecturally insufficient.

### Required Candidate

**Option B (Processor-State Only)**: REQUIRED_CANDIDATE

**Reason**: Only pathway for deep Serum state construction. However, NOT YET PROVEN VIABLE because Q7c (offline injection + Ableton application) is UNTESTED. B is not selected as the final architecture; it is the required validation path.

### Provisional

**Option C (Hybrid: State + Configure/MCP)**: **PROVISIONAL**

**Definition**: 
- Processor-state/file plane is the **intended mechanism** for deep Serum initialization and topology construction
- Configure/MCP is the **intended mechanism** for runtime host-visible parameter control
- Both planes are used together; neither alone is sufficient

**Status**: PROVISIONAL, not ACTIVE

**Transition Condition**: C becomes ACTIVE only if:
1. Q7c succeeds (offline injection works + Ableton applies on open)
2. Q8 or equivalent establishes automated audio capture/export path
3. Q9 or equivalent establishes automated save/reopen with state fidelity

**Conditional Fallback**: If Q7c fails:
- Revert to Option A (Configure-only)
- Document which 16.6 requirements become impossible (deep topology, arbitrary patches)
- Scope 16.6 to simple parameter-only patches with no custom mod routing

---

## Unresolved Assumptions

The provisional architecture depends on unknowns:

| Unknown | Impact | Status |
|---|---|---|
| **Q7c outcome**: Can offline injection work? Does Ableton apply it? | Critical | UNTESTED |
| **Q5e correction**: Do Configure parameters persist across save/reopen? | Important if B used alone | UNVERIFIED |
| **Q8 equivalent**: What automates audio capture/export? (render_to_file doesn't exist) | Critical for "render automatically" | UNKNOWN |
| **Q9**: Does entire pipeline survive save/close/reopen cycle? | Critical for production | UNKNOWN |
| **Configure coverage**: Do all needed Serum parameters publish to VST3? | Important for Configure plane | UNKNOWN (one param tested) |

---

## Fallback Architecture

If Q7c fails (offline injection does not work or Ableton does not apply it):

1. **Processor-state transport is not viable for automated production**
2. **Revert to Option A (Configure/MCP Only)**
3. **Constrain 16.6 scope** to patches that can be constructed entirely via Configure Mode parameters
4. **Document impossibilities**:
   - Custom mod topology: IMPOSSIBLE (not exposed via VST3)
   - Deep synthesis control: IMPOSSIBLE (limited to exposed parameters)
   - Arbitrary Serum patches: IMPOSSIBLE (coverage depends on VST3 exposure)
5. **Alternative for deep state**: Manual Serum preset loading (GUI, not automated)

---

## Q7c Specification — Critical Validation Gate

### Objective

Determine whether offline processor-state injection into `.als` files is viable as an automation mechanism. Specifically:
- Can we write a modified `<ProcessorState>` back into a `.als` file?
- Does Ableton apply that injected state when opening the file?
- Does Serum's actual state reflect the injection (not defaults)?

### Procedure

1. **Source**: Use the exact `.als` from Q7b (already verified to contain extractable processor state)
2. **Copy**: Make a scratch COPY; leave the original untouched
3. **Extract**: Decompress and parse the copy's XML; locate the Serum `<ProcessorState>` element
4. **Modify**: Edit exactly one known Serum field in the extracted hex payload
   - Example: Change `OSC1.Volume` from 0x... to a different value
   - Verify the modified hex differs from the original (hash check)
5. **Inject**: Write the modified processor-state hex back into the ProcessorState element in the copied `.als`
6. **Verify File**: Hash the modified `.als` to confirm injection succeeded
7. **Open in Ableton**: Open the modified `.als` copy in Ableton Live
   - **Critical**: This is the first time Ableton sees the injected state
8. **Read State**: Query Serum's state via AbletonMCP or examine Configure panel
9. **Verify Ableton Applied It**: 
   - Serum's actual parameter value must reflect the injected state (not the original)
   - Use both MCP parameter readback AND visual inspection of Serum UI
10. **Test Audio**: Play a MIDI note; verify Serum produces sound consistent with injected state
    - Example: If OSC1 volume was zeroed, should be silent
11. **Pass Condition**: Serum's actual state matches injected values, not defaults from original

### Failure Modes

**File modification fails**: Modified `.als` is corrupt or injection wasn't written correctly. Verdict: Procedural issue, not architectural.

**Ableton opens but ignores injection**: File modification succeeded, but Ableton resets state to default or original. Verdict: Q7c FAILS architecturally.

**Ableton crashes**: File modification corrupted the state structure. Verdict: Q7c FAILS; offline manipulation is not safe.

**Serum loads but shows wrong state**: Ableton applied *something*, but it's not what we injected. Verdict: Q7c FAILS; injection path is broken.

**Serum loads correctly**: Actual Serum state (confirmed via readback + audio) matches injected values. Verdict: Q7c PASSES.

### Success Criteria

- Modified `.als` is well-formed (Ableton can open it)
- Serum loads into the track without error
- Serum's actual state (as read via MCP and verified visually) reflects the injected processor-state values
- Audio output is consistent with the injected state
- **Critical**: Success requires independent verification (readback + visual + audio), not just file modification

### Artifacts to Preserve

- Original `.als` from Q7b (untouched)
- Copy of `.als` before injection (for comparison)
- Modified `.als` with injected processor-state (test artifact)
- SHA256 hashes of ProcessorState payload before/after injection
- MCP parameter readback before/after opening modified `.als`
- Audio recording if OSC1 state change is audible

---

## Dependency Separation

The following gates are **independent** — do NOT infer one's outcome from another:

| Gate | Scope | Depends On |
|---|---|---|
| **Q7c** | Processor-state injection viability | NOTHING (critical path) |
| **Q8** | Automated audio capture/export mechanism | NOT Q7c (orthogonal) |
| **Q9** | Save/close/reopen + state fidelity | NOT Q7c (orthogonal) |

**Why independent?**
- Q7c proves state can get *into* Serum; Q8 proves audio can get *out* of Ableton; Q9 proves everything survives cycles
- Failure of Q7c does not doom Q8 or Q9; they must be tested on the fallback architecture
- Success of Q7c does not guarantee Q8 or Q9 success; each has its own blockers

---

## Roadmap Update (16.5.58 Entry)

```
16.5.58 | Host Architecture Decision | PROVISIONAL | 16.5.57
├─ Decision: Hybrid (Processor-State + Configure/MCP) selected as provisional
├─ A rejected as sufficient (mod topology blocker)
├─ B required candidate (only state-plane path)
├─ C provisional (state + parameter planes together)
├─ Fallback: If Q7c fails, revert to Configure-only with constrained scope
├─ Q7c critical gate: offline injection viability
├─ Q8, Q9 independent gates (audio export, save/reopen)
└─ Transition: PROVISIONAL → ACTIVE only if Q7c + Q8 + Q9 succeed
```

---

## Transition: PROVISIONAL → ACTIVE

The provisional architecture becomes ACTIVE only when:

1. ✓ Q7c PASSES: Offline injection works; Ableton applies injected state
2. ✓ Q8 PASSES: Automated audio capture/export path established
3. ✓ Q9 PASSES: Save/close/reopen cycle preserves all state

Until all three pass, the architecture remains PROVISIONAL and could revert to the fallback (Configure-only) at any gate failure.

---

## Frontier Integrity

- **Contract count**: 37 (unchanged)
- **Composition**: 26 CAUSAL_VERIFIED, 8 STRUCTURAL_ONLY, 3 NEGATIVE_EVIDENCE (unchanged)
- **Provenance**: No capabilities promoted; decision only
- **No capability escalation** — this is an architecture choice, not evidence promotion

---

## Next Step: Q7c Processor-State Injection Experiment

After 16.5.58 commits, the immediate next work is:

**16.5.57-Q7c**: Execute the Q7c specification defined in this document.

Experiment goal: Determine whether offline processor-state injection is viable.

Success condition: Serum's actual state (verified via readback + audio) reflects injected values, not defaults.

Failure condition: Ableton ignores injection, applies wrong state, or crashes.

Result gates the viability of the entire processor-state-plane pathway and determines whether the Hybrid architecture can proceed.

