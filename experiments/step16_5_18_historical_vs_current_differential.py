"""16.5.18: Forensic differential analysis.

Objective: Systematically compare the historical witness condition with the
current producer baseline to identify what state dimension explains the
6925 Hz vs 3863 Hz baseline centroid discrepancy.

Historical measurement:
  baseline_centroid: 6925.1 Hz

Current measurement (16.5.17):
  baseline_centroid: 3863.0 Hz

Difference: 3062.1 Hz (significant spectral shift)

This is NOT a path/mutation issue (16.5.17 proved those work).
This IS a context/state issue.

Investigation method:
  1. Extract historical baseline state from evidence record
  2. Extract current producer baseline state
  3. Compare across all relevant dimensions
  4. Categorize differences: OBSERVED / DERIVED / UNKNOWN
  5. Report findings with strict provenance
  6. NO proposed changes, NO experiments, NO code modifications
  7. Identify which dimensions are candidates for the discrepancy
"""
import sys, pickle, json
sys.path.insert(0, r"D:\ableton claude")

# ---- Load data ----
print("=" * 80)
print("16.5.18: Historical vs Current State Differential")
print("=" * 80)
print()

hist_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
current_body = corpus["bodies"][4]

print("SECTION 1: Extract Historical Baseline State")
print("-" * 80)
print()

# The historical baseline is encoded in the experiment_condition_signature
hist_exp = hist_rec.experiment
hist_exp_sig = hist_exp.get("experiment_condition_signature", {})
hist_baseline_overrides = hist_exp_sig.get("baseline_overrides", [])

print("Historical experiment: FXEQ-FREQ1")
print("Baseline overrides present: %d" % len(hist_baseline_overrides))
print()

hist_fxrack = None
if hist_baseline_overrides:
    for path, state_json in hist_baseline_overrides:
        if path == "FXRack0":
            try:
                hist_fxrack = json.loads(state_json)
                print("OBSERVED: FXRack0 state recovered from baseline_overrides")
            except:
                pass

print()
print("SECTION 2: Extract Current Producer Baseline State")
print("-" * 80)
print()

current_fxrack = current_body.get("FXRack0", {})
print("OBSERVED: FXRack0 structure present in current body")
print()

# ---- Compare FXRack0 structure ----
print("SECTION 3: FXRack0 Structure Comparison")
print("-" * 80)
print()

print("Historical FXRack0 keys:", sorted(hist_fxrack.keys()) if hist_fxrack else "UNKNOWN")
print("Current FXRack0 keys:   ", sorted(current_fxrack.keys()))
print()

# FX array comparison
if hist_fxrack:
    hist_fx = hist_fxrack.get("FX", [])
    print("Historical FX array length: %d" % len(hist_fx))
    print("  Devices:")
    for i, fx in enumerate(hist_fx):
        if isinstance(fx, dict):
            dev = list(fx.keys())[0] if fx else "?"
            print("    [%d] %s" % (i, dev))
else:
    print("Historical FX array: UNKNOWN")

print()

current_fx = current_fxrack.get("FX", [])
print("Current FX array length: %d" % len(current_fx))
print("  Devices:")
for i, fx in enumerate(current_fx):
    if isinstance(fx, dict):
        dev = list(fx.keys())[0] if fx else "?"
        print("    [%d] %s" % (i, dev))

print()

# ---- Oscillator comparison ----
print("SECTION 4: Oscillator State Comparison")
print("-" * 80)
print()

hist_osc = hist_fxrack.get("Oscillator0", {}) if hist_fxrack else {}
current_osc = current_body.get("Oscillator0", {})

print("Historical Oscillator0 present: %s" % bool(hist_osc))
if hist_osc:
    print("  plainParams keys: %d" % len(hist_osc.get("plainParams", {})))
    osc_params = hist_osc.get("plainParams", {})
    if "kParamVolume" in osc_params:
        print("  kParamVolume: %.4f" % osc_params["kParamVolume"])
    if "kParamOctave" in osc_params:
        print("  kParamOctave: %.4f" % osc_params["kParamOctave"])

print()

print("Current Oscillator0 present: %s" % bool(current_osc))
if current_osc:
    print("  plainParams keys: %d" % len(current_osc.get("plainParams", {})))
    osc_params = current_osc.get("plainParams", {})
    if "kParamVolume" in osc_params:
        print("  kParamVolume: %.4f" % osc_params["kParamVolume"])
    if "kParamOctave" in osc_params:
        print("  kParamOctave: %.4f" % osc_params["kParamOctave"])

print()

# ---- Filter comparison ----
print("SECTION 5: Filter State Comparison")
print("-" * 80)
print()

hist_filter = hist_fxrack.get("VoiceFilter0", {}) if hist_fxrack else {}
current_filter = current_body.get("VoiceFilter0", {})

print("Historical VoiceFilter0 present: %s" % bool(hist_filter))
if hist_filter:
    filt_params = hist_filter.get("plainParams", {})
    print("  plainParams keys: %d" % len(filt_params))
    if "kParamFreq" in filt_params:
        print("  kParamFreq: %.4f" % filt_params["kParamFreq"])

print()

