import sys, cbor2
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

def fingerprint(obj, path="root"):
    """Recursively describe container/key/value types -- not just printed values."""
    lines = []
    def walk(o, p):
        t = type(o).__name__
        if isinstance(o, dict):
            lines.append(f"{p}: dict, keys={list(o.keys())!r}, key_types={[type(k).__name__ for k in o.keys()]}")
            for k, v in o.items():
                walk(v, f"{p}.{k!r}")
        elif isinstance(o, list):
            lines.append(f"{p}: list, len={len(o)}, elem_types={[type(x).__name__ for x in o]}")
            for i, v in enumerate(o):
                walk(v, f"{p}[{i}]")
        elif isinstance(o, float):
            lines.append(f"{p}: float, value={o!r}, is_integer_valued={o.is_integer()}")
        elif isinstance(o, int):
            lines.append(f"{p}: int, value={o!r}, bit_length={o.bit_length()}")
        elif isinstance(o, str):
            lines.append(f"{p}: str, value={o!r}, len={len(o)}")
        elif isinstance(o, bytes):
            lines.append(f"{p}: bytes, len={len(o)}")
        else:
            lines.append(f"{p}: {t}, value={o!r}")
    walk(obj, path)
    return lines

meta, skel_body = bridge.capture_v8_skeleton(VST3)
_, preset_body = codec.load_preset_file(r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset")

skel_slot = skel_body["ModSlot0"]
preset_slot = preset_body["ModSlot0"]

print("=== VALUE EQUALITY ===")
print("skel_slot == preset_slot:", skel_slot == preset_slot)
print()
print("=== SKELETON ModSlot0 fingerprint ===")
for l in fingerprint(skel_slot): print(" ", l)
print()
print("=== PRESET (v5-decoded) ModSlot0 fingerprint ===")
for l in fingerprint(preset_slot): print(" ", l)
print()
print("=== RAW CBOR BYTES ===")
skel_cbor = cbor2.dumps(skel_slot)
preset_cbor = cbor2.dumps(preset_slot)
print("skeleton cbor bytes:", skel_cbor.hex())
print("preset  cbor bytes:", preset_cbor.hex())
print("identical bytes:", skel_cbor == preset_cbor)
