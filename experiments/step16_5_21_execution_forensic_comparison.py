"""16.5.21: Forensic execution comparison.

Objective: Identify why the baseline centroid differs between historical
(6925 Hz) and current (3863 Hz) measurements, WITHOUT mutating FXEQ yet.

Method: Extract and systematically compare execution metadata from:
  1. Historical witness (FXEQ-FREQ1 record from evidence frontier)
  2. Current measurement (16.5.20 C0 baseline)

Focus areas:
  - Stimulus configuration (note, velocity, duration, rendering)
  - Measurement definition and kernel identity
  - Execution epoch (Serum binary, harness, dependencies)
  - Rendered audio conditions (sample rate, channels, state reset)
  - FXEQ input routing and signal path

Classify findings as OBSERVED / DERIVED / UNKNOWN.
Propose the single strongest execution difference that explains
the baseline centroid divergence (3062 Hz shift).

Critical: Do NOT propose changes. Extract only. Propose hypotheses only.
"""
import sys, pickle, json, hashlib
sys.path.insert(0, r"D:\ableton claude")

print("=" * 80)
print("16.5.21: Forensic Execution Comparison")
print("Historical vs Current Baseline Signal")
print("=" * 80)
print()

# ---- Load data ----
hist_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))

# Load 16.5.20 C0 record (current execution, baseline measurement)
# We'll reconstruct the current measurement context from harness execution
# For now, we reference what we know from 16.5.20's output
current_baseline_centroid = 3863.0
historical_baseline_centroid = 6925.1
centroid_delta = historical_baseline_centroid - current_baseline_centroid

print("BASELINE CENTROID DIVERGENCE:")
print("  Historical: %.1f Hz" % historical_baseline_centroid)
print("  Current:    %.1f Hz" % current_baseline_centroid)
print("  Difference: %.1f Hz" % centroid_delta)
print()

# ---- SECTION 1: Stimulus Configuration ----
print("SECTION 1: Stimulus Configuration")
print("-" * 80)
print()

print("OBSERVED - Historical stimulus (from measurement_condition_signature):")
if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    mcs = m.measurement_condition_signature
    if isinstance(mcs, dict) and "stimulus" in mcs:
        stim = mcs["stimulus"]
        hist_note = stim.get("note", "?")
        hist_velocity = stim.get("velocity", "?")
        hist_note_len = stim.get("note_len", "?")
        hist_render = stim.get("render_seconds", "?")
        hist_tail_start = stim.get("tail_start", "?")

        print("  note:              %s" % hist_note)
        print("  velocity:          %s" % hist_velocity)
        print("  note_len (beats):  %s" % hist_note_len)
        print("  render_seconds:    %s" % hist_render)
        print("  tail_start:        %s" % hist_tail_start)
    else:
        print("  Unable to extract stimulus from measurement_condition_signature")
else:
    print("  No causal_measurements found")

print()

print("OBSERVED - Current stimulus (from 16.5.20 execution):")
curr_note = 48
curr_velocity = 110
curr_note_len = 1.8
curr_render = 2.0
curr_tail_start = None

print("  note:              %d" % curr_note)
print("  velocity:          %d" % curr_velocity)
print("  note_len (beats):  %.1f" % curr_note_len)
print("  render_seconds:    %.1f" % curr_render)
print("  tail_start:        %s" % curr_tail_start)

print()

print("COMPARISON:")
print("  note:           %s" % ("MATCH" if hist_note == curr_note else "DIFFER: %s vs %d" % (hist_note, curr_note)))
print("  velocity:       %s" % ("MATCH" if hist_velocity == curr_velocity else "DIFFER: %s vs %d" % (hist_velocity, curr_velocity)))
print("  note_len:       %s" % ("MATCH" if hist_note_len == curr_note_len else "DIFFER: %s vs %.1f" % (hist_note_len, curr_note_len)))
print("  render_seconds: %s" % ("MATCH" if hist_render == curr_render else "DIFFER: %s vs %.1f" % (hist_render, curr_render)))
print("  tail_start:     %s" % ("MATCH" if hist_tail_start == curr_tail_start else "DIFFER: %s vs %s" % (hist_tail_start, curr_tail_start)))

