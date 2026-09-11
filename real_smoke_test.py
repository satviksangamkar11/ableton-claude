"""
Real Smoke Test — Evidence Integrity
Every PASS field derived from an observed result.
No simulated booleans. No manual True assignments.
"""

import sys
import os
import copy
import json
import tempfile
import numpy as np
from pathlib import Path

sys.path.insert(0, r"D:\ableton claude")

import dawdreamer as daw
from serum2 import bridge, codec, vst3_state
from serum2.evidence import epoch as epoch_mod
from serum2.qualification.a3_modulation_adapter import (
    write_modulation,
    read_slot,
    set_modulation_amount,
    remove_modulation,
    find_empty_slot,
)

VST3 = epoch_mod.SERUM_VST3
SR = 44100
BLOCK = 512

results = {
    "title": "Real Smoke Test — Observed Evidence Only",
    "timestamp": "2026-09-11",
    "serum_vst3": VST3,
    "evidence_gates": {},
    "errors": [],
}


# ---------------------------------------------------------------------------
# Helper: load a body into a fresh Serum instance, return the synth + engine
# ---------------------------------------------------------------------------
def make_engine_with_body(meta, body):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    return engine, synth


# ---------------------------------------------------------------------------
# Helper: save_state from a synth, decode, return body
# ---------------------------------------------------------------------------
def read_body_from_synth(synth):
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    synth.save_state(tmp)
    raw = open(tmp, "rb").read()
    os.remove(tmp)
    icomp = vst3_state.unwrap_vc2(raw)
    _, body = codec.decode(icomp)
    return body


# ---------------------------------------------------------------------------
# SECTION 1: OSC1.Volume real mutation
# ---------------------------------------------------------------------------
print("=" * 72)
print("[1/5] OSC1.Volume - Real Mutation (0.75 -> 0.50)")
print("=" * 72)
try:
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    params = synth.get_parameters_description()
    param_by_name = {p["name"]: p["index"] for p in params}

    idx = param_by_name["A Level"]
    baseline = float(synth.get_parameter(idx))
    print("Baseline:  " + str(baseline))

    synth.set_parameter(idx, 0.50)
    readback = float(synth.get_parameter(idx))
    print("Readback:  " + str(readback))

    mutation_ok = abs(readback - 0.50) < 0.01
    print("Mutation verified (readback == 0.50): " + str(mutation_ok))

    synth.set_parameter(idx, baseline)
    restored = float(synth.get_parameter(idx))
    restore_ok = abs(restored - baseline) < 0.01
    print("Restored:  " + str(restored) + "  match: " + str(restore_ok))

    del engine, synth
    results["evidence_gates"]["osc1_volume"] = {
        "baseline": baseline,
        "mutation_target": 0.50,
        "readback": readback,
        "mutation_verified": mutation_ok,
        "restored": restored,
        "restore_verified": restore_ok,
    }
