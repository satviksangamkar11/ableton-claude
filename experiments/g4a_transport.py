"""G4A -- transport. Figure out what object serum2-preset-loader actually
produces, and route it through the correct DawDreamer API (informed by G1),
instead of guessing."""
import serum2_preset_loader as loader
import inspect

for name in ["convert_preset_file", "convert_preset_bytes", "build_juce_vst3_state"]:
    fn = getattr(loader, name)
    print(f"{name}{inspect.signature(fn)}")
    doc = inspect.getdoc(fn)
    if doc: print("  doc:", doc[:300])

print()
preset = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"
icomp = loader.convert_preset_file(preset)
print("convert_preset_file -> len", len(icomp), "head:", icomp[:16])

vst3blob = loader.build_juce_vst3_state(icomp)
print("build_juce_vst3_state -> len", len(vst3blob), "head:", vst3blob[:16])

# Compare against what DawDreamer's own save_state produces for shape/format match
import dawdreamer as daw, tempfile, os
engine = daw.RenderEngine(44100, 512)
synth = engine.make_plugin_processor("serum", r"C:\Program Files\Common Files\VST3\Serum2.vst3")
fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(tmp)
native = open(tmp, "rb").read()
os.remove(tmp)
print("DawDreamer native save_state -> len", len(native), "head:", native[:16])

print("\nSAME MAGIC (VC2!)? loader-built vs DawDreamer-native:",
      vst3blob[:4] == native[:4] == b'VC2!')