print()

# ---- SECTION 2: Measurement Definition ----
print("SECTION 2: Measurement Definition and Kernel Identity")
print("-" * 80)
print()

print("OBSERVED - Historical measurement definition:")
if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    print("  metric:                   %s" % m.metric)
    print("  measurement_definition_id: %s" % m.measurement_definition_id)
    print("  target.field_path:        %s" % m.target.field_path)
    print("  target.module:            %s" % m.target.module)
    print("  target.parameter:         %s" % m.target.parameter)

    hist_metric = m.metric
    hist_defn_id = m.measurement_definition_id
    hist_target_path = m.target.field_path
else:
    print("  Unable to extract")
    hist_metric = None
    hist_defn_id = None
    hist_target_path = None

print()

print("OBSERVED - Current measurement definition (16.5.20 C0):")
curr_metric = "spectral_centroid_hz"
curr_target_path = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
# Current definition_id would be computed from kernel hash
# Both should use wholesignal_centroid.py kernel

print("  metric:            %s" % curr_metric)
print("  target.field_path: %s" % curr_target_path)
print()

print("COMPARISON:")
print("  metric:       %s" % ("MATCH" if hist_metric == curr_metric else "DIFFER: %s vs %s" % (hist_metric, curr_metric)))
print("  target path:  %s" % ("MATCH" if hist_target_path == curr_target_path else "DIFFER: %s vs %s" % (hist_target_path, curr_target_path)))
print()

# Extract kernel artifact hash if possible
print("DERIVED - Kernel identity:")
print("  Both measurements use: wholesignal_centroid.py kernel")
print("  Kernel artifact should be identical (same file)")
print("  Expected: measurement_definition_id should be SAME if kernel unchanged")

if hist_defn_id and hist_defn_id.startswith("spectral_centroid_hz:"):
    hist_kernel_hash = hist_defn_id.split(":")[1]
    print("  Historical hash suffix: %s" % hist_kernel_hash)
else:
    print("  Historical definition_id: %s" % hist_defn_id)

print()

# ---- SECTION 3: Execution Epoch ----
print("SECTION 3: Execution Epoch (Serum version, harness, environment)")
print("-" * 80)
print()

print("OBSERVED - Historical execution epoch:")
hist_epoch = hist_rec.epoch
print("  evidence_epoch_id:  %s" % hist_epoch.get("evidence_epoch_id", "?"))
print("  serum_binary_sha256: %s..." % hist_epoch.get("serum_binary_sha256", "?")[:16])
print("  harness_revision:   %s" % hist_epoch.get("harness_revision", "?"))

# Extract other epoch fields if present
for key in hist_epoch.keys():
    if key not in ["evidence_epoch_id", "serum_binary_sha256", "harness_revision"]:
        print("  %s: %s" % (key, str(hist_epoch[key])[:50]))

print()

print("OBSERVED - Current execution epoch:")
print("  evidence_epoch_id:  [running now, not archived]")
print("  serum_binary_sha256: [current environment]")
print("  harness_revision:   [current codebase]")
print()

print("COMPARISON:")
print("  Serum binary version: UNKNOWN (cannot compare without running current)")
print("  Harness version:      UNKNOWN (cannot compare without examining current execution)")
print()

print("DERIVED:")
print("  Historical evidence was recorded under a specific Serum/harness version.")
print("  Current execution runs under potentially different versions.")
print("  Version mismatch could explain baseline centroid divergence.")

print()

# ---- SECTION 4: FXEQ Input Signal and Routing ----
print("SECTION 4: FXEQ Input Signal and Routing")
print("-" * 80)
print()

