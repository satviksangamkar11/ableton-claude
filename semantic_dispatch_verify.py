"""
Semantic dispatch verification.
One semantic request object dispatches to two backends:
  - Serum side:   DawDreamer/VST3 (executed here)
  - Ableton side: returns an instruction dict for MCP caller to execute

The MCP caller (Claude) executes the Ableton instruction and patches the result
back into the evidence dict. Both observed values are then collected under
one semantic action ID.
"""
import sys, os, json, tempfile, uuid
sys.path.insert(0, r"D:\ableton claude")

import dawdreamer as daw
from serum2 import bridge, vst3_state, codec
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
SR, BLOCK = 44100, 512

# ── Semantic request ─────────────────────────────────────────────────────────
# One dict describes what both backends must do.
SEMANTIC_REQUEST = {
    "action_id": str(uuid.uuid4())[:8],
    "description": "Producer intent: brighten OSC1 and sync session tempo",
    "serum": {
        "parameter": "A Level",       # semantic name resolves to VST3 param
        "target_value": 0.60,
    },
    "ableton": {
        "operation": "set_tempo",
        "target_value": 128.0,
    },
}

print("SEMANTIC REQUEST")
print("  action_id  : " + SEMANTIC_REQUEST["action_id"])
print("  description: " + SEMANTIC_REQUEST["description"])
print("  serum      : set '" + SEMANTIC_REQUEST["serum"]["parameter"] +
      "' to " + str(SEMANTIC_REQUEST["serum"]["target_value"]))
print("  ableton    : " + SEMANTIC_REQUEST["ableton"]["operation"] +
      " = " + str(SEMANTIC_REQUEST["ableton"]["target_value"]))

evidence = {
    "action_id": SEMANTIC_REQUEST["action_id"],
    "request": SEMANTIC_REQUEST,
    "serum_dispatch": {},
    "ableton_dispatch": {"status": "pending_mcp_caller"},
}

# ── Serum dispatch ────────────────────────────────────────────────────────────
print()
print("DISPATCH -> SERUM (DawDreamer/VST3)")
print("-" * 56)

param_name = SEMANTIC_REQUEST["serum"]["parameter"]
target_val = SEMANTIC_REQUEST["serum"]["target_value"]

print("COMMAND: daw.RenderEngine(44100, 512)")
print("COMMAND: engine.make_plugin_processor('serum', VST3)")
engine = daw.RenderEngine(SR, BLOCK)
synth  = engine.make_plugin_processor("serum", VST3)

print("COMMAND: synth.get_parameters_description()")
params  = synth.get_parameters_description()
by_name = {p["name"]: p["index"] for p in params}

if param_name not in by_name:
    raise RuntimeError("Param not found: " + param_name)

idx = by_name[param_name]
print("OBSERVED: '" + param_name + "' index = " + str(idx))

print("COMMAND: synth.get_parameter(" + str(idx) + ")  [baseline]")
baseline = float(synth.get_parameter(idx))
print("OBSERVED: baseline = " + str(baseline))

print("COMMAND: synth.set_parameter(" + str(idx) + ", " + str(target_val) + ")")
synth.set_parameter(idx, target_val)

print("COMMAND: synth.get_parameter(" + str(idx) + ")  [readback]")
readback = float(synth.get_parameter(idx))
print("OBSERVED: readback = " + str(readback))

serum_ok = abs(readback - target_val) < 0.01
print("EVIDENCE: serum_dispatch.verified = abs(" +
      str(readback) + " - " + str(target_val) + ") < 0.01 = " + str(serum_ok))

print("COMMAND: synth.set_parameter(" + str(idx) + ", " + str(baseline) + ")  [restore]")
synth.set_parameter(idx, baseline)
print("COMMAND: synth.get_parameter(" + str(idx) + ")  [restore readback]")
restored = float(synth.get_parameter(idx))
print("OBSERVED: restored = " + str(restored))
serum_restore_ok = abs(restored - baseline) < 0.01
print("EVIDENCE: serum_dispatch.restore_verified = " + str(serum_restore_ok))

del engine, synth

evidence["serum_dispatch"] = {
    "param_name": param_name,
    "vst3_index": idx,
    "baseline": baseline,
    "target_value": target_val,
    "readback": readback,
    "verified": serum_ok,
    "restored": restored,
    "restore_verified": serum_restore_ok,
}

# ── Ableton instruction for MCP caller ───────────────────────────────────────
print()
print("DISPATCH -> ABLETON (instruction for MCP caller)")
print("-" * 56)
ableton_instruction = {
    "tool": "mcp__AbletonMCP__set_tempo",
    "args": {"tempo": SEMANTIC_REQUEST["ableton"]["target_value"]},
    "readback_tool": "mcp__AbletonMCP__get_session_info",
    "readback_field": "tempo",
    "expected_value": SEMANTIC_REQUEST["ableton"]["target_value"],
    "baseline_tool": "mcp__AbletonMCP__get_session_info",
    "restore_tool": "mcp__AbletonMCP__set_tempo",
}
print("INSTRUCTION: call " + ableton_instruction["tool"] +
      "(tempo=" + str(ableton_instruction["args"]["tempo"]) + ")")
print("INSTRUCTION: readback via " + ableton_instruction["readback_tool"])
print("INSTRUCTION: restore via " + ableton_instruction["restore_tool"])

evidence["ableton_dispatch"]["instruction"] = ableton_instruction
evidence["ableton_dispatch"]["status"] = "awaiting_mcp_execution"

# Save intermediate (Ableton side will be patched in)
from pathlib import Path
out = Path("serum2/qualification/A_SEMANTIC_DISPATCH_VERIFY.json")
with open(out, "w") as f:
    json.dump(evidence, f, indent=2)

print()
print("Serum side complete. Ableton side pending MCP calls.")
print("Saved intermediate: " + str(out))
print("action_id: " + SEMANTIC_REQUEST["action_id"])
