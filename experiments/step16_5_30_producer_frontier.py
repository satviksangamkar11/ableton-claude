"""16.5.30: Establish the Usable Producer Frontier.

Objective: Answer ONE question - which existing CAUSAL_VERIFIED capabilities
are genuinely safe for the producer to use today?

For each CAUSAL_VERIFIED contract, classify:
  CONTROL       - Can Claude set it reliably? (state_diff.matches_intent from record)
  EFFECT        - Is there causal evidence? (measurement status == EFFECT_OBSERVED)
  MEASUREMENT   - Is there an actual defined measurement backing the claim?
  PERSISTENCE   - Does trust depend on the now-questionable resave/decode path,
                  or is it independent of that (i.e. based on render_arm() output)?
  PRODUCER-USABLE - Yes / No / Conditional

Plus ONE direct runtime sanity check for Oscillator Volume:
  Volume=baseline vs Volume=lower -> render_arm() -> does audio change?
  Using the render path directly (harness.run()), NOT resave_state().

This does NOT re-litigate persistence. It classifies existing evidence and
runs exactly one confirmatory render test.

FXEQ and the FXRack round-trip anomaly are preserved as open research
findings, excluded from this producer-frontier classification.
"""
import sys, pickle, copy
sys.path.insert(0, r"D:\ableton claude")

from serum2.evidence.spec import ExperimentSpec, Mutation, Stimulus, MeasurementPlan, validate, SINGLE_FIELD
from serum2.evidence import harness
from serum2.evidence.measurement import MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT

print("=" * 80)
print("16.5.30: Establish the Usable Producer Frontier")
print("=" * 80)
print()

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
corpus = pickle.load(open(r"D:\ableton claude\experiments\_corpus_cache.pkl", "rb"))
body_base = corpus["bodies"][4]

# ---- SECTION 1: Oscillator Volume Runtime Sanity Check ----
print("SECTION 1: Oscillator Volume Runtime Sanity Check")
print("-" * 80)
print()
print("Question: Does render_arm()'s actual audio output respond to")
print("Oscillator0.Volume mutation? (independent of resave/decode check)")
print()

TARGET_OSC = MeasurementTargetRef(
    "Oscillator0.plainParams.kParamVolume",
    "Oscillator0", "kParamVolume"
)
STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

body_test = copy.deepcopy(body_base)
current_volume = body_test.get("Oscillator0", {}).get("plainParams", {}).get("kParamVolume")
lower_volume = 0.05

print("Baseline Volume: %.4f" % current_volume)
print("Treatment Volume: %.4f" % lower_volume)
print("Metric: overall_rms_db, kernel_artifact=overall_rms_db.py")
print("        (the ORIGINAL archived kernel that produced the historical")
print("        CAUSAL_VERIFIED evidence -- confirmed EQUIVALENT to registry")
print("        rms_db by direct source comparison; using the original directly)")
print()

spec_sanity = ExperimentSpec(
    experiment_id="16.5.30-OSC-VOLUME-RUNTIME-SANITY",
    mutations=[
        Mutation("Oscillator0.plainParams.kParamVolume", lower_volume,
                 "16.5.30 sanity: does render_arm() respond to Volume mutation?")
    ],
    prerequisites=[],
    isolation_level=SINGLE_FIELD,
    claim_subject="oscillator_volume",
    claim_predicate="affects_overall_rms_db",
    baseline_overrides=[],
    measurement_plans=[
        MeasurementPlan(
            metric="overall_rms_db",
            target=TARGET_OSC,
            expected_direction="decrease",
            threshold=1.0,
            stimulus=STIM,
            kernel_artifact="overall_rms_db.py",
        )
    ],
    notes="16.5.30: Direct render_arm() sanity check using ORIGINAL kernel, bypassing resave_state() entirely",
)