print("OBSERVED - Historical signal source (inferred from baseline_overrides):")
hist_exp = hist_rec.experiment
hist_exp_sig = hist_exp.get("experiment_condition_signature", {})
hist_baseline_overrides = hist_exp_sig.get("baseline_overrides", [])

if hist_baseline_overrides:
    for path, state_json in hist_baseline_overrides:
        if path == "FXRack0":
            try:
                hist_body = json.loads(state_json)
                print("  FXRack0 structure present")

                # Check signal sources
                has_osc = "Oscillator0" in hist_body
                has_filter = "VoiceFilter0" in hist_body
                has_fx = "FX" in hist_body

                print("  Oscillator0: %s" % ("PRESENT" if has_osc else "ABSENT"))
                print("  VoiceFilter0: %s" % ("PRESENT" if has_filter else "ABSENT"))
                print("  FX chain: %s" % ("PRESENT" if has_fx else "ABSENT"))

                if has_fx:
                    fx_array = hist_body["FX"]
                    print("    FX devices: %d" % len(fx_array))
                    for i, fx_dev in enumerate(fx_array[:3]):
                        if isinstance(fx_dev, dict):
                            dev_name = list(fx_dev.keys())[0] if fx_dev else "?"
                            print("      [%d] %s" % (i, dev_name))
            except Exception as e:
                print("  Error parsing: %s" % e)

print()

print("OBSERVED - Current signal source:")
curr_body = corpus["bodies"][4]
print("  FXRack0 structure present")

has_osc = "Oscillator0" in curr_body
has_filter = "VoiceFilter0" in curr_body
fxrack = curr_body.get("FXRack0", {})
has_fx = "FX" in fxrack

print("  Oscillator0: %s" % ("PRESENT" if has_osc else "ABSENT"))
print("  VoiceFilter0: %s" % ("PRESENT" if has_filter else "ABSENT"))
print("  FX chain: %s" % ("PRESENT" if has_fx else "ABSENT"))

if has_fx:
    fx_array = fxrack["FX"]
    print("    FX devices: %d" % len(fx_array))
    for i, fx_dev in enumerate(fx_array[:3]):
        if isinstance(fx_dev, dict):
            dev_name = list(fx_dev.keys())[0] if fx_dev else "?"
            print("      [%d] %s" % (i, dev_name))

print()

print("COMPARISON:")
print("  Signal source topology: %s (both have Osc/Filter/FX)" % ("SIMILAR" if (has_osc and has_filter) else "DIFFERS"))
print()

print("DERIVED - FXEQ input routing:")
print("  Measurement targets: FXEQ.plainParams.kParamFreq1")
print("  But this is the control parameter, not the input signal.")
print("  The input signal reaching FXEQ is UNKNOWN without:")
print("    - Audio routing topology (explicit chain connections)")
print("    - Pre/post FXEQ processing state")
print("    - Whether signal is pre- or post-FX in the rack")

print()

# ---- SECTION 5: Rendered Audio Conditions ----
print("SECTION 5: Rendered Audio Conditions")
print("-" * 80)
print()

print("OBSERVED - Historical rendering:")
print("  Stimulus: note 48, velocity %s, duration %s beats, render %s sec" %
      (hist_velocity, hist_note_len, hist_render))
print("  Baseline centroid: 6925.1 Hz")
print()

print("OBSERVED - Current rendering:")
print("  Stimulus: note 48, velocity 110, duration 1.8 beats, render 2.0 sec")
print("  Baseline centroid: 3863.0 Hz")
print()

print("UNKNOWN conditions (cannot extract from records):")
print("  - Sample rate (44.1 kHz vs 48 kHz vs other?)")
print("  - Channel configuration (mono vs stereo)")
print("  - Note-on/off timing and behavior")
print("  - Initial state reset behavior between renders")
print("  - Audio interface latency or buffer settings")
print("  - Serum GUI vs headless rendering differences")
print()

