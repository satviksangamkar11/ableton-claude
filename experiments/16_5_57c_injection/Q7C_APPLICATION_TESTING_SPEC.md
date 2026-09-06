# Q7c Application Testing Specification

**Status**: READY FOR EXECUTION  
**File to Open**: `experiments/16_5_57c_injection/SET_A_INJECTED_with_B_state.als`  
**MCP Constraint**: AbletonMCP has no `open_live_set()` tool; manual GUI action required  

---

## User Action Required

### Step 1: Open the Injected Set in Ableton Live

1. **Launch Ableton Live** (if not already running)
2. **File → Open Live Set**
3. **Navigate to**: `D:\ableton claude\experiments\16_5_57c_injection\SET_A_INJECTED_with_B_state.als`
4. **Click Open**
5. **Allow Ableton to load completely** (watch for load progress)

### Critical Points

- **Do NOT manually adjust any Serum parameters** after the set opens
- **Allow Ableton to apply the processor state** without intervention
- **Observe whether Serum loads without errors**
- **Note the Serum UI state** (what is OSC1.Volume showing?)

---

## Step 2: Verify Application (Automated via MCP)

After you've opened the set in Ableton, I will:

1. **Use MCP to query Serum's device parameters**:
   ```
   get_device_parameters(track=0, device=0)
   ```

2. **Read the OSC1.Volume parameter** and record its value

3. **Compare to baseline values**:
   - If value = 0.75 → Ableton **ignored** the injected state (loaded original SET_A)
   - If value = 0.50 → Ableton **applied** the injected state (loaded SET_B's state)

4. **Independent visual verification**: Check Serum's UI to confirm knob position matches readback

---

## Pass Condition for Q7c

**Q7c = PASS** only if ALL are true:

✓ SET_A_INJECTED_with_B_state.als opens successfully in Ableton  
✓ Serum loads without error  
✓ MCP `get_device_parameters()` returns OSC1.Volume = 0.50 (the injected value from SET_B)  
✓ Visual Serum UI confirms knob shows 0.50 (not 0.75)  
✓ No manual parameter adjustment occurred between opening and readback  

---

## Failure Conditions

**Q7c = FAIL** if any of these occur:

✗ SET_A_INJECTED_with_B_state.als cannot be opened (file corruption from injection)  
✗ Ableton opens but Serum fails to load (processor state is invalid for Ableton)  
✗ MCP readback shows 0.75 (Ableton ignored injection, loaded original state)  
✗ MCP readback shows an unexpected value (injection corrupted the state)  
✗ Serum UI shows 0.75 while MCP reports 0.50 (state mismatch)  

---

## Timeline

1. **You**: Open the injected .als in Ableton (manual, 30 seconds)
2. **You**: Tell me when it's open and what you observe in Serum UI
3. **I**: Use MCP to read the actual parameter values (automated)
4. **I**: Create Q7c application evidence artifact with results
5. **I**: Report Q7c PASS or FAIL with full evidence chain

---

## Expected Outcomes

### Scenario A: Ableton Applied the Injected State (PASS)

- File opens successfully ✓
- Serum shows OSC1.Volume knob at 0.50 (visibly different from 0.75)
- MCP readback: parameter value = 0.50
- **Q7c = PASS** → Processor-state transport is viable
- **Hybrid architecture can proceed** to Q8/Q9 testing

### Scenario B: Ableton Ignored the Injection (FAIL)

- File opens successfully ✓
- Serum shows OSC1.Volume knob at 0.75 (original value from SET_A)
- MCP readback: parameter value = 0.75
- **Q7c = FAIL** → Processor-state transport does not work
- **Hybrid architecture must revert** to Configure-only (constrained scope)

### Scenario C: File Corruption (FAIL)

- File cannot open, or
- Ableton opens but Serum fails to load
- **Q7c = FAIL** → Injection method is unsafe for Ableton
- **Hybrid architecture blocked** — alternative method required

---

## Ready to Proceed

The injected set is prepared and waiting to be opened.

**Next step**: Open `SET_A_INJECTED_with_B_state.als` in Ableton Live and report what you see in the Serum UI.

