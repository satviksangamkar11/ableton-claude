# Producer World Model + Planner Architecture

**16.5.61a-b: Goal Model → World Model → Goal Grounding → Planner**

## Overview

The Producer layer adds strategic reasoning above the compiler/capability infrastructure.

```
User Intent (natural language)
       ↓ (Goal Parser)
GoalModel (structured: role, section, characteristics)
       ↓ (Planner consults)
WorldModel (current state: roles, sections, capabilities)
       ↓ (Gap Analysis)
GoalGroundingResult (satisfied/missing/contradictory/constrained/ungrounded)
       ↓ (Planner decides)
Plan (intentional actions: "increase brightness", not "set Filter1Freq to 0.5")
       ↓ (Executor)
Execution (MCP writes, rendering, measurement)
       ↓ (Feedback)
Updated WorldModel
```

## Module Contracts

### GoalModel (goal_model.py)

Represents **what the user wants**, not **how to achieve it**.

**Invariant: No Serum parameters in the goal.**

```python
GoalModel(
    user_phrasing="Make the bass darker and punchier for the drop",
    role="bass",
    section_name="peak",
    characteristics=MusicalCharacteristics(
        character=[Character.DARK, Character.PUNCHY],
        energy=Energy.HIGH,
        register=Register.LOW,
    )
)
```

Characteristics are constrained to a closed vocabulary:
- `character`: musical quality (dark, bright, warm, clean, punchy, smooth, harsh, soft, aggressive, mellow)
- `energy`: absolute level (low, medium, high)
- `register`: frequency range (sub, low, mid, high)
- `density`: texture thickness (sparse, medium, dense)
- `attack`: envelope shape (slow, medium, fast, punchy)
- `sustain_length`: sustain duration (short, medium, long)
- `spread`: spatial width (mono, medium, wide)

### WorldModel (world_model.py)

Snapshot of **current state**: arrangement, roles, Serum parameters, measured characteristics, verified capabilities.

**Invariant: Read-only from Planner's perspective.**

```python
WorldModel(
    arrangement=ArrangementState(
        key="A minor",
        tempo_bpm=124,
        sections=[
            SectionState("intro", 0, 16, ["pad"]),
            SectionState("peak", 16, 16, ["bass", "pad", "lead"]),
        ]
    ),
    roles={
        "bass": RoleState(
            role="bass",
            track_id=0,
            device_index=0,
            serum_state=SerumState(
                parameter_values={"OSC1.Volume": 0.75, "Filter.Cutoff": 0.3},
            ),
            measured_characteristics=MeasuredCharacteristics(
                brightness=0.2,       # low → "dark"
                attack_speed=0.8,     # high → "punchy"
                sustain_level=0.4,
                overall_loudness_db=-14.5,
            ),
            verified_capabilities=[
                VerifiedCapability(
                    capability_key="OSC1.Volume",
                    contract_hash="abc123def456...",
                    status="CAUSAL_VERIFIED",
                ),
            ],
        ),
    },
)
```

Measured characteristics come from **audio analysis**, not parameter inspection:
- `brightness`: spectral centroid or high-frequency RMS (0-1, 1 = bright)
- `attack_speed`: onset detection (0-1, 1 = fast/punchy)
- `sustain_level`: sustain window RMS relative to peak (0-1)
- `overall_loudness_db`: dB measured from rendered audio

### GoalGrounding (goal_grounding.py)

**Gap analysis**: compares goal to world state.

```python
result = ground_goal(goal, world)

# result.satisfied → [CharacteristicGap]
# result.missing → [CharacteristicGap]
# result.contradictory → [CharacteristicGap]
# result.constrained → [CharacteristicGap]
# result.ungrounded → [CharacteristicGap]
```

Gap types:

| Type | Meaning | Example |
|---|---|---|
| **SATISFIED** | Goal already met in world state | Goal: "punchy"; attack_speed = 0.8 ✓ |
| **MISSING** | Goal required but not measured | Goal: "dark"; brightness = None (not measured yet) |
| **CONTRADICTORY** | Goal conflicts with current state | Goal: "bright"; brightness = 0.2 (too dark) |
| **CONSTRAINED** | Evidence exists but prerequisites blocked | Goal: "longer sustain"; "no MCP mapping for Env1.Sustain" |
| **UNGROUNDED** | No known capability | Goal: "subtle warble"; no synthesis control maps to this |

### Planner (planner.py — to be written)

Will read:
1. GoalModel
2. GoalGroundingResult
3. Available capabilities from evidence system

Will decide:
1. Which satisfied gaps to leave alone (no change needed)
2. Which missing gaps to address (which capability to apply)
3. Whether contradictory gaps can be resolved or require refusal
4. Whether constrained gaps can be lifted or require discovery
5. Whether ungrounded gaps require a DiscoveryRequest

Will output:
```python
Plan(
    goal=goal,
    grounding=grounding_result,
    actions=[
        IntentAction(
            intent="increase bass brightness",
            semantic_target="Filter.Cutoff",
            capability_key="..."
        ),
    ],
    blocked=[...],
    confidence="evidence_bounded",
)
```