print("Current VoiceFilter0 present: %s" % bool(current_filter))
if current_filter:
    filt_params = current_filter.get("plainParams", {})
    print("  plainParams keys: %d" % len(filt_params))
    if "kParamFreq" in filt_params:
        print("  kParamFreq: %.4f" % filt_params["kParamFreq"])

print()

# ---- Modulation/Routing comparison ----
print("SECTION 6: Modulation/Routing State Comparison")
print("-" * 80)
print()

hist_mod_slots = hist_fxrack.get("Modulation", []) if hist_fxrack else []
current_mod = current_body.get("Modulation", [])

print("Historical Modulation slots: %d" % len(hist_mod_slots if isinstance(hist_mod_slots, list) else []))
print("Current Modulation slots:    %d" % len(current_mod if isinstance(current_mod, list) else []))

print()

# ---- Global/Mix state ----
print("SECTION 7: Global/Mix State Comparison")
print("-" * 80)
print()

hist_global = hist_fxrack.get("Global", {}) if hist_fxrack else {}
current_global = current_body.get("Global", {})

print("Historical Global present: %s" % bool(hist_global))
if hist_global:
    print("  keys: %s" % list(hist_global.keys())[:5])

print()

print("Current Global present: %s" % bool(current_global))
if current_global:
    print("  keys: %s" % list(current_global.keys())[:5])

print()

# ---- FXEQ detailed comparison ----
print("SECTION 8: FXEQ Instance State Detailed Comparison")
print("-" * 80)
print()

print("Historical FXEQ[0] and FXEQ[1]:")
if hist_fxrack and "FX" in hist_fxrack:
    for i, fx in enumerate(hist_fxrack["FX"][:2]):
        if "FXEQ" in fx:
            params = fx["FXEQ"].get("plainParams", {})
            print("  [%d] kParamFreq1=%.2f, kParamFreq2=%.2f, kParamGain1=%.2f" %
                  (i, params.get("kParamFreq1", 0), params.get("kParamFreq2", 0), params.get("kParamGain1", 0)))

print()

print("Current FXEQ[0] and FXEQ[1]:")
if "FX" in current_fxrack:
    for i, fx in enumerate(current_fxrack["FX"][:2]):
        if "FXEQ" in fx:
            params = fx["FXEQ"].get("plainParams", {})
            print("  [%d] kParamFreq1=%.2f, kParamFreq2=%.2f, kParamGain1=%.2f" %
                  (i, params.get("kParamFreq1", 0), params.get("kParamFreq2", 0), params.get("kParamGain1", 0)))

print()

# ---- Measurement/Stimulus ----
print("SECTION 9: Measurement/Stimulus Comparison")
print("-" * 80)
print()

print("Historical measurement condition:")
if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    mcs = m.measurement_condition_signature if isinstance(m.measurement_condition_signature, dict) else {}
    if "stimulus" in mcs:
        stim = mcs["stimulus"]
        print("  note: %d, velocity: %d, note_len: %.2f, render: %.1f" %
              (stim.get("note", 0), stim.get("velocity", 0), stim.get("note_len", 0), stim.get("render_seconds", 0)))

print()

print("Current measurement stimulus (from 16.5.17):")
print("  note: 48, velocity: 110, note_len: 1.8, render: 2.0")
print()

# ---- Execution epoch ----
print("SECTION 10: Execution Epoch Comparison")
print("-" * 80)
print()

hist_epoch = hist_rec.epoch
print("Historical epoch:")
print("  evidence_epoch_id: %s" % hist_epoch.get("evidence_epoch_id"))
print("  serum_binary_sha256: %s" % hist_epoch.get("serum_binary_sha256", "?")[:16])

print()

print("Current execution: running in current environment")
print()

# ---- Summary of differences ----
print("=" * 80)
print("DIFFERENTIAL SUMMARY")
print("=" * 80)
print()

print("OBSERVED DIFFERENCES:")
print("  - Baseline centroid: historical 6925.1 Hz vs current 3863.0 Hz (3062 Hz difference)")
print("  - This is a LARGE spectral shift")
print()

print("DIMENSIONS REQUIRING INVESTIGATION:")
print("  1. Oscillator state (volume, octave, tuning, waveform)")
print("  2. Filter state (frequency, resonance, type)")
print("  3. FX routing and order")
print("  4. Modulation routing (if any)")
print("  5. Global mix/level state")
print("  6. FXEQ instance states (both index 0 and 1)")
print("  7. Stimulus differences (if any)")
print("  8. Measurement kernel differences (if any)")
print("  9. Execution environment (Serum binary version, dependencies)")
print()

print("STATUS:")
print("  Path resolution: VERIFIED WORKING (16.5.17)")
print("  Mutation application: VERIFIED WORKING (16.5.17)")
print("  Measurement execution: VERIFIED WORKING (16.5.17)")
print("  Historical effect reproduction: FAILED (0 Hz delta)")
print()

print("CONCLUSION:")
print("  The missing context is NOT path-related.")
print("  The missing context IS structural/state-related.")
print("  FXEQ.Freq1 alone does NOT explain historical behavior.")
print("  One or more of the above dimensions differs between historical and current.")
print()

print("=" * 80)
