# 16.5.57b Test Plan — Bounded Scratch-Set Testing

**Status**: BLOCKED (AbletonMCP not available in this session)  
**Date**: 2026-09-07  
**Phase**: 16.5.57b — mutating tests on disposable scratch Ableton set  

---

## Critical Safety Rule

**NEVER touch the user's real Ableton project.**

All tests below use ONLY a disposable scratch set created for this purpose. After testing:
- Delete scratch set file
- Verify user's project is untouched
- Verify no unsaved changes to user's Live session

---

## Blocking Issue

**AbletonMCP Status**: CONNECTION_CLOSED (session-level)
- Ableton Live 12.3 Suite: Running (PID 44420)
- MCP server processes: Running (14 processes active)
- Claude session MCP access: NOT AVAILABLE
- Implication: Cannot execute any operations requiring AbletonMCP tool calls

**Resolution required**: Reconnect AbletonMCP to this session or spawn a new agent with MCP access.

---

## Test Plan by Question

### Q5: Serum Parameter Mutation + Readback

**Objective**: Verify that Serum parameters can be mutated via AbletonMCP and readback confirms the mutation was applied.

**Setup**:
1. Create scratch set: `[scratchpad]/16_5_57b_scratch_q5.als`
2. Load Serum 2 into track 1
3. Select a simple, already-qualified parameter (e.g., `OSC1.Volume` — CAUSAL_VERIFIED in frontier)

**Test Steps**:

| Step | Action | Expected | Record |
|---|---|---|---|
| 1 | Get device parameters for Serum 2 | Parameter list includes OSC1.Volume | `interface_discovered: true` |
| 2 | Read current OSC1.Volume value | Returns numeric value (0.0–1.0) | `baseline_value: {value}` |
| 3 | Mutate OSC1.Volume to baseline + 0.25 | No error | `mutation_requested: {new_value}` |
| 4 | Read OSC1.Volume again | Returns new value ± 0.02 (within tolerance) | `readback_value: {value}` |
| 5 | Calculate delta | Readback ~= Requested | `delta: {readback - requested}` |

**Success Criteria**:
- Interface discovered: YES (get/set methods available)
- Mutation applied: YES (readback confirms)
- Delta: ≤ 0.02 (AbletonMCP rounding tolerance)

**Record Template**:
```json
{
  "q5_result": {
    "interface_discovered": true,
    "operation_attempted": true,
    "operation_succeeded": true,
    "parameter_name": "OSC1.Volume",
    "baseline_value": <float>,
    "requested_value": <float>,
    "readback_value": <float>,
    "delta": <float>,
    "within_tolerance": true,
    "exact_mechanism": "set_device_parameter('OSC1.Volume', value) → get_device_parameter('OSC1.Volume')",
    "artifacts": []
  }
}
```

---

### Q6: Track + Device + Clip + Notes Creation

**Objective**: Verify that Ableton tracks, Serum 2 devices, MIDI clips, and notes can be created programmatically.

**Setup**:
1. Use same scratch set: `[scratchpad]/16_5_57b_scratch_q5.als` (or create new)

**Test Steps**:

| Step | Action | Expected | Record |
|---|---|---|---|
| 1 | Call `create_midi_track(name='Test Track')` | Track exists in session | `track_created: true`, `track_id: {id}` |
| 2 | Verify track is visible in Live | Visual confirmation | `track_visible: true` |
| 3 | Call `add_device(track_id, 'Serum 2')` | Serum 2 device appears in track | `device_loaded: true`, `device_id: {id}` |
| 4 | Verify device parameters accessible | Can call get_device_parameters | `device_params_accessible: true` |
| 5 | Call `create_clip(track_id, clip_name, start_pos=0, length=4)` | MIDI clip exists | `clip_created: true`, `clip_id: {id}` |
| 6 | Call `add_notes_to_clip(clip_id, notes=[60, 64, 67], velocity=100)` | Notes appear in clip | `notes_added: true`, `note_count: 3` |
| 7 | Verify clip is playable | Can hear MIDI triggering Serum | `playable: true` |

