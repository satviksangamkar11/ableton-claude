import sys, copy
sys.path.insert(0, r"D:\ableton claude")
from serum2 import bridge, codec, vst3_state
import dawdreamer as daw
import numpy as np
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
AARDVARK = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"

skeleton = bridge.capture_v8_skeleton(VST3)
_, aardvark_body = codec.load_preset_file(AARDVARK)
real_route = aardvark_body["ModSlot0"]
print("Real Aardvark route:", real_route)

def build_state(modslot0_value):
    meta8, body8 = copy.deepcopy(skeleton[0]), copy.deepcopy(skeleton[1])
    body8["ModSlot0"] = copy.deepcopy(modslot0_value)
    return meta8, body8

def render_windows(state_path, n_windows=8, seconds=2.0, note=48, vel=110, note_len=1.8):
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(state_path)
    params = synth.get_parameters_description()
    on_idx = next(p["index"] for p in params if p["name"] == "Filter 1 On")
    synth.set_parameter(on_idx, 1.0)   # force VoiceFilter audible, identical in every condition
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    audio = np.asarray(engine.get_audio())
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    win = len(x) // n_windows
    centroids = []
    for i in range(n_windows):
        seg = x[i*win:(i+1)*win]
        if len(seg) < 64: continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0/SR)
        c = float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))
        centroids.append(c)
    return centroids

def run(label, modslot0_value):
    meta8, body8 = build_state(modslot0_value)
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, meta8, body8)
    centroids = render_windows(tmp)
    os.remove(tmp)
    print(f"{label:<28} centroids(8 windows): {[round(c,1) for c in centroids]}")
    return centroids

default_route = skeleton[1]["ModSlot0"]
exaggerated_route = copy.deepcopy(real_route)
exaggerated_route["plainParams"]["kParamAmount"] = 100.0

c_baseline = run("BASELINE (no route)", default_route)
c_real = run("REAL Aardvark route (29.68)", real_route)
c_exag = run("EXAGGERATED (amount=100)", exaggerated_route)

print()
print("mean baseline:", np.mean(c_baseline))
print("mean real route:", np.mean(c_real))
print("mean exaggerated:", np.mean(c_exag))
print("real route differs from baseline:", abs(np.mean(c_real)-np.mean(c_baseline)) > 5)
print("exaggerated differs from baseline more than real route does:",
      abs(np.mean(c_exag)-np.mean(c_baseline)) > abs(np.mean(c_real)-np.mean(c_baseline)))