## Workflow Example

**User says:** "Make the bass darker and punchier for the peak"

### Step 1: Parse Intent → GoalModel

```python
goal = GoalModel(
    user_phrasing="Make the bass darker and punchier for the peak",
    role="bass",
    section_name="peak",
    characteristics=MusicalCharacteristics(
        character=[Character.DARK, Character.PUNCHY],
    ),
)
```

### Step 2: Ground Goal Against WorldModel

```python
grounding = ground_goal(goal, world)

# Assuming world has a bass role with:
# - measured_characteristics.brightness = 0.5 (medium)
# - measured_characteristics.attack_speed = 0.6 (medium-fast)

# Result:
# - Gap for "dark": CONTRADICTORY (brightness is 0.5, need < 0.4)
#   possible_capabilities: ["Filter.Cutoff"]
# - Gap for "punchy": MISSING (attack_speed is 0.6, need > 0.7)
#   possible_capabilities: ["Env1.Attack"]
```

### Step 3: Planner Decides

```python
plan = planner.make_plan(goal, grounding, world, evidence_system)

# Decision logic:
# 1. "dark" is contradictory → need to decrease brightness
#    → evidence system has CAUSAL_VERIFIED for Filter.Cutoff → decrease_cutoff
# 2. "punchy" is missing → need to increase attack speed
#    → evidence system has CAUSAL_VERIFIED for Env1.Attack → decrease_attack

# Output:
# Plan(
#     actions=[
#         IntentAction("decrease_bass_brightness", "Filter.Cutoff", ...),
#         IntentAction("increase_bass_punchiness", "Env1.Attack", ...),
#     ],
#     blocked=[],
# )
```

### Step 4: Executor Runs Plan

```python
for action in plan.actions:
    # Read current value from Ableton
    current = mcp.get_device_parameter(...)
    
    # Compiler converts action → control value
    new_value = compiler.resolve_to_value(action, current)
    
    # Execute via MCP
    mcp.set_device_parameter(new_value)
    readback = mcp.get_device_parameter(...)
    
    # Record audit
    audit_record.append({
        "intent": action.intent,
        "semantic_target": action.semantic_target,
        "written_value": new_value,
        "readback": readback,
    })
```

### Step 5: Render & Measure

```python
# Render audio
audio_stream = mcp.record_section(track_id=0, duration_beats=16)

# Measure
measured = {
    "brightness": measure_centroid(audio_stream),
    "attack_speed": measure_attack_onset(audio_stream),
    "overall_loudness_db": measure_loudness(audio_stream),
}

# Update WorldModel
world.roles["bass"].measured_characteristics = MeasuredCharacteristics(**measured)
```

### Step 6: Feedback

```python
# Did the plan succeed?
new_grounding = ground_goal(goal, world)

if not new_grounding.has_blocking_gap:
    return "Goal achieved"
elif new_grounding.requires_discovery:
    return "Goal requires discovery; DiscoveryRequest: " + ...
else:
    return "Goal partially achieved; replan with new measurements"
```

## Key Invariants

1. **No Serum parameters in user-facing contracts**
   - GoalModel: musical characteristics only
   - Plan: intentional actions only (e.g., "increase_brightness")
   - Parameter resolution happens in compiler/executor

2. **WorldModel is immutable from Planner's perspective**
   - Planner reads it; does not write
   - Updates via external systems (Ableton, rendering, evidence system)

3. **Gap types are exhaustive and mutually exclusive**
   - Every characteristic gets exactly one gap type
   - No ambiguous cases

4. **Evidence system is the authority**
   - Planner queries capabilities via evidence contracts
   - No guessing; refused capabilities return UNGROUNDED gaps
   - HYPOTHESIS → DiscoveryRequest, not execution

5. **Measurement is audio, not parameters**
   - Characteristics are measured from rendered audio
   - Parameter inspection is audit only
   - This ensures the producer reasons about music, not dials

## Planner Contract (16.5.61b)

### PlannerDecisionEngine

Converts GoalGroundingResult into executable Plan.

**Input:**
- GoalGroundingResult (gaps from goal vs. world state analysis)
- Evidence system (capabilities and their CapabilityContract.status)
- allowed_statuses (which contract statuses are acceptable; default: ["CAUSAL_VERIFIED"])

**Output:**
```python
Plan(
    goal=goal,
    grounding=grounding,
    confidence="grounded",  # or "bounded", "structural", "unknown"
    actions=[PlannedAction(...), ...],  # what to do (musical intent)
    blocked_gaps=[BlockedGap(...), ...],  # couldn't resolve
    discovery_requests=[DiscoveryRequest(...), ...],  # needs evidence
)
```

### Decision Rules Per Gap Type

| Gap Type | Planner Decision | Output |
|---|---|---|
| SATISFIED | No action | (skip) |
| MISSING | Find qualified capability | PlannedAction or DiscoveryRequest |
| CONTRADICTORY | Find corrective capability | PlannedAction or BlockedGap |
| CONSTRAINED | Prerequisites block | BlockedGap (explicit refusal) |
| UNGROUNDED | No known capability | DiscoveryRequest |