**Success Criteria**:
- All 6 operations succeed
- No error on any step
- Each artifact (track, device, clip, notes) is independently verifiable

**Record Template**:
```json
{
  "q6_result": {
    "interface_discovered": true,
    "operation_attempted": true,
    "operation_succeeded": true,
    "artifacts": [
      {
        "type": "track",
        "name": "Test Track",
        "id": "<track_id>",
        "exists": true
      },
      {
        "type": "device",
        "name": "Serum 2",
        "track_id": "<track_id>",
        "device_id": "<device_id>",
        "exists": true,
        "parameters_accessible": true
      },
      {
        "type": "clip",
        "name": "Test Clip",
        "track_id": "<track_id>",
        "clip_id": "<clip_id>",
        "start_position": 0,
        "length": 4,
        "exists": true
      },
      {
        "type": "notes",
        "clip_id": "<clip_id>",
        "notes": [60, 64, 67],
        "velocity": 100,
        "count": 3,
        "exist": true
      }
    ],
    "exact_mechanism": "create_midi_track() → add_device() → create_clip() → add_notes_to_clip()",
    "limitations": []
  }
}
```

---

### Q7: Processor-State Transport (Import + Extract)

**Objective**: Verify that Serum processor state can be imported from a .SerumPreset and extracted back.

**Setup**:
1. Use scratch set from Q6
2. Known Serum preset file: `C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset`
3. Reference codec: `serum2.codec` can parse .SerumPreset files

**Test Steps**:

| Step | Action | Expected | Record |
|---|---|---|---|
| 1 | Load .SerumPreset file via codec | Parsed successfully into processor state dict | `preset_loaded: true`, `preset_hash: {sha256}` |
| 2 | Load Serum 2 device into track (Q6) | Device ready | `device_loaded: true` |
| 3 | Call `set_device_processor_state(device_id, state_dict)` or equivalent | State applied to Serum device | `state_import_attempted: true` |
| 4 | Call `get_device_processor_state(device_id)` or read `<ProcessorState>` from .als XML | Extract processor state from Ableton | `state_extraction_attempted: true`, `state_extraction_format: {xml|hex|json}` |
| 5 | Compare extracted state to imported state | Bytes/content match or fields match | `state_roundtrip_fidelity: {percent_match}` |
| 6 | Save scratch set and check for `<ProcessorState>` in .als XML | State persists to file | `state_persisted_to_file: true` |

**Success Criteria**:
- State import succeeds (no error)
- State extraction succeeds (can read state from Ableton)
- Roundtrip fidelity ≥ 95% (field-by-field comparison) or byte-identical (if deterministic)

**Known Limitation**: Per PROOF_PLAN.md, manual extraction succeeded once; this test verifies automation. Do NOT assume byte identity unless empirically established.

**Record Template**:
```json
{
  "q7_result": {
    "interface_discovered": true,
    "operation_attempted": true,
    "operation_succeeded": null,  // fill after test
    "source_preset": "ARP - Aardvark.SerumPreset",
    "source_preset_hash": "<sha256>",
    "import_mechanism": "set_device_processor_state(device_id, state_dict)",
    "extraction_mechanism": "get_device_processor_state(device_id) or parse .als XML",
    "extraction_format": "<xml|hex|json>",
    "roundtrip_fidelity": {
      "method": "<field_match | byte_identity | hamming_distance>",
      "score": <float>,
      "is_sufficient": <bool>
    },
    "artifacts": [
      {
        "type": "imported_state_dict",
        "hash": "<sha256>",
        "field_count": <int>
      },
      {
        "type": "extracted_state",
        "hash": "<sha256>",
        "field_count": <int>,
        "source": "AbletonMCP or .als XML"
      }
    ],
    "limitations": "No byte-identity assumption; only field-match verification",
    "exact_mechanism": "(1) Load .SerumPreset via codec → (2) set_device_processor_state → (3) get_device_processor_state → (4) compare"
  }
}
```

---

### Q8: Rendering (Master + Stems)

**Objective**: Verify that the scratch set can be rendered to master audio file and separate stems.

