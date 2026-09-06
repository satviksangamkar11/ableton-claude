"""G4 forensic diff: known-good Serum-produced state vs loader-translated
state, for the SAME conceptual patch as closely as we can get."""
import dawdreamer as daw
import serum2_preset_loader as loader
import tempfile, os, re

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

# Known-good: fresh Serum instance, default patch, captured via save_state
engine = daw.RenderEngine(SR, 512)
synth = engine.make_plugin_processor("serum", VST3)
fd, good_path = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(good_path)
good = open(good_path, "rb").read()

# Loader-translated: our simple_wavetable golden preset
preset = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"
bad = loader.convert_preset_file(preset)

def strip_header(b):
    # VC2! <u32 len> <u32 mode-ish> then XML text begins at '<?xml'
    i = b.find(b'<?xml')
    return b[:i], b[i:]

good_hdr, good_xml = strip_header(good)
bad_hdr, bad_xml = strip_header(bad)

print("good header bytes:", good_hdr, "len xml:", len(good_xml))
print("bad  header bytes:", bad_hdr, "len xml:", len(bad_xml))

open(r"D:\ableton claude\experiments\good_state.xml", "wb").write(good_xml)
open(r"D:\ableton claude\experiments\bad_state.xml", "wb").write(bad_xml)
os.remove(good_path)

# quick structural comparison: XML tag names present in each
good_tags = set(re.findall(rb'<(\w+)', good_xml))
bad_tags = set(re.findall(rb'<(\w+)', bad_xml))
print("\ntags only in GOOD (Serum-native):", sorted(t.decode() for t in good_tags - bad_tags)[:30])
print("\ntags only in BAD (loader-translated):", sorted(t.decode() for t in bad_tags - good_tags)[:30])
print("\nshared tags:", len(good_tags & bad_tags), "of good:", len(good_tags), "of bad:", len(bad_tags))
