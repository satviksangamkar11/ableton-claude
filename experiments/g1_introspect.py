"""G1 -- State API reconnaissance. Pure introspection, zero preset mutation.
Inspects the six state-related methods on the exact DawDreamer build installed,
so nothing downstream is a guess."""
import dawdreamer as daw
import inspect, sys

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", VST3)

METHODS = ["load_preset", "load_vst3_preset", "get_patch", "set_patch",
           "load_state", "save_state"]

print("DawDreamer version:", daw.__version__)
print("=" * 70)
for name in METHODS:
    print(f"\n--- {name} ---")
    if not hasattr(synth, name):
        print("  NOT PRESENT on this build")
        continue
    m = getattr(synth, name)
    try:
        print("  signature:", inspect.signature(m))
    except (TypeError, ValueError) as e:
        print("  signature: <unavailable via inspect ->", e, ">")
    doc = inspect.getdoc(m)
    print("  doc:", doc if doc else "<no docstring>")

print("\n" + "=" * 70)
print("get_plugin_parameter_size / save_state round-trip probe (no mutation):")
try:
    sz = synth.get_plugin_parameter_size()
    print("  plugin parameter blob size:", sz)
except Exception as e:
    print("  get_plugin_parameter_size failed:", repr(e))

import tempfile, os
try:
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    synth.save_state(tmp)
    raw = open(tmp, "rb").read()
    print("  save_state() wrote", len(raw), "bytes; first 16:", raw[:16])
    os.remove(tmp)
except Exception as e:
    print("  save_state probe failed:", repr(e))
