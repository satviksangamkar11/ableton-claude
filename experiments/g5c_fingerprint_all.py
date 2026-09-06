import sys, cbor2
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
meta, skel_body = bridge.capture_v8_skeleton(VST3)
_, preset_body = codec.load_preset_file(r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset")

for i in range(10):
    key = f"ModSlot{i}"
    s = skel_body.get(key)
    p = preset_body.get(key)
    s_cbor = cbor2.dumps(s)
    p_cbor = cbor2.dumps(p)
    print(f"{key}: value_eq={s==p}  cbor_eq={s_cbor==p_cbor}  "
          f"skel_bytes={s_cbor.hex()}  preset_bytes={p_cbor.hex()}")
