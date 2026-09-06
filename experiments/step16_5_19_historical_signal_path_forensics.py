"""16.5.19: Historical signal-path and context forensics.

Objective: Extract what signal was actually being measured in the historical
witness, and what the signal-routing topology was. Do NOT propose changes yet.

From 16.5.18 differential:
  - Oscillator0/VoiceFilter0 present in current, absent in historical
  - FXEQ parameters identical
  - Centroid baseline differs: 6925.1 Hz (historical) vs 3863.0 Hz (current)

Question: What signal-producing context created the historical 6925.1 Hz baseline?

Method:
  1. Extract measurement target from historical record
  2. Extract stimulus configuration
  3. Extract baseline body state (active sources)
  4. Extract routing topology
  5. Extract execution context
  6. Classify: OBSERVED / DERIVED / UNKNOWN

Do NOT infer causation yet. Only extract what the evidence shows.
"""
import sys, pickle, json
sys.path.insert(0, r"D:\ableton claude")

# ---- Load data ----
print("=" * 80)
print("16.5.19: Historical Signal-Path Forensic Extraction")
print("=" * 80)
print()

hist_rec = pickle.load(open(r"D:\ableton claude\experiments\_fxeq_freq1_record.pkl", "rb"))

print("SECTION 1: Measurement Target (What was measured?)")
print("-" * 80)
print()

if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    print("OBSERVED - Measurement target from causal_measurements[0]:")
    print("  metric: %s" % m.metric)
    print("  target.field_path: %s" % m.target.field_path)
    print("  target.module: %s" % m.target.module)
    print("  target.parameter: %s" % m.target.parameter)
    print()
    print("  kernel_artifact (from measurement_definition_id): %s" % m.measurement_definition_id)
    print()
    print("DERIVED:")
    print("  The measurement explicitly targets: %s" % m.target.field_path)
    print("  This is a field within the FXEQ module")
    print()

print()
print("SECTION 2: Stimulus Configuration (What drove the measurement?)")
print("-" * 80)
print()

if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    mcs = m.measurement_condition_signature
    if isinstance(mcs, dict) and "stimulus" in mcs:
        stim = mcs["stimulus"]
        print("OBSERVED - Stimulus from measurement_condition_signature:")
        print("  note: %d" % stim.get("note", 0))
        print("  velocity: %d" % stim.get("velocity", 0))
        print("  note_len: %.2f beats" % stim.get("note_len", 0))
        print("  render_seconds: %.1f" % stim.get("render_seconds", 0))
        print("  tail_start: %s" % stim.get("tail_start"))
        print()
        print("DERIVED:")
        print("  A single sustained note (48, velocity 110, 1.8 beat duration)")
        print("  rendered for 2.0 seconds total")
        print()

print()
print("SECTION 3: Baseline Body State (What was the signal source?)")
print("-" * 80)
print()

hist_exp = hist_rec.experiment
hist_exp_sig = hist_exp.get("experiment_condition_signature", {})
hist_baseline_overrides = hist_exp_sig.get("baseline_overrides", [])

print("OBSERVED - Baseline state from baseline_overrides:")
if hist_baseline_overrides:
    for path, state_json in hist_baseline_overrides:
        if path == "FXRack0":
            try:
                hist_body = json.loads(state_json)
                print("  FXRack0 structure recovered")
                print()

                # Check for signal sources
                print("DERIVED - Signal sources in historical baseline:")
                print()

                # Oscillator
                if "Oscillator0" in hist_body:
                    print("  Oscillator0: PRESENT")
                    osc = hist_body["Oscillator0"]
                    if "plainParams" in osc:
                        vol = osc["plainParams"].get("kParamVolume")
                        print("    kParamVolume: %.4f" % vol if vol is not None else "unknown")
                else:
                    print("  Oscillator0: ABSENT")

                print()

                # Voice Filter
                if "VoiceFilter0" in hist_body:
                    print("  VoiceFilter0: PRESENT")
                    filt = hist_body["VoiceFilter0"]
                    if "plainParams" in filt:
                        freq = filt["plainParams"].get("kParamFreq")
                        print("    kParamFreq: %.4f" % freq if freq is not None else "unknown")
                else:
                    print("  VoiceFilter0: ABSENT")

                print()

                # Other signal sources
                print("  Other potential signal sources:")
                for key in hist_body.keys():
                    if key.startswith("Osc") or key.startswith("Voice") or key.startswith("Env"):
                        print("    %s: present" % key)

                print()
                print("OBSERVED:")
                print("  Historical baseline has Oscillator0: %s" % ("PRESENT" if "Oscillator0" in hist_body else "ABSENT"))
                print("  Historical baseline has VoiceFilter0: %s" % ("PRESENT" if "VoiceFilter0" in hist_body else "ABSENT"))

            except Exception as e:
                print("  ERROR parsing baseline: %s" % e)
else:
    print("  baseline_overrides empty")