**Setup**:
1. Use scratch set from Q6/Q7 with at least one note playing through Serum
2. Render output paths:
   - Master: `[scratchpad]/16_5_57b_master.wav`
   - Stem 1 (track 1): `[scratchpad]/16_5_57b_stem_track1.wav`

**Test Steps**:

| Step | Action | Expected | Record |
|---|---|---|---|
| 1 | Call `render_to_file(set_path, master_path, stem_paths=[...])` | Render starts | `render_initiated: true`, `render_command: {command_text}` |
| 2 | Wait for render completion (poll or callback) | Files appear on disk | `render_completed: true`, `completion_time_seconds: {time}` |
| 3 | Verify master file exists and is non-empty | File size > 100 KB | `master_file_exists: true`, `master_file_size: {bytes}` |
| 4 | Verify stem files exist and are non-empty | Each stem > 50 KB | `stem_files_exist: true`, `stem_file_sizes: {[sizes]}` |
| 5 | Calculate file hashes | Track identity across reruns | `master_hash: "<sha256>"`, `stem_hashes: [...]` |
| 6 | Decode audio frame count from WAV headers | Verify audio content | `master_frame_count: {frames}`, `master_duration_seconds: {seconds}` |
| 7 | Spot-check: Play master audio and verify Serum sound is audible | Not silent / white noise | `audible_content: true`, `recognizable_as_serum: true` |

**Success Criteria**:
- Render completes without error
- Master file is non-empty and contains audio
- Stems are recoverable as separate files
- Audio is audible and recognizable
- Do NOT accept silent files even if render says "completed successfully"

**Record Template**:
```json
{
  "q8_result": {
    "interface_discovered": true,
    "operation_attempted": true,
    "operation_succeeded": null,  // fill after test
    "render_initiated": true,
    "render_command": "<command_text>",
    "render_completed": true,
    "completion_time_seconds": <float>,
    "artifacts": [
      {
        "type": "master",
        "file_path": "[scratchpad]/16_5_57b_master.wav",
        "exists": true,
        "file_size_bytes": <int>,
        "sha256": "<hash>",
        "duration_seconds": <float>,
        "frame_count": <int>,
        "is_silent": false,
        "contains_recognizable_audio": true
      },
      {
        "type": "stem",
        "stem_name": "track_1",
        "file_path": "[scratchpad]/16_5_57b_stem_track1.wav",
        "exists": true,
        "file_size_bytes": <int>,
        "sha256": "<hash>"
      }
    ],
    "limitations": "Ableton render may complete but produce silent file; verify audio content empirically",
    "exact_mechanism": "render_to_file(set_path, master_path, stem_paths) → wait → verify files → decode WAV headers → spot-check audio"
  }
}
```

---

### Q9: Save / Reopen + State Survival

**Objective**: Verify that the scratch set survives save/reopen cycle and all state persists.

**Setup**:
1. Scratch set from Q8 (already has track, Serum device, notes, rendered audio)
2. Scratch set file path: `[scratchpad]/16_5_57b_scratch_q5.als`

**Test Steps**:

| Step | Action | Expected | Record |
|---|---|---|---|
| 1 | Save scratch set to file | File exists on disk | `save_initiated: true`, `file_path: "[scratchpad]/16_5_57b_scratch_q5.als"` |
| 2 | Verify .als file exists and is non-empty | File > 100 KB | `file_exists: true`, `file_size: {bytes}`, `file_hash: "<sha256>"` |
| 3 | Close Ableton session or close this scratch set | Session/set no longer open | `session_closed: true` |
| 4 | Reopen scratch set file (close and re-launch Live, or use `load_live_set`) | Set opens without error | `set_reopened: true` |
| 5 | Verify track still exists | Track count == pre-close count | `track_count: <int>`, `track_names_match: true` |
| 6 | Verify Serum device still exists and is loaded | Device visible, parameters accessible | `serum_device_exists: true`, `device_parameters_accessible: true` |
| 7 | Verify MIDI clip and notes still exist | Clip visible, note count matches | `clip_exists: true`, `note_count: {matches_baseline}` |
| 8 | Re-extract Serum processor state (Q7) | State matches pre-close state ± tolerance | `state_survival_fidelity: {percent}` |
| 9 | Attempt render again (subset of Q8) | Audio renders without error | `rerender_successful: true` |