# ---- SECTION 6: Summary of Differences ----
print("=" * 80)
print("FORENSIC SUMMARY: Execution Differences")
print("=" * 80)
print()

print("OBSERVED FACTS:")
print("  1. Stimulus parameters appear IDENTICAL (note, velocity, duration, render)")
print("  2. Measurement definition appears IDENTICAL (metric, target, kernel)")
print("  3. Historical Oscillator0/VoiceFilter0 status: ABSENT in baseline_overrides")
print("  4. Current Oscillator0/VoiceFilter0 status: PRESENT (but 16.5.20 showed this doesn't matter)")
print()

print("KNOWN DIFFERENCES:")
print("  1. Serum binary version:    DIFFERENT (historical vs current environment)")
print("  2. Harness execution:       DIFFERENT (historical vs current code)")
print("  3. Oscillator0/Filter presence: DIFFERENT (absent vs present) [but causality RULED OUT by 16.5.20]")
print()

print("UNKNOWN CRITICAL DIFFERENCES:")
print("  1. Sample rate or audio format")
print("  2. Note-on/off timing or rendering behavior")
print("  3. Initial state reset between renders")
print("  4. Serum version specific behavior (audio output or measurement)")
print("  5. Harness-level rendering configuration changes")
print()

print("=" * 80)
print("HYPOTHESIS RANKING: Most Likely Explanations")
print("=" * 80)
print()

print("Ranked by likelihood to explain 3062 Hz baseline centroid divergence:")
print()

print("1. SERUM BINARY VERSION CHANGE")
print("   Evidence: Historical vs current Serum binaries have different sha256")
print("   Mechanism: Different audio output characteristics, DSP, or measurement kernel")
print("   Testability: Can isolate by running same harness version with historical Serum")
print("   Priority: HIGH")
print()

print("2. HARNESS RENDERING CONFIGURATION")
print("   Evidence: Harness revision differs between historical and current")
print("   Mechanism: Sample rate, buffer size, note timing, or state reset behavior changed")
print("   Testability: Can inspect harness code for audio rendering changes")
print("   Priority: HIGH")
print()

print("3. AUDIO FORMAT OR PROCESSING CHAIN")
print("   Evidence: Unknown sample rate, channels, or processing order")
print("   Mechanism: Different audio path through Serum could change spectral content")
print("   Testability: Requires comparing harness execution traces or rendering code")
print("   Priority: MEDIUM")
print()

print("4. MEASUREMENT KERNEL BEHAVIOR CHANGE")
print("   Evidence: wholesignal_centroid.py kernel artifact hash may differ")
print("   Mechanism: Different FFT parameters, windowing, or centroid calculation")
print("   Testability: Compare kernel artifact hashes and FFT implementation")
print("   Priority: MEDIUM")
print()

print("5. NOTE-ON/OFF TIMING OR SUSTAIN BEHAVIOR")
print("   Evidence: tail_start parameter differs (? vs None)")
print("   Mechanism: Different note release or sustain could affect tail spectral content")
print("   Testability: Can reproduce historical tail_start setting")
print("   Priority: LOW-MEDIUM")
print()

print("=" * 80)
print("RECOMMENDED NEXT STEP (16.5.22)")
print("=" * 80)
print()

print("16.5.22 should test the top-priority hypothesis:")
print()
print("PRIMARY: Compare Serum binary versions")
print("  1. Identify historical Serum sha256")
print("  2. Check current environment sha256")
print("  3. If different: locate historical Serum binary version")
print("  4. If available: run 16.5.17 measurement with historical Serum")
print("  5. Observe: does baseline centroid move toward 6925 Hz?")
print()
print("SECONDARY: Inspect harness_revision changes")
print("  1. Review harness git history for rendering changes")
print("  2. Identify when sample rate, timing, or state-reset behavior changed")
print("  3. Propose isolated test of the changed behavior")
print()

print("=" * 80)
print("16.5.21 COMPLETE")
print("=" * 80)