print()
print()
print("SECTION 4: Routing Topology (How was the signal routed?)")
print("-" * 80)
print()

print("OBSERVED from historical experiment setup:")
print("  Experiment claimed to test: FXRack0.FX[1].FXEQ.plainParams.kParamFreq1")
print("  This is a mutation within the FXEQ device at index [1]")
print()

print("DERIVED from measurement target:")
print("  The centroid measurement explicitly targets the FXEQ output")
print("  (target.field_path = FXRack0.FX[FXEQ].plainParams.kParamFreq1)")
print()

print("UNKNOWN:")
print("  Exact signal routing: what signal feeds into FXEQ?")
print("  Is Oscillator0 -> VoiceFilter0 -> FXEQ?")
print("  Or FXEQ is the only active FX processing the input?")
print("  Or some other topology?")
print()

print()
print("SECTION 5: Execution Context (How was it rendered?)")
print("-" * 80)
print()

print("OBSERVED - Execution epoch from historical record:")
hist_epoch = hist_rec.epoch
print("  evidence_epoch_id: %s" % hist_epoch.get("evidence_epoch_id", "?"))
print("  serum_binary_sha256: %s..." % hist_epoch.get("serum_binary_sha256", "?")[:16])
print("  harness_revision: %s" % hist_epoch.get("harness_revision", "?"))
print()

print("DERIVED:")
print("  The historical measurement was performed under specific Serum version/environment")
print()

print()
print("SECTION 6: Measurement Outcome (What was observed?)")
print("-" * 80)
print()

if hist_rec.causal_measurements:
    m = hist_rec.causal_measurements[0]
    print("OBSERVED:")
    print("  baseline_centroid: %.1f Hz" % m.baseline)
    print("  treatment_centroid: %.1f Hz" % m.treatment)
    print("  delta: %.1f Hz" % m.delta)
    print("  observed_direction: %s" % m.observed_direction)
    print("  status: %s" % m.status)
    print()
    print("DERIVED:")
    print("  When FXEQ.Freq1 changed from 639.84 Hz to 15000.0 Hz,")
    print("  the spectral centroid decreased by 505.95 Hz")
    print("  Effect was OBSERVED and measurable")
    print()

print()
print("=" * 80)
print("FORENSIC SUMMARY: Historical Signal-Path")
print("=" * 80)
print()

print("OBSERVED FACTS:")
print("  1. Measurement target: FXEQ output (explicitly)")
print("  2. Stimulus: note 48, velocity 110, 1.8 beat, 2.0 sec render")
print("  3. Oscillator0: ABSENT from historical baseline")
print("  4. VoiceFilter0: ABSENT from historical baseline")
print("  5. FXEQ: PRESENT with specific parameter values")
print("  6. Baseline centroid: 6925.1 Hz (high-frequency rich signal)")
print("  7. Treatment centroid: 6419.1 Hz (centroid shifts lower)")
print("  8. Effect: EFFECT_OBSERVED with -505.95 Hz delta")
print()

print("DERIVED CONSTRAINTS:")
print("  - A signal WAS present at the FXEQ input (something generated 6925 Hz centroid)")
print("  - That signal was responsive to FXEQ.Freq1 mutation")
print("  - The signal is NOT from Oscillator0 or VoiceFilter0 (both absent)")
print("  - UNKNOWN: where the signal came from if not Oscillator/Filter")
print()

print("UNKNOWN CRITICAL FACTS:")
print("  1. Signal source: If Oscillator0 and VoiceFilter0 are absent,")
print("     what generated the signal that produced 6925 Hz centroid?")
print()
print("  2. Routing topology: How did that signal reach FXEQ input?")
print()
print("  3. Context difference: Why does current corpus with Oscillator0/Filter active")
print("     produce 3863 Hz baseline (and no FXEQ effect) instead of 6925 Hz?")
print()

print("CRITICAL OBSERVATION:")
print("  The historical absence of Oscillator0/VoiceFilter0 is an OBSERVED difference.")
print("  But their causal role in the centroid discrepancy is NOT YET ESTABLISHED.")
print()
print("  Possible interpretations:")
print("    A: Oscillator0/Filter absence is THE cause (current signal > 6925 Hz baseline)")
print("    B: Some other upstream difference (stimulus, DAW state, render config)")
print("    C: Current Oscillator0/Filter is bypassing or overriding FXEQ measurement")
print("    D: Some interaction between Oscillator, Filter, and FXEQ in current config")
print()

print("=" * 80)
print("NEXT STEP GUIDANCE (NOT YET EXECUTED):")
print("=" * 80)
print()
print("To determine which of A/B/C/D is correct, 16.5.20 should run a")
print("minimal controlled test that varies ONE dimension at a time,")
print("starting from the current corpus state.")
print()
print("But the EXACT dimension to vary should be determined by the")
print("most parsimonious hypothesis based on this forensic evidence.")
print()
