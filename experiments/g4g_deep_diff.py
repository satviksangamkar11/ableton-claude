"""Decode both IComponent XferJson payloads fully (meta + zstd + CBOR) using
our own proven codec, and diff the resulting parameter trees directly."""
import dawdreamer as daw
import serum2_preset_loader as loader
import struct, json, zstandard as zstd, cbor2
import tempfile, os, re

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def extract_icomp_binary(state_bytes):
    m = re.search(rb'<IComponent>(.*?)</IComponent>', state_bytes, re.S)
    text = m.group(1).decode('ascii')
    return loader.juce_memoryblock_b64decode(text)

def decode_xferjson(raw):
    assert raw[:8] == b'XferJson'
    meta_len = struct.unpack('<Q', raw[9:17])[0]
    meta = json.loads(raw[17:17+meta_len])
    tail = raw[17+meta_len:]
    raw_len, mode = struct.unpack('<II', tail[0:8])
    body = cbor2.loads(zstd.ZstdDecompressor().decompress(tail[8:], max_output_size=max(raw_len*4, 1<<22)))
    return meta, body

# native (default patch, straight from Serum itself)
engine = daw.RenderEngine(SR, 512)
synth = engine.make_plugin_processor("serum", VST3)
fd, p = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synth.save_state(p)
native_full = open(p, "rb").read()
os.remove(p)
native_raw = extract_icomp_binary(native_full)
native_meta, native_body = decode_xferjson(native_raw)

# loader (translated from our golden .SerumPreset)
preset = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"
loader_full = loader.convert_preset_file(preset)
loader_raw = extract_icomp_binary(loader_full)
loader_meta, loader_body = decode_xferjson(loader_raw)

print("=== META ===")
print("native meta:", native_meta)
print("loader meta:", loader_meta)

print("\n=== BODY TOP-LEVEL KEYS ===")
print("native keys (%d):" % len(native_body), sorted(native_body.keys())[:10], "...")
print("loader keys (%d):" % len(loader_body), sorted(loader_body.keys())[:10], "...")

print("\nkeys only in native:", set(native_body) - set(loader_body))
print("keys only in loader:", set(loader_body) - set(native_body))
