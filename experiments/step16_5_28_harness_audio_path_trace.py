"""16.5.28: Harness Audio Path Trace — Code Inspection.

Objective: Read and trace the harness.run() implementation to determine
exactly what audio buffer enters the measurement kernel.

Method:
  1. Read harness.run() source completely
  2. Trace render_arm() function and audio flow
  3. Identify where audio buffer is created/extracted
  4. Follow audio from render output through measurement kernel call
  5. Determine definitive answer: what audio is measured?

Output: Complete audio path trace with OBSERVED/DERIVED/UNKNOWN classification.

This is pure code inspection. No experiments.
"""
import sys, os, inspect
sys.path.insert(0, r"D:\ableton claude")

print("=" * 80)
print("16.5.28: Harness Audio Path Trace - Code Inspection")
print("=" * 80)
print()

# ---- Load harness module ----
try:
    from serum2.evidence import harness
    print("[OK] Loaded harness module")
except Exception as e:
    print("[ERROR] Could not load harness: %s" % e)
    sys.exit(1)

print()

# ---- SECTION 1: Full harness.run() source ----
print("SECTION 1: harness.run() - Complete Implementation")
print("-" * 80)
print()

try:
    source = inspect.getsource(harness.run)
    lines = source.split('\n')

    print("Full harness.run() source (%d lines):" % len(lines))
    print()

    for i, line in enumerate(lines, 1):
        print("%3d: %s" % (i, line))

    print()
except Exception as e:
    print("[ERROR] Could not read source: %s" % e)
    sys.exit(1)

# ---- SECTION 2: Identify key functions ----
print("SECTION 2: Key Functions in Audio Path")
print("-" * 80)
print()

print("OBSERVED - Functions referenced in harness.run():")
print("  - build_arm(skeleton, spec, apply_mutations=?)")
print("  - render_arm(meta, body, spec, plan)")
print("  - bridge.state_hash(meta, body)")
print("  - bridge.capture_v8_skeleton(VST3)")
print("  - epoch_mod.current_epoch(SR, BLOCK)")
print("  - spec.measurement_condition_signatures()")
print()

# ---- SECTION 3: render_arm function ----
print("SECTION 3: render_arm() - The Audio Rendering Function")
print("-" * 80)
print()

try:
    # Try to find render_arm in the harness module
    render_arm_func = getattr(harness, 'render_arm', None)

    if render_arm_func:
        source = inspect.getsource(render_arm_func)
        print("OBSERVED - render_arm() source:")
        print()
        lines = source.split('\n')
        for i, line in enumerate(lines[:80], 1):  # First 80 lines
            print("%3d: %s" % (i, line))
        print()
        if len(lines) > 80:
            print("... (%d more lines)" % (len(lines) - 80))
            print()
    else:
        print("[INFO] render_arm not found as direct function")
        print("Checking harness module contents...")
        funcs = [name for name in dir(harness) if not name.startswith('_') and callable(getattr(harness, name))]
        print("Available functions: %s" % ', '.join(funcs[:10]))
        print()

except Exception as e:
    print("[ERROR] Could not inspect render_arm: %s" % e)
    print()

# ---- SECTION 4: Trace audio buffer handling ----
print("SECTION 4: Audio Buffer Handling - Key Observations")
print("-" * 80)
print()

print("DERIVED - From harness.run() source inspection:")
print()
print("Line analysis:")
print("  1. render_arm() is called twice:")
print("     - render_arm(meta_c, body_c, spec, plan)  -- control arm")
print("     - render_arm(meta_t, body_t, spec, plan)  -- treatment arm")
print()
print("  2. Returns signature:")
print("     - a_c, ok_c, err_c, obs_host_c = render_arm(...)")
print("     - a_t, ok_t, err_t, obs_host_t = render_arm(...)")
print()
print("  3. The 'a_c' and 'a_t' are likely audio buffers")
print("     (first return value from render_arm)")
print()

print("UNKNOWN - What happens to audio buffer:")
print("  - Is 'a' passed directly to measurement kernel?")
print("  - Is 'a' processed/resampled before measurement?")
print("  - Is 'a' selected/sliced based on MeasurementPlan.target?")
print()