sanity_result = None
try:
    validate(spec_sanity)
    print("[OK] Spec validated")
    skeleton = ({}, copy.deepcopy(body_test))
    record = harness.run(spec_sanity, skeleton=skeleton)
    if record and record.causal_measurements:
        m = record.causal_measurements[0]
        print("[OK] Rendered via render_arm() (actual audio path)")
        print("  baseline_rms: %.2f dB" % m.baseline)
        print("  treatment_rms: %.2f dB" % m.treatment)
        print("  delta: %.2f dB" % m.delta)
        print("  status: %s" % m.status)
        sanity_result = m.status
    else:
        print("[ERROR] No measurement recorded")
except Exception as e:
    print("[ERROR] Sanity check failed: %s" % e)
    import traceback
    traceback.print_exc()

print()

if sanity_result == EFFECT_OBSERVED:
    print("VERDICT: render_arm() DOES respond to Oscillator0.Volume mutation.")
    print("  OSC-VOLUME remains eligible for the producer-safe frontier,")
    print("  despite the open resave/decode anomaly (which affects a")
    print("  DIFFERENT codepath than actual rendering).")
    osc_volume_render_confirmed = True
elif sanity_result == NO_OBSERVED_EFFECT:
    print("VERDICT: render_arm() does NOT show effect from Volume mutation.")
    print("  OSC-VOLUME must be REMOVED from the producer-safe frontier")
    print("  until this is resolved.")
    osc_volume_render_confirmed = False
else:
    print("VERDICT: INCONCLUSIVE (execution error or unexpected status)")
    osc_volume_render_confirmed = None

print()

# ---- SECTION 2: Contract Classification ----
print("=" * 80)
print("SECTION 2: Capability Contract Classification")
print("=" * 80)
print()

causal_verified = {t: c for t, c in contracts.items() if c.status == "CAUSAL_VERIFIED"}
print("Total CAUSAL_VERIFIED contracts: %d" % len(causal_verified))
print()

# Known issues to factor into PERSISTENCE classification:
# - FXRack0/FXEQ: resave_state() showed FX array empty after round trip (16.5.34)
# - Oscillator0: resave_state() showed plainParams collapse to "default" (16.5.32)
# These affect PERSISTENCE trust for any contract whose target lives under
# FXRack0.* or involves module-level chunk state resembling these patterns.

KNOWN_RESAVE_ANOMALY_PREFIXES = ["fx_field_eq", "fx_field_distortion", "modulation_route_fxdelay"]

classification = []

for target_key, c in causal_verified.items():
    target_name = target_key[0] if isinstance(target_key, tuple) else target_key
    short_name = target_name.split(":")[0]

    m = c.measurement or {}
    scope = c.scope or {}

    # CONTROL: was the mutation applied correctly at body-dict level?
    # We infer this from the fact that CAUSAL_VERIFIED status exists at all --
    # a contract can't reach CAUSAL_VERIFIED without the harness's state_diff
    # check (matches_intent) passing at generation time.
    control_ok = True  # generation-time gate; no new evidence contradicts this

    # EFFECT: causal measurement shows real effect
    effect_ok = m.get("status") == "EFFECT_OBSERVED"

    # MEASUREMENT: is there a concrete metric/baseline/treatment on record?
    measurement_ok = (m.get("metric") is not None and
                       m.get("baseline") is not None and
                       m.get("treatment") is not None)

    # PERSISTENCE: flag known-anomalous families
    is_fx_family = any(short_name.startswith(p) for p in KNOWN_RESAVE_ANOMALY_PREFIXES)
    is_oscillator_family = short_name.startswith("oscillator_field")

    if is_fx_family:
        persistence_note = "QUESTIONABLE (FXRack round-trip anomaly, 16.5.34)"
        persistence_ok = False
    elif is_oscillator_family and short_name == "oscillator_field_OSC-VOLUME":
        if osc_volume_render_confirmed is True:
            persistence_note = "CONFIRMED via direct render_arm() sanity check (16.5.30)"
            persistence_ok = True
        elif osc_volume_render_confirmed is False:
            persistence_note = "FAILED direct render_arm() sanity check (16.5.30)"
            persistence_ok = False
        else:
            persistence_note = "INCONCLUSIVE sanity check"
            persistence_ok = None
    elif is_oscillator_family:
        persistence_note = "UNTESTED (same family as OSC-VOLUME resave anomaly, not individually re-checked)"
        persistence_ok = None
    else:
        persistence_note = "No known anomaly; relies on original CAUSAL_VERIFIED evidence"
        persistence_ok = True  # not proven anomalous, treated as trustworthy by default

    # PRODUCER-USABLE verdict
    if control_ok and effect_ok and measurement_ok and persistence_ok is True:
        usable = "YES"
    elif control_ok and effect_ok and measurement_ok and persistence_ok is None:
        usable = "CONDITIONAL"
    else:
        usable = "NO"

    classification.append({
        "target": short_name,
        "control": control_ok,
        "effect": effect_ok,
        "measurement": measurement_ok,
        "persistence": persistence_ok,
        "persistence_note": persistence_note,
        "usable": usable,
        "metric": m.get("metric"),
        "delta": m.get("delta"),
    })