**Success Criteria**:
- File persists after close
- Set reopens without error
- All artifacts (track, device, clip, notes) survive
- Serum state can be re-extracted and matches baseline
- Re-render produces audio (even if different from first render; repeatability TBD by Q9)

**Record Template**:
```json
{
  "q9_result": {
    "interface_discovered": true,
    "operation_attempted": true,
    "operation_succeeded": null,  // fill after test
    "save_file_path": "[scratchpad]/16_5_57b_scratch_q5.als",
    "pre_close_state": {
      "track_count": <int>,
      "track_names": [<list>],
      "device_count": <int>,
      "device_names": [<list>],
      "clip_count": <int>,
      "clip_names": [<list>],
      "serum_processor_state_hash": "<sha256>"
    },
    "file_persistence": {
      "file_exists_after_save": true,
      "file_size_bytes": <int>,
      "file_hash_after_save": "<sha256>"
    },
    "reopen_state": {
      "set_reopened_without_error": true,
      "track_count": <int>,
      "track_names_match": true,
      "device_count": <int>,
      "device_names_match": true,
      "clip_count": <int>,
      "clip_names_match": true,
      "serum_device_loaded": true,
      "serum_processor_state_hash": "<sha256>",
      "state_survival_fidelity": <float>
    },
    "rerender_result": {
      "rerender_attempted": true,
      "rerender_successful": true,
      "rerender_produces_audio": true,
      "rerender_file_hash": "<sha256>",
      "hash_matches_first_render": <bool>
    },
    "artifacts": [
      {
        "type": "saved_als_file",
        "path": "[scratchpad]/16_5_57b_scratch_q5.als",
        "hash_before_close": "<sha256>",
        "hash_after_reopen": "<sha256>"
      }
    ],
    "limitations": "Render repeatability not guaranteed; hash may differ. Fidelity measured via field-match, not byte identity.",
    "exact_mechanism": "save() → close() → load() → verify artifacts → re-extract state → rerender"
  }
}
```

---

## Cleanup (After All Tests)

**BEFORE FINISHING**: Execute cleanup in this exact order:

1. Close scratch set file WITHOUT saving (discard any changes from test steps)
2. Delete `[scratchpad]/16_5_57b_scratch_*.als`
3. Delete rendered audio files: `[scratchpad]/16_5_57b_*.wav`
4. Verify user's Ableton project directory is unchanged
5. Check git status: `git status` should show no .als or .wav files in repository
6. Verify Ableton Live session state matches pre-test baseline

**Verification**:
```bash
# Should return nothing (no scratch files)
ls [scratchpad]/16_5_57b_*

# Should show no .als or .wav changes
git status | grep -E "\.als|\.wav"
```

---

## Execution Checklist (for when AbletonMCP becomes available)

- [ ] Q5: Parameter mutation + readback (1 parameter, baseline → baseline+0.25 → readback)
- [ ] Q6: Track/device/clip/notes creation (visual + programmatic verification)
- [ ] Q7: Processor state import/extract (roundtrip ≥ 95% fidelity)
- [ ] Q8: Rendering (master + stems, non-silent, audible)
- [ ] Q9: Save/reopen/state survival (all artifacts persistent, re-extract state, rerender)
- [ ] Cleanup: Delete scratch files, verify no project contamination

---

## Notes for Future Execution

1. **AbletonMCP Interface Requirement**: This plan assumes AbletonMCP tool is available. If connection fails, record as Q5–Q9 BLOCKED.
2. **Scratch Set Only**: NEVER use or modify the user's real project. Create a temporary .als file in scratchpad.
3. **No Silent Acceptance**: Do not call an operation "successful" if interface exists but operation produces no effect (e.g., render completes but audio is silent).
4. **Fidelity vs Identity**: Do not assume byte-identical roundtrip. Field-match ≥ 95% or frame-count equivalence sufficient.
5. **Record Everything**: Each test step must be independently recorded with success/failure and artifact paths/hashes.