### PlannedAction Contract

```python
@dataclass(frozen=True)
class PlannedAction:
    intent: str  # e.g., "darken_bass" (musical intent, not parameter)
    target_dimension: str  # "brightness", "attack", etc.
    gap: CharacteristicGap  # the gap being addressed
    selected_capability: str  # semantic target: "Filter.Cutoff", "Env1.Attack"
    capability_key: str  # from evidence system
    capability_status: str  # "CAUSAL_VERIFIED", "STRUCTURAL_ONLY", etc.
    reasoning: str  # why this capability was chosen
```

### Critical Invariants

1. **Zero Silent Parameter Selection**
   - If no capability qualifies for a gap → refuse (BlockedGap or DiscoveryRequest)
   - Never guess or silently choose a fallback parameter
   - Example: unsupported intent "warmer" → DiscoveryRequest, NOT applied parameter

2. **Musical Intent, Not Tactical Parameters**
   - Planner outputs intent: "darken_bass", "increase_punchiness"
   - NOT parameter values: "set Filter.Cutoff to 0.5"
   - Parameter resolution is executor/compiler responsibility

3. **Evidence-Backed Decisions Only**
   - Only capabilities with status in allowed_statuses can be selected
   - Default (strict): ["CAUSAL_VERIFIED"] — only fully proven controls
   - Can loosen to ["CAUSAL_VERIFIED", "STRUCTURAL_ONLY"] for bounded execution
   - HYPOTHESIS → DiscoveryRequest, never silent execution

4. **Fully Auditable**
   - Every PlannedAction names:
     - The gap it addresses
     - The capability selected
     - Why that capability was chosen
   - Plan.to_dict() produces machine-readable decision record

5. **No Invention**
   - Planner refuses unknown targets gracefully
   - Unknown gap → DiscoveryRequest (not a guess)
   - Unknown capability → BlockedGap (not a fallback)

### Confidence Tracking

Planner computes confidence based on capability statuses used in actions:

- **"grounded"**: all actions CAUSAL_VERIFIED
- **"bounded"**: mix of CAUSAL_VERIFIED and STRUCTURAL_ONLY
- **"structural"**: all STRUCTURAL_ONLY
- **"low"**: any HYPOTHESIS (executor will refuse these anyway)
- **"unknown"**: no actions or unknown statuses

### Example: "Make the bass darker and punchier for the peak"

1. **Parse intent → GoalModel**
   ```python
   goal = GoalModel(
       user_phrasing="Make the bass darker and punchier for the peak",
       role="bass",
       section_name="peak",
       characteristics=MusicalCharacteristics(
           character=[Character.DARK, Character.PUNCHY],
       ),
   )
   ```

2. **Ground goal against world state**
   ```python
   grounding = ground_goal(goal, world)
   # Assuming world.roles["bass"].measured_characteristics:
   #   brightness=0.5 (too high; contradicts "dark" goal)
   #   attack_speed=0.5 (too slow; contradicts "punchy" goal)
   # Result: 2 CONTRADICTORY gaps
   ```

3. **Planner decides**
   ```python
   planner = PlannerDecisionEngine(evidence_system)
   plan = planner.plan(grounding)
   
   # Grounding:
   #   - Gap 1 (dark): CONTRADICTORY, possible_capabilities=["Filter.Cutoff"]
   #   - Gap 2 (punchy): CONTRADICTORY, possible_capabilities=["Env1.Attack"]
   
   # Planner finds capabilities:
   #   - Filter.Cutoff: CAUSAL_VERIFIED ✓
   #   - Env1.Attack: CAUSAL_VERIFIED ✓
   
   # Plan output:
   #   - 2 PlannedActions
   #   - no blocked gaps
   #   - no discovery requests
   #   - confidence="grounded"
   ```

4. **Executor runs actions**
   - Read current Filter.Cutoff, Env1.Attack from Ableton
   - Decide new values (compiler responsibility)
   - Write via MCP
   - Record audit trail

5. **Measure and feedback**
   - Render audio for role
   - Measure brightness, attack_speed
   - Update WorldModel
   - Reground goal with new measurements
   - Check if satisfied

### Failure Case: "Give the bass a longer sustain"

1. **Grounding** finds:
   - Gap: sustain_length=LONG is MISSING (not measured)
   - Or: sustain_length=LONG is CONSTRAINED ("no MCP mapping for Env1.Release")

2. **Planner:**
   - If MISSING: looks for capability, possibly finds Env1.Sustain in evidence
   - If CONSTRAINED: adds BlockedGap (doesn't proceed)
   - If no capability found: DiscoveryRequest

3. **Key: NO silent parameter selection**
   - Even if "sustain" maps to some parameter in the evidence system,
   - If prerequisites are blocked, Planner refuses explicitly.
   - If evidence is missing, Planner returns DiscoveryRequest.
