"""16.5.37: Historical-Capability Revalidation (post root-cause fix).

INVALIDATION BOUNDARY
---------------------
Root cause confirmed in 16.5.36:
  A 16.5.17 workaround replaced the native processor skeleton with a
  preset-flavor corpus body lacking component="processor", and passed meta={}.
  Serum silently declined that state and rendered its init patch on EVERY arm.

  Sufficiency proven: body["component"]="processor" alone makes the corpus
  body audibly effective (F == E, both != fresh). The 14 preset-metadata
  keys are irrelevant.

All null results from 16.5.17 onward that traversed that path are hereby
marked INVALIDATED -- actuator contamination. They are NOT Serum negative
evidence. This script re-derives the four representative capabilities from
the valid actuator path; it does not restore the old frontier from memory.

Method: identical experimental semantics to 16.5.31 -- same mutation paths,
values, metrics, kernels, thresholds, directions, prerequisites -- but run
through harness.run(spec) with NO skeleton argument, so the harness calls
capture_v8_skeleton() itself. That is the path the historical experiments
used, evidenced by their baselines matching the native default render.

Each capability is classified INDEPENDENTLY. A fixed root cause does not
promote anything automatically.
"""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")

from serum2 import bridge
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                                  MeasurementPlan, validate, SINGLE_FIELD)
from serum2.evidence import harness
from serum2.evidence.measurement import MeasurementTargetRef
from serum2.evidence.record import EFFECT_OBSERVED, NO_OBSERVED_EFFECT, WRONG_DIRECTION
from serum2.evidence import epoch as epoch_mod

VST3 = epoch_mod.SERUM_VST3
STIM = Stimulus(note=48, velocity=110, note_len=1.8, render_seconds=2.0, tail_start=None)

print("=" * 80)
print("16.5.37: Historical-Capability Revalidation (post root-cause fix)")
print("=" * 80)
print()

# ---- Precondition: the actuator path must be sound ----
print("PRECONDITION: native skeleton capture")
print("-" * 80)
try:
    meta_n, body_n = bridge.capture_v8_skeleton(VST3)
    has_component = body_n.get("component")
    print("  capture_v8_skeleton(): OK")
    print("  meta.component = %r   meta.version = %r" % (meta_n.get("component"), meta_n.get("version")))
    print("  body['component'] = %r" % (has_component,))
    if has_component != "processor":
        print("  [STOP] native body lacks component='processor'; actuator unverified.")
        sys.exit(1)
except Exception as e:
    print("  [STOP] capture_v8_skeleton() failed: %s" % e)
    sys.exit(1)
print()

CASES = [
    dict(label="Envelope Attack",
         target_path="Env0",
         value={"plainParams": {"kParamAttack": 0.8}},
         metric="attack_onset_rms_db", kernel="attack_onset_rms_db.py",
         direction="decrease", threshold=3.0,
         h_base=-19.113398409784892, h_treat=-44.975847140950734, h_delta=-25.86244873116584,
         prereqs=[], ctx="12dc2f522836863e"),
    dict(label="Filter Resonance",
         target_path="VoiceFilter0.plainParams.kParamReso",
         value=90.0,
         metric="overall_rms_db", kernel="overall_rms_db.py",
         direction="increase", threshold=1.0,
         h_base=-26.38009085696747, h_treat=-7.924990259745385, h_delta=18.455100597222085,
         prereqs=[], ctx="8d8c276adab7ae3a"),
    dict(label="Global MasterVolume",
         target_path="Global0.plainParams.kParamMasterVolume",
         value=0.1,
         metric="overall_rms_db", kernel="overall_rms_db.py",
         direction="decrease", threshold=3.0,
         h_base=-19.248245789506942, h_treat=-26.23365813883149, h_delta=-6.985412349324548,
         prereqs=[], ctx="12dc2f522836863e"),
    dict(label="ModRoute VoiceFilter",
         target_path="ModSlot0",
         value={"destModuleID": 0, "destModuleParamID": 3,
                "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
                "plainParams": {"kParamAmount": 29.682552814483643}, "source": [6, 0]},
         metric="spectral_centroid_hz", kernel="wholesignal_centroid.py",
         direction="increase", threshold=100.0,
         h_base=348.66527315050166, h_treat=946.0409311097084, h_delta=597.3756579592067,
         prereqs=[Prerequisite("host:Filter 1 On", 1.0, True)], ctx="6755cec516c2a243"),
]

results = []

