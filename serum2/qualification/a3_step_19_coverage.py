"""16.5.69.2-A3-19: Full Serum parameter coverage inventory.

Execution sequence:
  1. Enumerate all 2,623 VST3 parameters
  2. Build ParameterEntry inventory with routes and classifications
  3. Run bulk host_param generation check (O(1) Serum loads for all 541 auto params)
  4. Run cbor_body generation check for known-routed params
  5. Carry forward behavior status for H1 pre-qualified targets
  6. Assemble ParameterQualification per entry
  7. Produce machine-readable coverage matrix

Output file: serum2/qualification/A3_STEP_19_COVERAGE_MATRIX.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path


# Pre-qualified behavior status from Steps 14-17
PREQUALIFIED_BEHAVIOR: dict[str, tuple[str, str]] = {
    "Filter.Resonance": (
        "CAUSAL_VERIFIED",
        "Step 17: delta=+2.74 dB RMS with Filter 1 On=1.0, Freq=0.15",
    ),
    "Filter.Type": (
        "CAUSAL_VERIFIED",
        "Step 17: delta=+349 Hz spectral centroid with Filter 1 On=1.0, Freq=0.35",
    ),
    "OSC1.Enable": (
        "CAUSAL_VERIFIED",
        "Step 17: delta=+99.95 dB RMS, arm-specific A Enable 0->1",
    ),
}


def run_step_19() -> dict:
    print("\n" + "=" * 70)
    print("STEP 19: FULL PARAMETER / CONTROL COVERAGE INVENTORY")
    print("=" * 70)

    from serum2 import bridge
    from serum2.evidence import epoch as epoch_mod
    import dawdreamer as daw, tempfile, os

    VST3 = epoch_mod.SERUM_VST3

    # --- 1. Load Serum, enumerate all parameters ---
    print("\n[1/6] Enumerating VST3 parameters...")
    skeleton = bridge.capture_v8_skeleton(VST3)
    meta, body = skeleton

    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    os.remove(tmp)

    raw_params = synth.get_parameters_description()
    print("  Total parameters enumerated: {}".format(len(raw_params)))

    # --- 2. Build inventory ---
    print("\n[2/6] Building ParameterEntry inventory...")
    from serum2.qualification.a3_parameter_inventory import build_inventory, summarize_inventory
    entries = build_inventory(raw_params)
    summary = summarize_inventory(entries)
    print("  Automatable synthesis: {}".format(summary["automatable_synthesis"]))
    print("  MIDI passthrough:      {}".format(summary["midi_passthrough"]))
    print("  Semantically mapped:   {}".format(summary["semantically_identified"]))
    print("  Unmapped:              {}".format(summary["unmapped_semantic"]))
    print("  Mutation class dist:   {}".format(summary["mutation_class_distribution"]))

    # --- 3. Bulk host_param generation check ---
    print("\n[3/6] Running bulk host_param generation check (in-process)...")
    from serum2.qualification.a3_bulk_pipeline import run_bulk_host_param_generation
    t0 = time.time()
    host_param_obs = run_bulk_host_param_generation(entries, VST3, skeleton)
    elapsed = time.time() - t0
    gen_pass = sum(1 for o in host_param_obs.values() if o.status == "PASS")
    gen_fail = sum(1 for o in host_param_obs.values() if o.status == "FAIL")
    gen_na = sum(1 for o in host_param_obs.values() if o.status == "NOT_APPLICABLE")
    print("  Elapsed: {:.3f}s".format(elapsed))
    print("  Generation PASS: {}  FAIL: {}  NOT_APPLICABLE: {}".format(
        gen_pass, gen_fail, gen_na))

    # --- 4. CBOR body generation check for known routes ---
    print("\n[4/6] Running state_mutation generation check for known cbor_body routes...")
    from serum2.qualification.a3_bulk_pipeline import run_cbor_body_generation
    cbor_gen_map = {}
    cbor_entries = [e for e in entries if e.mutation_route.adapter == "cbor_body"]
    for e in cbor_entries:
        obs = run_cbor_body_generation(e, skeleton)
        cbor_gen_map[e.vst3_index] = obs
        print("  {} idx={}: {}".format(e.vst3_name, e.vst3_index, obs.status))

    # --- 5. Assemble qualifications ---
    print("\n[5/6] Assembling per-parameter qualifications...")
    from serum2.qualification.a3_bulk_pipeline import assemble_qualifications, coverage_summary
    qualifications = assemble_qualifications(
        entries,
        host_param_observations=host_param_obs,
        cbor_generation_map=cbor_gen_map,
        behavior_status_map=PREQUALIFIED_BEHAVIOR,
    )
    print("  Assembled {} entries".format(len(qualifications)))

    # --- 6. Build coverage matrix ---
    print("\n[6/6] Computing coverage matrix...")
    matrix = coverage_summary(qualifications)
    matrix["execution_time_seconds"] = round(time.time() - t0, 3)

    # Print matrix
    print()
    print("=" * 70)
    print("STEP 19 COVERAGE MATRIX")
    print("=" * 70)
    for k, v in matrix.items():
        print("  {}: {}".format(k, v))

    # --- Write JSON output ---
    output = {
        "coverage_matrix": matrix,
        "parameters": [q.to_dict() for q in qualifications],
    }

    out_path = Path("serum2/qualification/A3_STEP_19_COVERAGE_MATRIX.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print("\nCoverage matrix written to: {}".format(out_path))

    return matrix


if __name__ == "__main__":
    run_step_19()