except Exception as e:
    print("ERROR: " + str(e))
    results["errors"].append("osc1_volume: " + str(e))
    results["evidence_gates"]["osc1_volume"] = {"mutation_verified": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SECTION 2: OSC1.Pitch real mutation
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("[2/5] OSC1.Pitch - Real Mutation (0.5 -> 0.0)")
print("=" * 72)
try:
    engine = daw.RenderEngine(SR, BLOCK)
    synth = engine.make_plugin_processor("serum", VST3)
    params = synth.get_parameters_description()
    param_by_name = {p["name"]: p["index"] for p in params}

    idx = param_by_name["A Coarse Pitch"]
    baseline = float(synth.get_parameter(idx))
    print("Baseline:  " + str(baseline))

    synth.set_parameter(idx, 0.0)
    readback = float(synth.get_parameter(idx))
    print("Readback:  " + str(readback))

    mutation_ok = abs(readback - 0.0) < 0.01
    print("Mutation verified (readback == 0.0): " + str(mutation_ok))

    synth.set_parameter(idx, baseline)
    restored = float(synth.get_parameter(idx))
    restore_ok = abs(restored - baseline) < 0.01
    print("Restored:  " + str(restored) + "  match: " + str(restore_ok))

    del engine, synth
    results["evidence_gates"]["osc1_pitch"] = {
        "baseline": baseline,
        "mutation_target": 0.0,
        "readback": readback,
        "mutation_verified": mutation_ok,
        "restored": restored,
        "restore_verified": restore_ok,
    }
except Exception as e:
    print("ERROR: " + str(e))
    results["errors"].append("osc1_pitch: " + str(e))
    results["evidence_gates"]["osc1_pitch"] = {"mutation_verified": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SECTION 3: Modulation lifecycle — real bridge adapter
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("[3/5] Modulation Lifecycle - Real CBOR body via bridge adapter")
print("=" * 72)
try:
    # Step 3a: capture fresh skeleton body
    skeleton_meta, skeleton_body = bridge.capture_v8_skeleton(VST3)
    print("Skeleton captured. ModSlot0 baseline: " + str(skeleton_body.get("ModSlot0")))

    # Step 3b: CREATE — write LFO1 -> Filter1.Cutoff at amount 0.37
    slot_before = find_empty_slot(skeleton_body, start=0)
    print("First empty slot: " + str(slot_before))

    body_after_create, entry_created = write_modulation(
        skeleton_body,
        source="LFO1",
        destination="Filter1.Cutoff",
        amount=0.37,
    )
    created_slot_idx = entry_created.slot_index
    print("CREATE: slot=" + str(created_slot_idx) +
          " source=" + entry_created.source_name +
          " dest=" + entry_created.destination_name +
          " amount_cbor=" + str(entry_created.amount_cbor))

    # Step 3c: VERIFY CREATE — load state into Serum, save_state back, read slot
    engine_c, synth_c = make_engine_with_body(skeleton_meta, body_after_create)
    readback_body_c = read_body_from_synth(synth_c)
    del engine_c, synth_c

    readback_entry = read_slot(readback_body_c, created_slot_idx)
    if readback_entry is None:
        raise RuntimeError("read_slot returned None after create — slot not persisted")

    create_ok = (
        readback_entry.source_name == "LFO1"
        and readback_entry.destination_name == "Filter1.Cutoff"
        and abs(readback_entry.amount_normalized - 0.37) < 0.01
    )
    print("READ after create: source=" + str(readback_entry.source_name) +
          " dest=" + str(readback_entry.destination_name) +
          " amount_norm=" + str(round(readback_entry.amount_normalized, 4)))
    print("CREATE verified: " + str(create_ok))

    # Step 3d: UPDATE — change amount from 0.37 to 0.60
    body_after_update, new_cbor = set_modulation_amount(body_after_create, created_slot_idx, 0.60)
    print("UPDATE: slot=" + str(created_slot_idx) + " new_amount_cbor=" + str(new_cbor))

    engine_u, synth_u = make_engine_with_body(skeleton_meta, body_after_update)
    readback_body_u = read_body_from_synth(synth_u)
    del engine_u, synth_u

    readback_entry_u = read_slot(readback_body_u, created_slot_idx)
    if readback_entry_u is None:
        raise RuntimeError("read_slot returned None after update")

    update_ok = abs(readback_entry_u.amount_normalized - 0.60) < 0.01
    print("READ after update: amount_norm=" + str(round(readback_entry_u.amount_normalized, 4)))
    print("UPDATE verified: " + str(update_ok))

    # Step 3e: REMOVE — clear the slot
    body_after_remove = remove_modulation(body_after_update, created_slot_idx)
    print("REMOVE: slot=" + str(created_slot_idx))

    engine_r, synth_r = make_engine_with_body(skeleton_meta, body_after_remove)
    readback_body_r = read_body_from_synth(synth_r)
    del engine_r, synth_r

    readback_entry_r = read_slot(readback_body_r, created_slot_idx)
    remove_ok = readback_entry_r is None
    slot_val_after_remove = readback_body_r.get("ModSlot" + str(created_slot_idx))
    print("Slot value after remove: " + str(slot_val_after_remove))
    print("REMOVE verified (slot absent): " + str(remove_ok))

    full_cycle_ok = create_ok and update_ok and remove_ok
    print("Full cycle verified: " + str(full_cycle_ok))

    results["evidence_gates"]["modulation_lifecycle"] = {
        "create": {
            "slot_index": created_slot_idx,
            "source": readback_entry.source_name,
            "destination": readback_entry.destination_name,
            "amount_normalized_readback": round(readback_entry.amount_normalized, 4),
            "verified": create_ok,
        },
        "update": {
            "amount_normalized_readback": round(readback_entry_u.amount_normalized, 4),
            "verified": update_ok,
        },
        "remove": {
            "slot_value_after": str(slot_val_after_remove),
            "slot_absent": remove_ok,
            "verified": remove_ok,
        },
        "full_cycle_verified": full_cycle_ok,
    }
except Exception as e:
    print("ERROR: " + str(e))
    results["errors"].append("modulation: " + str(e))
    results["evidence_gates"]["modulation_lifecycle"] = {"full_cycle_verified": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SECTION 4: Audio render — real DawDreamer render, non-silent check
# ---------------------------------------------------------------------------
print()
print("=" * 72)
print("[4/5] Audio Render - Real DawDreamer render, non-silent check")
print("=" * 72)
try:
    engine_rnd = daw.RenderEngine(SR, BLOCK)
    synth_rnd = engine_rnd.make_plugin_processor("serum", VST3)

    # Load skeleton so Serum is in a known state (Filter1 enabled for audibility)
    skeleton_meta_r, skeleton_body_r = bridge.capture_v8_skeleton(VST3)
    fd, tmp_rnd = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    bridge.write_state_file(tmp_rnd, skeleton_meta_r, skeleton_body_r)
    synth_rnd.load_state(tmp_rnd)
    os.remove(tmp_rnd)

    # Enable Filter1 so default preset produces audible output
    params_rnd = synth_rnd.get_parameters_description()
    param_map_rnd = {p["name"]: p["index"] for p in params_rnd}
    filt_on_idx = param_map_rnd.get("Filter 1 On")
    if filt_on_idx is not None:
        synth_rnd.set_parameter(filt_on_idx, 1.0)

    # MIDI: C3 (pitch 60), velocity 100, start 0.0, duration 1.5 s
    synth_rnd.add_midi_note(60, 100, 0.0, 1.5)

    engine_rnd.load_graph([(synth_rnd, [])])
    render_duration = 2.0  # seconds
    engine_rnd.render(render_duration)
    audio = np.asarray(engine_rnd.get_audio())
    del engine_rnd, synth_rnd

    # audio shape: (channels, samples) or (samples,)
    flat = audio.flatten()
    sample_count = len(flat)
    rms = float(np.sqrt(np.mean(flat ** 2)))
    max_abs = float(np.max(np.abs(flat)))
    non_silent = rms > 1e-5  # threshold: any audible signal

    print("Audio shape: " + str(audio.shape))
    print("Sample count: " + str(sample_count))
    print("RMS: " + str(round(rms, 8)))
    print("Max abs: " + str(round(max_abs, 6)))
    print("Non-silent (RMS > 1e-5): " + str(non_silent))

    results["evidence_gates"]["audio_render"] = {
        "render_duration_s": render_duration,
        "midi_note": 60,
        "midi_velocity": 100,
        "audio_shape": list(audio.shape),
        "sample_count": sample_count,
        "rms": round(rms, 8),
        "max_abs": round(max_abs, 6),
        "non_silent": non_silent,
        "render_verified": non_silent,
    }

except Exception as e:
    print("ERROR: " + str(e))
    results["errors"].append("render: " + str(e))
    results["evidence_gates"]["audio_render"] = {"render_verified": False, "error": str(e)}


# ---------------------------------------------------------------------------
# SECTION 5: Ableton tempo — written by caller (MCP tool calls in Claude)
# Placeholder: will be filled from actual MCP readback
# ---------------------------------------------------------------------------
results["evidence_gates"]["ableton_tempo"] = {
    "note": "Populated from actual Ableton MCP calls — see mcp_tempo section"
}


# ---------------------------------------------------------------------------
# Final gate summary
# ---------------------------------------------------------------------------
def safe_get(d, *keys):
    for k in keys:
        if not isinstance(d, dict):
            return False
        d = d.get(k, False)
    return bool(d)

gates = {
    "serum_mutation_verified": safe_get(results, "evidence_gates", "osc1_volume", "mutation_verified"),
    "serum_readback_verified": safe_get(results, "evidence_gates", "osc1_volume", "mutation_verified"),
    "serum_restoration_verified": safe_get(results, "evidence_gates", "osc1_volume", "restore_verified"),
    "serum_pitch_mutation_verified": safe_get(results, "evidence_gates", "osc1_pitch", "mutation_verified"),
    "serum_pitch_restore_verified": safe_get(results, "evidence_gates", "osc1_pitch", "restore_verified"),
    "modulation_cycle_verified": safe_get(results, "evidence_gates", "modulation_lifecycle", "full_cycle_verified"),
    "render_verified": safe_get(results, "evidence_gates", "audio_render", "render_verified"),
    "ableton_tempo_verified": False,   # set after MCP calls in outer script
}
results["gates_summary"] = gates

print()
print("=" * 72)
print("GATE SUMMARY (Ableton tempo pending MCP calls)")
print("=" * 72)
for k, v in gates.items():
    print("  " + k + ": " + str(v))

# Save
out = Path("serum2/qualification/A_REAL_SMOKE_TEST.json")
with open(out, "w") as f:
    json.dump(results, f, indent=2)
print()
print("Saved: " + str(out))