for c in CASES:
    print("=" * 80)
    print("CASE: %s" % c["label"])
    print("=" * 80)
    print("  path=%s" % c["target_path"])
    print("  value=%s" % str(c["value"])[:80])
    print("  metric=%s  kernel=%s  dir=%s  thr=%s" %
          (c["metric"], c["kernel"], c["direction"], c["threshold"]))
    print("  historical: baseline=%.2f treatment=%.2f delta=%.2f  (ctx %s)" %
          (c["h_base"], c["h_treat"], c["h_delta"], c["ctx"]))
    print()

    spec = ExperimentSpec(
        experiment_id="16.5.37-%s" % c["label"].upper().replace(" ", "-"),
        mutations=[Mutation(c["target_path"], c["value"], "16.5.37 revalidation")],
        prerequisites=list(c["prereqs"]),
        isolation_level=SINGLE_FIELD,
        claim_subject=c["label"].lower().replace(" ", "_"),
        claim_predicate="affects_%s" % c["metric"],
        baseline_overrides=[],
        measurement_plans=[MeasurementPlan(
            metric=c["metric"],
            target=MeasurementTargetRef(c["target_path"], None, None),
            expected_direction=c["direction"], threshold=c["threshold"],
            stimulus=STIM, kernel_artifact=c["kernel"])],
        notes="16.5.37 revalidation via native skeleton (capture_v8_skeleton)",
    )

    row = dict(label=c["label"], hist=c)
    try:
        validate(spec)
        rec = harness.run(spec)            # skeleton=None -> capture_v8_skeleton()
        if not rec or not rec.causal_measurements:
            print("  [ERROR] no measurement")
            row["verdict"] = "INCONCLUSIVE"; row["reason"] = "no measurement"
            results.append(row); print(); continue

        m = rec.causal_measurements[0]
        so = rec.state_observation
        pe = rec.persistence_observation
        print("  current: baseline=%.2f treatment=%.2f delta=%.2f  status=%s" %
              (m.baseline, m.treatment, m.delta, m.status))
        print("  state_diff: matches_intent=%s   persistence: %s" %
              (so.get("matches_intent"), pe.get("status")))

        base_close = abs(m.baseline - c["h_base"]) < max(2.0, abs(c["h_base"]) * 0.10)
        print("  baseline vs historical: %s (%.2f vs %.2f)" %
              ("MATCH" if base_close else "DIFFERS", m.baseline, c["h_base"]))

        if m.status == EFFECT_OBSERVED and m.observed_direction == c["direction"]:
            verdict = "CURRENTLY_REPRODUCED"
        elif m.status == NO_OBSERVED_EFFECT and not base_close:
            verdict = "INCONCLUSIVE"
            row["reason"] = "no effect AND baseline context differs from historical"
        elif m.status == NO_OBSERVED_EFFECT:
            verdict = "CURRENTLY_NOT_REPRODUCED"
        elif m.status == WRONG_DIRECTION:
            verdict = "CURRENTLY_NOT_REPRODUCED"
            row["reason"] = "effect observed in wrong direction"
        else:
            verdict = "INCONCLUSIVE"

        row.update(verdict=verdict, baseline=m.baseline, treatment=m.treatment,
                   delta=m.delta, status=m.status, base_close=base_close,
                   matches_intent=so.get("matches_intent"), persistence=pe.get("status"))
        print("  VERDICT: %s%s" % (verdict, ("  (%s)" % row["reason"]) if row.get("reason") else ""))

    except Exception as e:
        print("  [ERROR] %s" % e)
        import traceback; traceback.print_exc()
        row["verdict"] = "INCONCLUSIVE"; row["reason"] = str(e)[:80]

    results.append(row)
    print()

# ---- Summary ----
print("=" * 80)
print("REVALIDATION SUMMARY")
print("=" * 80)
print()
print("%-24s %-26s %-10s %-10s %s" % ("CAPABILITY", "VERDICT", "delta", "hist_delta", "baseline"))
print("-" * 88)
for r in results:
    d = ("%.2f" % r["delta"]) if "delta" in r else "--"
    b = ("%.2f" % r["baseline"]) if "baseline" in r else "--"
    print("%-24s %-26s %-10s %-10.2f %s" % (r["label"], r["verdict"], d, r["hist"]["h_delta"], b))
print()

n_rep = sum(1 for r in results if r["verdict"] == "CURRENTLY_REPRODUCED")
n_not = sum(1 for r in results if r["verdict"] == "CURRENTLY_NOT_REPRODUCED")
n_inc = sum(1 for r in results if r["verdict"] == "INCONCLUSIVE")
print("CURRENTLY_REPRODUCED:     %d / %d" % (n_rep, len(results)))
print("CURRENTLY_NOT_REPRODUCED: %d / %d" % (n_not, len(results)))
print("INCONCLUSIVE:             %d / %d" % (n_inc, len(results)))
print()

print("=" * 80)
print("INTERPRETATION")
print("=" * 80)
print()
if n_rep == len(results):
    print("All four representative capabilities reproduce through the corrected")
    print("actuator path. The 16.5.31 4/4 failure is confirmed as an artifact of")
    print("actuator contamination, not Serum behavior.")
elif n_rep > 0:
    print("%d of %d reproduce. The contaminated-actuator explanation is supported," % (n_rep, len(results)))
    print("but the remaining case(s) need individual examination -- a fixed root")
    print("cause does not license promoting them.")
else:
    print("None reproduced even through the corrected path. The root-cause fix is")
    print("necessary but not sufficient; investigate before rebuilding any frontier.")
print()
print("Prior null results (16.5.17-16.5.36) remain marked:")
print("  INVALIDATED -- actuator contamination  (not Serum negative evidence)")
print()
print("Non-blocking forensic items retained:")
print("  WHY-CAPTURE-V8-FAILED-1     transient capture failure at 16.5.17")
print("  CORPUS-PROCESSOR-FLAVOR-1   convert corpus at rest vs inject component")
print()
print("=" * 80)
print("16.5.37 COMPLETE")
print("=" * 80)
