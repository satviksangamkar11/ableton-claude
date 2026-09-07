#!/usr/bin/env python3
"""16.5.64: Multi-intent compilation and execution."""

import sys
sys.path.insert(0, 'D:\\ableton claude')

from serum2.compiler.mcp_intent import (
    compile_intent, resolve_host_value, make_audit_record
)

# Multi-intent goal: decomposed into explicit parameter intents
# "darker" → decrease cutoff
# "punchier" → increase resonance or decrease attack
# "louder" → increase volume
intents = [
    "Decrease filter cutoff",
    "Increase filter resonance",
    "Increase OSC 1 volume"
]

# Current host values (from readback)
current_values = {
    "Filter.Cutoff": 0.30,    # 379 Hz
    "Filter.Resonance": 0.40, # 40%
    "Env1.Attack": 0.05,      # 0.0 ms
    "OSC1.Volume": 1.0        # 100%
}

print("=" * 70)
print("16.5.64: MULTI-INTENT EXECUTION + BOUNDED OPTIMIZER")
print("=" * 70)
print(f"\nHigh-level goal: 'Make the current bass darker, punchier, and louder'")
print("Decomposed intents (capability-aware):\n")
print("Intents to compile:")
for i, intent in enumerate(intents, 1):
    print(f"  {i}. {intent}")

print("\n" + "-" * 70)
print("COMPILATION RESULTS")
print("-" * 70)

compiled_plans = []
refused = []

for intent in intents:
    result = compile_intent(intent)

    if hasattr(result, '__dataclass_fields__') and 'reason' in result.__dataclass_fields__:
        # IntentRefusal
        refused.append({
            "intent": intent,
            "reason": result.reason,
            "detail": result.detail
        })
        print(f"\nINTENT: {intent}")
        print(f"  STATUS: REFUSED")
        print(f"  REASON: {result.reason}")
        print(f"  DETAIL: {result.detail}")
    else:
        # IntentPlan
        compiled_plans.append(result)
        current_val = current_values.get(result.semantic_target.name, 0.5)
        host_val = resolve_host_value(result, current_val)

        print(f"\nINTENT: {intent}")
        print(f"  SEMANTIC TARGET: {result.semantic_target.name}")
        print(f"  CAPABILITY KEY: {result.capability_key}")
        print(f"  HOST PARAMETER: idx {result.host_param.index} ({result.host_param.name})")
        print(f"  VALUE KIND: {result.value_kind}")
        print(f"  CURRENT VALUE: {current_val:.2f}")
        print(f"  RESOLVED HOST VALUE: {host_val:.2f}")
        print(f"  STATUS: ADMITTED")

print("\n" + "-" * 70)
print("EXECUTION PLAN")
print("-" * 70)
print(f"\nAdmitted: {len(compiled_plans)}")
print(f"Refused: {len(refused)}")

if compiled_plans:
    print("\nMCP write batch (ready for execution):")
    for plan in compiled_plans:
        current_val = current_values.get(plan.semantic_target.name, 0.5)
        host_val = resolve_host_value(plan, current_val)
        print(f"  set_device_parameter(parameter={plan.host_param.index}, value={host_val:.2f})")

if refused:
    print("\nRefused controls (not in MCP_HOST_MAP):")
    for ref in refused:
        print(f"  - {ref['intent']}")
        print(f"    Reason: {ref['reason']}")

print("\n" + "=" * 70)
