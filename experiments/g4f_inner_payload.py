"""Compare the actual binary payload inside <IComponent>...</IComponent>
for a known-good native state vs the loader's translated state."""
import dawdreamer as daw
import serum2_preset_loader as loader
import tempfile, os, re, base64

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def extract_icomp_text(state_bytes):
    m = re.search(rb'<IComponent>(.*?)</IComponent>', state_bytes, re.S)
    return m.group(1) if m else None

# native
engine = daw.RenderEngine(SR, 512)
synth = engine.make_plugin_processor("serum", VST3)
fd, p = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(p)
native_full = open(p, "rb").read()
os.remove(p)
native_icomp_text = extract_icomp_text(native_full)

# loader
preset = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"
loader_full = loader.convert_preset_file(preset)
loader_icomp_text = extract_icomp_text(loader_full)

print("native  IComponent text length:", len(native_icomp_text), "  head:", native_icomp_text[:40])
print("loader  IComponent text length:", len(loader_icomp_text), "  head:", loader_icomp_text[:40])

# JUCE MemoryBlock::toBase64Encoding uses a custom alphabet with '.' as one of the chars,
# not standard base64. Let's find juce_memoryblock_b64decode in the loader package itself.
raw_native = loader.juce_memoryblock_b64decode(native_icomp_text.decode('ascii'))
raw_loader = loader.juce_memoryblock_b64decode(loader_icomp_text.decode('ascii'))
print("\ndecoded native  IComponent binary len:", len(raw_native), " head:", raw_native[:24])
print("decoded loader  IComponent binary len:", len(raw_loader), " head:", raw_loader[:24])
