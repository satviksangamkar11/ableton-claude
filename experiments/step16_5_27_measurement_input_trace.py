"""16.5.27: Measurement Input Trace — Forensic Audio Path Analysis.

Objective: Determine what exact audio buffer enters wholesignal_centroid.kernel()
during measurement execution.

Critical question: Is the kernel measuring FXEQ output, FXEQ input, instrument
output, or something else?

Method:
  1. Examine harness.run() implementation
  2. Trace MeasurementPlan target interpretation
  3. Determine audio rendering flow
  4. Identify where the audio buffer comes from
  5. Map the measurement target path to actual audio source
  6. Document current vs historical signal routing
  7. Classify each finding as OBSERVED / DERIVED / UNKNOWN

Output: Complete audio path from render to kernel. No experiments yet.
"""
import sys, os, inspect
sys.path.insert(0, r"D:\ableton claude")

print("=" * 80)
print("16.5.27: Measurement Input Trace — Forensic Audio Path Analysis")
print("=" * 80)
print()

# ---- SECTION 1: Examine harness.run() ----
print("SECTION 1: Harness Execution Flow")
print("-" * 80)
print()

try:
    from serum2.evidence import harness

    print("OBSERVED - harness.run() signature:")
    sig = inspect.signature(harness.run)
    print("  %s" % sig)
    print()

    print("OBSERVED - harness.run() docstring:")
    if harness.run.__doc__:
        lines = harness.run.__doc__.strip().split('\n')[:10]
        for line in lines:
            print("  %s" % line)
    else:
        print("  (no docstring)")
    print()

    # Try to read the source code
    try:
        source = inspect.getsource(harness.run)
        print("OBSERVED - harness.run() source (first 50 lines):")
        print("-" * 80)
        for i, line in enumerate(source.split('\n')[:50], 1):
            print("%3d: %s" % (i, line[:75]))
        print()
    except Exception as e:
        print("Could not read source: %s" % e)
        print()

except Exception as e:
    print("ERROR loading harness: %s" % e)
    print()

# ---- SECTION 2: Examine MeasurementPlan ----
print("SECTION 2: MeasurementPlan and Target Interpretation")
print("-" * 80)
print()

try:
    from serum2.evidence.spec import MeasurementPlan

    print("OBSERVED - MeasurementPlan fields:")
    mp_fields = [f for f in dir(MeasurementPlan) if not f.startswith('_')]
    for field in mp_fields[:15]:
        print("  %s" % field)
    print()

    # Check the docstring
    if MeasurementPlan.__doc__:
        print("MeasurementPlan docstring:")
        print(MeasurementPlan.__doc__[:500])
    print()

except Exception as e:
    print("ERROR: %s" % e)
    print()

# ---- SECTION 3: Audio Rendering Pipeline ----
print("SECTION 3: Audio Rendering Pipeline")
print("-" * 80)
print()

print("DERIVED - Expected rendering flow in harness.run():")
print()
print("  1. Load experiment spec (ExperimentSpec)")
print("  2. Extract skeleton (({}, body))")
print("  3. Create baseline from skeleton[1]")
print("  4. Apply baseline_overrides if present")
print("  5. For each MeasurementPlan:")
print("     a. Apply mutation to create treatment body")
print("     b. Render Serum with baseline body -> audio_control")
print("     c. Render Serum with treatment body -> audio_treatment")
print("     d. Extract audio buffer from render output")
print("     e. Apply measurement kernel to audio buffer")
print("     f. Record measurement result")
print()

# ---- SECTION 4: Measurement Target Path Interpretation ----
print("SECTION 4: Target Path Interpretation")
print("-" * 80)
print()

target_path = "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"

print("OBSERVED - Measurement target from 16.5.20:")
print("  %s" % target_path)
print()

print("DERIVED - Target path interpretation:")
print("  FXRack0 = top-level FX rack")
print("  FX.1 = effect at index [1] in the FX array")
print("  FXEQ = the FXEQ device at that position")
print("  plainParams.kParamFreq1 = the Freq1 parameter")
print()

print("CRITICAL QUESTION:")
print("  Does this target path indicate:")
print("    A. The measurement MEASURES this path's output audio?")
print("    B. The measurement MUTATES this parameter, but measures")
print("       some OTHER audio?")
print("    C. The measurement measures FXEQ INPUT, not output?")
print("    D. The measurement measures the full instrument output?")
print()

print("UNKNOWN - Current implementation detail:")
print("  Which interpretation is correct cannot be determined")
print("  without examining harness code or render logs")
print()

# ---- SECTION 5: Audio Rendering in Serum Context ----
print("SECTION 5: Serum Rendering Architecture")
print("-" * 80)
print()

print("DERIVED - Typical Serum rendering flow:")
print()
print("  Serum instrument structure:")
print("    +-- Oscillator (signal source)")
print("    +-- Voice Filter (per-note filter)")
print("    +-- Wavetable/Modulation")
print("    +-- FXRack (effects)")
print("    |   +-- FX[0] (effect 0)")
print("    |   +-- FX[1] (effect 1, typically FXEQ)")
print("    |   +-- FX[...] (more effects)")
print("    +-- Output (master level)")
print("    +-- Modulation matrix")
print()

print("Signal path options:")
print("  1. Osc -> VoiceFilter -> FXRack -> Output")
print("  2. Osc -> FXRack -> Output (filter bypassed)")
print("  3. FXRack -> Output (Osc/Filter silenced)")
print("  4. Some subset of the above")
print()

