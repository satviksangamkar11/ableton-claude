"""A1.1 -- Direct VST3 IEditController parameter-surface interrogation.

Independent of vst~'s message layer (which produced NEGATIVE_EVIDENCE for
params/get -4 on Serum 2 -- see owned_host_surface_negative.json). Uses
DawDreamer's get_parameters_description(), which queries the VST3
IEditController directly. Pure introspection, zero mutation, zero preset
load -- modeled on experiments/g1_introspect.py.

Purpose: determine what Serum 2 actually exports via VST3's own parameter
interface, and compare the count/names against the Ableton/MCP 127-parameter
surface already evidenced in SERUM_CONTROL_CAPABILITY_MATRIX.md.
"""
import json
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)

params = synth.get_parameters_description()

print("DawDreamer version:", daw.__version__)
print("VST3 IEditController parameter count:", len(params))
print("=" * 70)

for p in params[:10]:
    print(json.dumps(p, indent=2, default=str))

out_path = "experiments/A1_1_vst3_parameter_surface.json"
with open(out_path, "w") as f:
    json.dump(
        {
            "experiment": "16_5_A1.1",
            "mechanism": "DawDreamer get_parameters_description() -> VST3 IEditController, independent of vst~ message layer",
            "plugin": {"name": "Serum 2", "version": "2.0.21", "format": "VST3", "path": VST3},
            "parameter_count": len(params),
            "parameters": params,
        },
        f,
        indent=2,
        default=str,
    )
print("=" * 70)
print(f"Full parameter list written to {out_path}")
