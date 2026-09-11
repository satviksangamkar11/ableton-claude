# Experiment A Harness v0.1 — A0/A1 Recorder

## Purpose

Records raw `vst~` observations into a structured JSON artifact for architectural discovery.

**Scope: A0/A1 only** — host viability + parameter enumeration.

## Files

- `experiment_A_harness.maxpat` — Max visual patch (UI + vst~ binding)
- `experiment_A_harness.js` — JavaScript recorder (normalization only, NO semantic interpretation)
- `owned_host_surface.json` — Output artifact (first real evidence)

## Frozen Recorder Rules

- **vst~ output → JSON normalization.** That's it.
- **NO semantic interpretation.** Do not decide that "A Level" = OSC1.Volume.
- **NO classification.** Do not mark parameter as SCALAR, ENUM, BOOLEAN, etc.
- **NO value interpretation.** Do not decide whether a value is "meaningful."
- **Preserve raw host representation.** 0.63 stays 0.63. Symbolic values as-is.
- **Explicit UNKNOWN for untested.** MIDI, snapshot, audio equivalence = UNKNOWN (not false/null).

## Control Flow

1. **[LOAD SERUM]** → vst~ loads Serum 2.0.21 VST3
2. **[PROBE HOST]** → verify editor/audio viability (A0 checks)
3. **[DUMP PARAMS]** → enumerate all parameters via `vst~ params` (A1)
4. **[EXPORT JSON]** → serialize to `owned_host_surface.json`

## A0 Viability Checks

```
load              → plugin loads successfully
editor_open       → Serum editor window opens
audio_path        → audio input/output connected
midi              → UNKNOWN (not tested in v0.1)
snapshot          → UNKNOWN (not tested in v0.1)
```

## A1 Parameter Enumeration

For each parameter:

```json
{
  "index": 0,
  "name": "Device On",
  "normalized": 0.0,
  "symbolic": "Off",
  "query_timestamp": "..."
}
```

**No interpretation. Just record what vst~ exposes.**

## Output: owned_host_surface.json

```json
{
  "experiment": "16_5_A",
  "run_id": "A0-A1-...",
  "timestamp": "...",
  "host": {
    "application": "Ableton Live",
    "container": "Max for Live",
    "version": "..."
  },
  "plugin": {
    "name": "Serum 2",
    "version": "2.0.21",
    "format": "VST3",
    "identifier": "..."
  },
  "viability": {
    "load": "PASS",
    "editor_open": "PASS",
    "audio_path": "PASS",
    "midi": "UNKNOWN",
    "snapshot": "UNKNOWN"
  },
  "parameters": {
    "count": 127,
    "list": [
      {
        "index": 0,
        "name": "Device On",
        "normalized": 0.0,
        "symbolic": "Off",
        "query_timestamp": "..."
      },
      ...
    ]
  },
  "status": "COMPLETE",
  "artifacts": ["owned_host_surface.json"]
}
```

## Next Steps After v0.1

Once `owned_host_surface.json` exists:

1. **A2 (Python layer)** — Compare with Ableton/MCP 127 parameters
2. **A3 (Python layer)** — Surface characterization (profile mutation classes)
3. **A4-A9** — Built on top of v0.1 artifact

**The harness is a recorder; semantic analysis happens in the repo layer.**

## Usage

1. Open `experiment_A_harness.maxpat` in Max
2. Click [LOAD SERUM]
3. Click [PROBE HOST]
4. Click [DUMP PARAMS]
5. Click [EXPORT JSON]
6. Check `owned_host_surface.json` in the working directory

## Frozen Constraints

- Recorder only. No interpretation.
- Normalize vst~ output to stable JSON schema.
- All parameters enumerated (no filtering).
- Explicit UNKNOWN for untested.
- v0.1 scope: A0/A1 only. A2-A9 happen in Python/repo layer.