print("Measurement could capture:")
print("  - FXRack input (before FX processing)")
print("  - FXRack[1] output (after FXEQ specifically)")
print("  - FXRack final output (after all FX)")
print("  - Instrument master output (post-FXRack)")
print()

# ---- SECTION 6: Historical vs Current Signal Path ----
print("SECTION 6: Historical vs Current Signal Routing")
print("-" * 80)
print()

print("OBSERVED - From 16.5.18 and 16.5.19:")
print()
print("  Historical baseline state (from baseline_overrides):")
print("    FXRack0 = present")
print("    Oscillator0 = ABSENT")
print("    VoiceFilter0 = ABSENT")
print("    FXEQ[0], FXEQ[1] = present with specific params")
print()

print("  Current baseline state:")
print("    FXRack0 = present")
print("    Oscillator0 = present (volume 0.3369)")
print("    VoiceFilter0 = present (freq 0.4706)")
print("    FXEQ[0], FXEQ[1] = present with identical params")
print()

print("KEY DISCREPANCY:")
print("  Historical: Osc/Filter ABSENT")
print("  Current:    Osc/Filter PRESENT")
print()

print("DERIVED - Hypothetical signal sources:")
print()
print("  Historical scenario A:")
print("    Instrument input -> FXRack -> FXEQ[1] -> Output")
print("    (no Osc, no Filter: signal must come from elsewhere)")
print()
print("  Historical scenario B:")
print("    Some pre-rendered or external signal -> FXEQ[1] -> Output")
print()
print("  Current scenario:")
print("    Osc -> Filter -> FXRack -> FXEQ[1] -> Output")
print()

print("QUESTION: Is FXRack receiving input from Osc/Filter,")
print("or is FXRack input sourced separately?")
print()

# ---- SECTION 7: Evidence from 16.5.20/16.5.26 ----
print("SECTION 7: What 16.5.26 Mutation Tells Us")
print("-" * 80)
print()

print("OBSERVED from 16.5.26:")
print("  C1: Osc muted (volume 0.3369 -> 0.0)")
print("      -> baseline centroid stayed 3863 Hz")
print()
print("  C2: Filter muted (freq 0.4706 -> 0.0)")
print("      -> baseline centroid stayed 3863 Hz")
print()

print("INTERPRETATION OPTIONS:")
print()
print("  A. Osc/Filter are not on the measurement signal path")
print("     -> measurement receives pre-Osc signal or synthetic input")
print()
print("  B. Osc/Filter are on the signal path, but muting them")
print("     produces 0 dB signal that still measures ~3863 Hz centroid")
print("     -> measurement includes silence/noise characteristics")
print()
print("  C. The measurement is not measuring FXRack output at all")
print("     -> measurement captures instrument master or pre-FX signal")
print()
print("  D. Rendering is deterministic per-module, and muting Osc/Filter")
print("     produces a canned signal that still measures 3863 Hz")
print("     -> harness rendering does not dynamically resynthesize")
print()

print("UNKNOWN - Which interpretation is correct")
print()

# ---- SECTION 8: Missing Information ----
print("=" * 80)
print("SECTION 8: Critical Missing Information for 16.5.28")
print("=" * 80)
print()

print("To definitively trace the measurement input, we need:")
print()
print("1. Harness rendering code")
print("   QUESTION: What audio buffer does harness.run() return?")
print("   - Instrument output?")
print("   - Specific plugin output?")
print("   - Pre-rendered cache?")
print()

print("2. MeasurementPlan execution logic")
print("   QUESTION: How does target path map to audio buffer selection?")
print("   - Does target.field_path select the audio source?")
print("   - Or does it only identify the control being mutated?")
print()

print("3. Measurement kernel context")
print("   QUESTION: What sample rate and channels does kernel receive?")
print("   - Does kernel receive stereo or mono?")
print("   - Does sample rate affect FFT centroid calculation?")
print()

print("4. Render caching or pre-computation")
print("   QUESTION: Is audio pre-computed or dynamically synthesized?")
print("   - If pre-computed, muting Osc would not affect it")
print("   - If dynamic, muting Osc should reduce high-frequency content")
print()

# ---- SECTION 9: Recommendation ----
print("=" * 80)
print("RECOMMENDATION FOR 16.5.28")
print("=" * 80)
print()

print("To resolve the measurement input ambiguity:")
print()
print("Option A (Code inspection):")
print("  1. Read harness.run() source code")
print("  2. Trace audio buffer from render to kernel")
print("  3. Determine exactly where measurement input comes from")
print()

print("Option B (Experimental probe):")
print("  1. Render with ONLY FXEQ active (all other modules silent)")
print("  2. If baseline changes significantly -> FXEQ receives active signal")
print("  3. If baseline stays ~3863 Hz -> FXEQ receives pre-rendered signal")
print()

print("Option C (Logging/debugging):")
print("  1. Modify measurement to log audio buffer statistics")
print("  2. Check buffer for presence of Osc/Filter frequencies")
print("  3. Determine whether Osc/Filter contributions are present")
print()

print("Highest-value move:")
print("  Option A (code inspection) gives definitive answer fastest")
print("  Option B or C if code inspection is inconclusive")
print()

print("=" * 80)
print("16.5.27 COMPLETE")
print("=" * 80)
print()
print("Status: Measurement input path UNRESOLVED")
print()
print("Next: 16.5.28 must definitively answer:")
print("  'What audio buffer does wholesignal_centroid kernel receive?'")