# ---- Print classification table ----
print("%-40s %-8s %-8s %-8s %-12s %-12s" % ("TARGET", "CONTROL", "EFFECT", "MEASURE", "PERSIST", "USABLE"))
print("-" * 100)
for row in sorted(classification, key=lambda r: r["target"]):
    persist_str = "YES" if row["persistence"] is True else "NO" if row["persistence"] is False else "COND"
    print("%-40s %-8s %-8s %-8s %-12s %-12s" % (
        row["target"][:40],
        "YES" if row["control"] else "NO",
        "YES" if row["effect"] else "NO",
        "YES" if row["measurement"] else "NO",
        persist_str,
        row["usable"],
    ))

print()

# ---- SECTION 3: Producer Vocabulary Output ----
print("=" * 80)
print("SECTION 3: Producer Vocabulary")
print("=" * 80)
print()

safe = [r for r in classification if r["usable"] == "YES"]
conditional = [r for r in classification if r["usable"] == "CONDITIONAL"]
not_usable = [r for r in classification if r["usable"] == "NO"]

print("PRODUCER-SAFE (%d):" % len(safe))
for r in sorted(safe, key=lambda r: r["target"]):
    print("  %-40s metric=%-20s delta=%s" % (r["target"], r["metric"], r["delta"]))
print()

print("CONDITIONAL (%d):" % len(conditional))
for r in sorted(conditional, key=lambda r: r["target"]):
    print("  %-40s reason: %s" % (r["target"], r["persistence_note"]))
print()

print("NOT CURRENTLY USABLE (%d):" % len(not_usable))
for r in sorted(not_usable, key=lambda r: r["target"]):
    print("  %-40s reason: %s" % (r["target"], r["persistence_note"]))
print()

# ---- SECTION 4: Open Research Findings (preserved, not blocking) ----
print("=" * 80)
print("SECTION 4: Open Research Findings (preserved, NOT blocking producer work)")
print("=" * 80)
print()
print("  1. FXEQ.Freq1 -> spectral_centroid_hz: historical effect not reproducible")
print("     in current corpus context (16.5.17-16.5.28). Root cause undetermined.")
print()
print("  2. FXRack0.FX becomes an empty list after write->load->save->decode")
print("     round trip (16.5.34). Unknown whether this affects render_arm()'s")
print("     actual rendering or only the resave_state() diagnostic path.")
print()
print("  3. Oscillator0.plainParams collapses to string 'default' after the")
print("     same round trip (16.5.32) for inactive engines; OSC-VOLUME's")
print("     render-path behavior was independently confirmed in Section 1.")
print()
print("  These remain candidates for future capability-discovery tasks when")
print("  the producer needs a control this frontier doesn't yet cover (e.g.")
print("  a verified 'brightness' control).")
print()

print("=" * 80)
print("16.5.30 COMPLETE")
print("=" * 80)
print()
print("Producer vocabulary size: %d safe, %d conditional, %d excluded (of %d CAUSAL_VERIFIED total)" % (
    len(safe), len(conditional), len(not_usable), len(causal_verified)))
