"""G2 -- Direct Serum parameter control. No loader, no .SerumPreset, no Live.
Pick a highly deterministic parameter, change it, render, verify the audio
changes predictably, restore, verify it returns to baseline."""
import dawdreamer as daw
import numpy as np

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100

def new_synth():
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_plugin_processor("serum", VST3)
    return engine, synth

def render(engine, synth, seconds=2.0, note=48, vel=110, note_len=1.5):
    synth.clear_midi()
    synth.add_midi_note(note, vel, 0.0, note_len)
    engine.load_graph([(synth, [])])
    engine.render(seconds)
    return np.asarray(engine.get_audio())

def spectral_centroid(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    n = len(x)
    spec = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    return float(np.sum(freqs * spec) / (np.sum(spec) + 1e-12))

def rms(audio):
    x = audio.mean(axis=0) if audio.ndim == 2 else audio
    return float(np.sqrt(np.mean(x**2)) + 1e-12)

engine, synth = new_synth()
params = synth.get_parameters_description()
cutoff = next((p for p in params if p["name"] == "Filter 1 Freq"), None)
if cutoff is None:
    cutoff = next((p for p in params if "Filter" in p["name"] and "Cut" in p["name"]), None)
print("Target parameter:", cutoff["name"] if cutoff else "NOT FOUND -- listing filter-ish params:")
if cutoff is None:
    for p in params:
        if "filt" in p["name"].lower() or "cut" in p["name"].lower():
            print(" ", p["index"], p["name"])
    raise SystemExit(1)

idx = cutoff["index"]
baseline_val = synth.get_parameter(idx)
print(f"baseline param value (normalized 0-1): {baseline_val}")

# --- Pass 1: baseline render ---
a_base = render(engine, synth)
c_base, r_base = spectral_centroid(a_base), rms(a_base)
print(f"BASELINE   centroid={c_base:.1f} Hz  rms_db={20*np.log10(r_base):.2f}")

# --- Pass 2: extreme low cutoff ---
synth.set_parameter(idx, 0.0)
readback_low = synth.get_parameter(idx)
a_low = render(engine, synth)
c_low, r_low = spectral_centroid(a_low), rms(a_low)
print(f"CUTOFF=0.0 readback={readback_low:.4f}  centroid={c_low:.1f} Hz  rms_db={20*np.log10(r_low):.2f}")

# --- Pass 3: extreme high cutoff ---
synth.set_parameter(idx, 1.0)
readback_high = synth.get_parameter(idx)
a_high = render(engine, synth)
c_high, r_high = spectral_centroid(a_high), rms(a_high)
print(f"CUTOFF=1.0 readback={readback_high:.4f}  centroid={c_high:.1f} Hz  rms_db={20*np.log10(r_high):.2f}")

# --- Pass 4: restore baseline ---
synth.set_parameter(idx, baseline_val)
readback_restored = synth.get_parameter(idx)
a_restored = render(engine, synth)
c_restored = spectral_centroid(a_restored)
print(f"RESTORED   readback={readback_restored:.4f}  centroid={c_restored:.1f} Hz")

print("\n=== VERDICT ===")
print("low != high (audio differs):", abs(c_low - c_high) > 1.0, f"(delta={abs(c_low-c_high):.1f} Hz)")
print("direction correct (low cutoff -> darker/lower centroid):", c_low < c_high)
print("restore ~= baseline:", abs(c_restored - c_base) < max(1.0, 0.05*c_base), f"(delta={abs(c_restored-c_base):.2f} Hz)")

print("\n=== DIAGNOSIS: is Filter 1 actually enabled? ===")
on_idx = next(p["index"] for p in params if p["name"] == "Filter 1 On")
print("Filter 1 On value:", synth.get_parameter(on_idx))

print("\n=== RETEST with Filter 1 explicitly enabled ===")
synth.set_parameter(on_idx, 1.0)
synth.set_parameter(idx, 0.0)
a_low2 = render(engine, synth)
c_low2 = spectral_centroid(a_low2)
synth.set_parameter(idx, 1.0)
a_high2 = render(engine, synth)
c_high2 = spectral_centroid(a_high2)
print(f"Filter1 ON, cutoff=0.0: centroid={c_low2:.1f} Hz")
print(f"Filter1 ON, cutoff=1.0: centroid={c_high2:.1f} Hz")
print("delta:", abs(c_high2 - c_low2), "Hz")
print("direction correct:", c_low2 < c_high2)
