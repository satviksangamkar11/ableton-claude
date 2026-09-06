"""Confirm: does REMOVING IEditController from an otherwise-known-good state
reproduce the silent-default failure? If yes, we've found the actual cause."""
import dawdreamer as daw
import numpy as np
import tempfile, os, re

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def render(engine, synth, seconds=2.0, note=48, vel=110, note_len=1.5):
    synth.clear_midi()
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    return np.asarray(engine.get_audio())

def centroid(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    return float(np.sum(freqs*spec)/(np.sum(spec)+1e-12))

# Build a known-good MUTATED state (audibly different from default)
engineA = daw.RenderEngine(SR, 512)
synthA = engineA.make_plugin_processor("serum", VST3)
paramsA = synthA.get_parameters_description()
idx = lambda n: next(p["index"] for p in paramsA if p["name"] == n)
synthA.set_parameter(idx("Filter 1 On"), 1.0)
synthA.set_parameter(idx("Filter 1 Freq"), 0.1)
a_centroid = centroid(render(engineA, synthA))
print("A (mutated, direct render) centroid:", a_centroid)

fd, full_path = tempfile.mkstemp(suffix=".bin"); os.close(fd)
synthA.save_state(full_path)
full = open(full_path, "rb").read()
os.remove(full_path)

# Strip IEditController section out, keep IComponent + wrapper
m = re.search(rb'(<VST3PluginState><IComponent>.*?</IComponent>)(<IEditController>.*?</IEditController>)?(</VST3PluginState>)', full, re.S)
if not m:
    print("regex did not match -- inspecting raw structure instead")
    print(full[:200])
else:
    hdr_end = full.find(b'<?xml')
    header = full[:hdr_end]
    icomp_only_xml = m.group(1) + m.group(3)
    stripped = header + icomp_only_xml
    print("full state len:", len(full), " | stripped (no IEditController) len:", len(stripped))

    fd, stripped_path = tempfile.mkstemp(suffix=".bin"); os.close(fd)
    open(stripped_path, "wb").write(stripped)

    engineB = daw.RenderEngine(SR, 512)
    synthB = engineB.make_plugin_processor("serum", VST3)
    b_before = centroid(render(engineB, synthB))
    synthB.load_state(stripped_path)
    b_after = centroid(render(engineB, synthB))
    os.remove(stripped_path)

    print("B before load (default):", b_before)
    print("B after load (IEditController-stripped state):", b_after)
    print("\n=== VERDICT ===")
    print("B matches A (fix worked despite stripping):", abs(b_after - a_centroid) < 5.0)
    print("B fell back to its own default (confirms IEditController is required):", abs(b_after - b_before) < 5.0)
