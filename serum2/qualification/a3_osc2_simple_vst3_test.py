"""16.5.69.2-A3: Simple Osc2 Real VST3 Test.

Direct VST3 parameter test of 3 Osc2 representatives.
Actual readback, not stub.
"""

from __future__ import annotations

import json
import tempfile
import os
from pathlib import Path

import dawdreamer as daw
from serum2 import bridge as br
from serum2.evidence import epoch as epoch_mod


def test_osc2_representatives():
    """Test 3 Osc2 representatives via real VST3."""
    print("\n" + "=" * 70)
    print("OSC2 REAL VST3 REPRESENTATIVE TEST")
    print("=" * 70)

    VST3 = epoch_mod.SERUM_VST3

    # Representatives to test
    representatives = [
        {"name": "B Enable", "class": "BOOLEAN", "test_value": 1.0},
        {"name": "B Octave", "class": "INTEGER", "test_value": 0.0},
        {"name": "B Level", "class": "SCALAR", "test_value": 0.75},
    ]

    results = []

    for rep in representatives:
        print(f"\nTesting {rep['name']} [{rep['class']}]...")

        try:
            # Create fresh engine for each test
            engine = daw.RenderEngine(44100, 512)
            synth = engine.make_plugin_processor("serum", VST3)

            # Get parameter index
            params = synth.get_parameters_description()
            param_map = {p["name"]: p["index"] for p in params}

            if rep["name"] not in param_map:
                print(f"  ERROR: Parameter not found in VST3")
                results.append({
                    "name": rep["name"],
                    "class": rep["class"],
                    "success": False,
                    "error": "Parameter not found",
                })
                continue

            param_idx = param_map[rep["name"]]

            # Read baseline
            baseline = synth.get_parameter(param_idx)
            print(f"  Baseline: {baseline}")

            # Set test value
            synth.set_parameter(param_idx, rep["test_value"])
            print(f"  Set to: {rep['test_value']}")

            # Read back
            readback = synth.get_parameter(param_idx)
            print(f"  Readback: {readback}")

            # Check success
            success = abs(float(readback) - float(rep["test_value"])) < 0.01
            print(f"  {'PASS' if success else 'FAIL'}")

            results.append({
                "name": rep["name"],
                "class": rep["class"],
                "baseline": baseline,
                "set_value": rep["test_value"],
                "readback": readback,
                "success": success,
            })

            del engine
            del synth

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "name": rep["name"],
                "class": rep["class"],
                "success": False,
                "error": str(e),
            })

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    passed = sum(1 for r in results if r.get("success"))
    print(f"\nPassed: {passed}/{len(results)}")
    for r in results:
        status = "PASS" if r.get("success") else "FAIL"
        print(f"  {r['name']}: {status}")

    # Save results
    output = {
        "title": "OSC2 Real VST3 Representative Test",
        "tested": len(results),
        "passed": passed,
        "results": results,
        "architecture": {
            "ableton_mcp_serum_surface": "NOT_EXPOSED",
            "serum_vst3_control_surface": "AVAILABLE_VIA_DAWDREAMER",
            "semantic_mcp_plane": "DECOUPLED_FROM_VST3_ADAPTER",
        },
    }

    path = Path("serum2/qualification/A_OSC2_REAL_VST3_REPRESENTATIVE_TEST.json")
    with open(path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved: {path}")


if __name__ == "__main__":
    test_osc2_representatives()
