"""16.4.3c-6: persistence check on the exact winning [6,0] configuration.
Save state, reload into a FRESH Serum instance, verify LFO0 state and
source=[6,0] survived, re-render at rate=R2 and compare the destination-
response trace against the pre-save render. Nothing else changes."""
import sys, copy, tempfile, os, pickle
sys.path.insert(0, r"D:\ableton claude")
import numpy as np
from serum2 import bridge, codec, pathmerge, vst3_state
import dawdreamer as daw

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
RATE = 4.919910075711187

meta, skel_body = bridge.capture_v8_skeleton(VST3)

def route(source, amount=29.682552814483643):
    return {'destModuleID': 0, 'destModuleParamID': 3, 'destModuleParamName': 'kParamFreq',
           'destModuleTypeString': 'VoiceFilter', 'plainParams': {'kParamAmount': amount}, 'source': source}

m, b = copy.deepcopy(meta), copy.deepcopy(skel_body)
pathmerge.apply_path_value(b, "LFO0.plainParams",
                           {"kParamDefaultMode": 0.0, "kParamMode": "Free", "kParamRate": RATE})
pathmerge.apply_path_value(b, "ModSlot30", route([6, 0]))

def render(m, b, seconds=4.5, note=48, vel=110, note_len=4.0):
    fd, tmp = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    bridge.write_state_file(tmp, m, b)
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    synth.load_state(tmp)
    params = synth.get_parameters_description()
    on_idx = next(p["index"] for p in params if p["name"] == "Filter 1 On")
    synth.set_parameter(on_idx, 1.0)
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    audio = np.asarray(engine.get_audio())
    os.remove(tmp)
    return audio.mean(axis=0) if audio.ndim == 2 else audio, tmp

def per_window_centroid(x, n_windows=200, sr=SR):
    win = len(x) // n_windows
    centroids = []
    for i in range(n_windows):
        seg = x[i*win:(i+1)*win]
        if len(seg) < 64:
            centroids.append(centroids[-1] if centroids else 0.0); continue
        n = len(seg)
        spec = np.abs(np.fft.rfft(seg * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1.0/sr)
        centroids.append(float(np.sum(freqs*spec)/(np.sum(spec)+1e-12)))
    return np.array(centroids)

def signature(trace):
    n = len(trace)
    detr = trace - np.polyval(np.polyfit(np.arange(n), trace, 2), np.arange(n))
    signs = np.sign(detr - np.mean(detr)); signs[signs == 0] = 1
    zc = int(np.sum(np.abs(np.diff(signs)) > 0))
    return float(np.std(detr)), zc

print("=== PRE-SAVE render ===")
x_pre, tmp1 = render(m, b)
amp_pre, zc_pre = signature(per_window_centroid(x_pre))
print(" amp_std=%.3f zero_crossings=%d" % (amp_pre, zc_pre))

print()
print("=== step 1-2: save state, reload into a FRESH engine/synth instance ===")
fd, saved_path = tempfile.mkstemp(suffix=".bin"); os.close(fd)
bridge.write_state_file(saved_path, m, b)

# fresh engine + fresh synth, load from the just-saved file, then re-extract state via re-save
engine2 = daw.RenderEngine(SR, 512)
synth2 = engine2.make_plugin_processor("serum", VST3)
synth2.load_state(saved_path)
fd2, resaved_path = tempfile.mkstemp(suffix=".bin"); os.close(fd2)
synth2.save_state(resaved_path)
raw = open(resaved_path, "rb").read()
meta_reload, body_reload = codec.decode(vst3_state.unwrap_vc2(raw))

print("step 3: reloaded LFO0 state:", body_reload.get("LFO0"))
print("step 4: reloaded ModSlot30 source:", pathmerge.read_path_value(body_reload, "ModSlot30.source"))
lfo_persisted = pathmerge.tolerant_equal(body_reload.get("LFO0", {}).get("plainParams"),
                                        {"kParamDefaultMode": 0.0, "kParamMode": "Free", "kParamRate": RATE})
source_persisted = pathmerge.read_path_value(body_reload, "ModSlot30.source") == [6, 0]
print("LFO0.plainParams persisted exactly:", lfo_persisted)
print("ModSlot30.source==[6,0] persisted:", source_persisted)

print()
print("=== step 5: re-render from the RELOADED state, compare trace to pre-save ===")
x_post, _ = render(meta_reload, body_reload)
amp_post, zc_post = signature(per_window_centroid(x_post))
print(" amp_std=%.3f zero_crossings=%d" % (amp_post, zc_post))
print(" bit-identical audio pre vs post reload:", np.array_equal(x_pre, x_post))
print(" max abs diff:", float(np.max(np.abs(x_pre - x_post))))

print()
print("=== step 6: persistence + causal-behavior-survival verdict ===")
print(" persistence PASS (state):", lfo_persisted and source_persisted)
print(" causal behavior survived (signature matches within tolerance):",
     abs(amp_pre - amp_post) < 1.0 and zc_pre == zc_post)

for p in (tmp1, saved_path, resaved_path):
    try: os.remove(p)
    except OSError: pass