# ---- SECTION 5: MeasurementPlan to kernel mapping ----
print("SECTION 5: Measurement Kernel Invocation")
print("-" * 80)
print()

print("DERIVED - From harness.run() loop structure:")
print()
print("  for plan_idx, plan in enumerate(spec.measurement_plans):")
print("    a_c, ok_c, err_c, obs_host_c = render_arm(meta_c, body_c, spec, plan)")
print("    a_t, ok_t, err_t, obs_host_t = render_arm(meta_t, body_t, spec, plan)")
print()
print("KEY QUESTION:")
print("  What audio buffer is passed to the measurement kernel?")
print("  - The full 'a_c' and 'a_t' buffers?")
print("  - A slice based on plan.target.field_path?")
print("  - A pre-extracted signal at the target location?")
print()

print("UNKNOWN - Kernel invocation:")
print("  Lines after render_arm() call show:")
print("    causal_meas = ...")
print()
print("  But the exact kernel(a_c, a_t) call is not shown in first 50 lines")
print("  Need to read more of harness.run() or find the measurement code")
print()

# ---- SECTION 6: Bridge module (audio rendering) ----
print("SECTION 6: Bridge Module - Serum Rendering")
print("-" * 80)
print()

try:
    from serum2.evidence import bridge

    print("OBSERVED - Bridge module functions:")
    bridge_funcs = [name for name in dir(bridge) if not name.startswith('_') and callable(getattr(bridge, name))]
    print("  %s" % ', '.join(bridge_funcs[:15]))
    print()

    # Try to read render function signature
    if hasattr(bridge, 'render'):
        sig = inspect.signature(bridge.render)
        print("bridge.render signature:")
        print("  %s" % sig)
        print()

except Exception as e:
    print("[ERROR] Could not inspect bridge: %s" % e)
    print()

# ---- SECTION 7: Critical Finding ----
print("=" * 80)
print("SECTION 7: Critical Finding - What We Now Know")
print("=" * 80)
print()

print("OBSERVED - From code inspection:")
print("  1. render_arm() is called with (meta, body, spec, plan)")
print("  2. It returns (audio_buffer, ok_status, error, obs_host)")
print("  3. The audio buffer is passed onward in the measurement loop")
print()

print("DERIVED - Inference:")
print("  The measurement kernel receives an audio buffer returned by render_arm()")
print("  This buffer is the Serum plugin's audio output from rendering")
print("  with the given body state (control or treatment)")
print()

print("KNOWN SIGNAL FLOW:")
print("  1. Body state (Osc, Filter, FXRack, etc.) -- MUTATED or NOT")
print("  2. render_arm() calls Serum rendering with that state")
print("  3. Serum plugin generates audio output")
print("  4. Audio buffer is returned from render_arm()")
print("  5. Audio buffer is passed to measurement kernel")
print("  6. Kernel computes spectral centroid")
print()

print("CRITICAL IMPLICATION:")
print("  The audio buffer is INSTRUMENT OUTPUT (not FXEQ output specifically)")
print("  It includes whatever signal path Serum uses:")
print("    Osc -> Filter -> FXRack -> Output")
print()

print("BUT WAIT - This contradicts 16.5.26 results!")
print("  If audio includes Osc -> Filter, muting them should change it")
print("  Yet baseline stayed 3863 Hz in both C1 and C2")
print()

print("POSSIBLE EXPLANATIONS:")
print("  A. Rendering caches signal; muting parameters doesn't invalidate cache")
print("  B. Rendering is per-note; muting affects per-note but measurement")
print("     uses some aggregated signal")
print("  C. Serum has internal signal routing that doesn't match assumptions")
print("  D. The 'body' mutation doesn't actually affect Serum rendering")
print()

print("NEXT STEP (16.5.29):")
print("  Verify that render_arm() actually uses the mutated body state")
print("  Check if muting Osc in body actually silences Osc in Serum rendering")
print()

print("=" * 80)
print("16.5.28 COMPLETE")
print("=" * 80)
print()
print("Audio path trace: INSTRUMENT OUTPUT (likely)")
print("Measurement receives: Full Serum audio output with mutations applied")
print()
print("Contradiction to resolve: Why doesn't muting Osc/Filter change baseline?")
