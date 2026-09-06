import dawdreamer as daw
import numpy as np
import serum2_preset_loader as loader
import tempfile, os

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
BLOCK = 512

def make_engine():
    return daw.RenderEngine(SR, BLOCK)

def render_preset(preset_path, seconds=2.0, note=60, vel=100, note_len=1.0):
    engine = make_engine()
    synth = engine.make_plugin_processor("serum", VST3)
    icomp_state = loader.convert_preset_file(preset_path)
    vst3_blob = loader.build_juce_vst3_state(icomp_state)
    fd, tmp = tempfile.mkstemp(suffix='.vstpreset')
    os.close(fd)
    with open(tmp, 'wb') as f:
        f.write(vst3_blob)
    try:
        synth.load_state(tmp)
    finally:
        os.remove(tmp)
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    audio = np.asarray(engine.get_audio())
    return audio

def features(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    rms = float(np.sqrt(np.mean(x**2)) + 1e-12)
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0/SR)
    centroid = float(np.sum(freqs*spec) / (np.sum(spec)+1e-12))
    return dict(rms=rms, rms_db=20*np.log10(rms), centroid_hz=centroid, peak=float(np.max(np.abs(x))))
