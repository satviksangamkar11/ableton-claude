import sys
sys.path.insert(0, r"D:\ableton claude\experiments")
from g1_render_lib import render_preset, features

A = r"D:\ableton claude\archive\golden_presets\simple_wavetable.SerumPreset"
B = r"D:\ableton claude\archive\golden_presets\spectral.SerumPreset"

for tag, path in [("A(wavetable)", A), ("B(spectral)", B)]:
    audio = render_preset(path)
    f = features(audio)
    print(tag, f)
