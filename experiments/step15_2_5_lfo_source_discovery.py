"""15.2.5: LFO-source discovery via a discriminating (periodicity-aware)
measurement.

Prior aggregate-only measurements (mean RMS / mean centroid) could not
distinguish "no effect" from "a periodic effect that averages to the same
aggregate" -- this is why LFO-source identification stalled. This experiment
uses two new kernels (modulation_frequency_hz.py, modulation_depth.py,
validated against synthetic ground truth first -- see
_lfo_kernel_validation.txt / the session report) that extract a windowed-RMS
envelope trace, detrend it in log-domain (robust to the note's own
attack/decay/release shape regardless of decay rate), and look for a genuine
spectral line in the residual.

Route structure follows the ALREADY-PROVEN E0/E1 pattern exactly (see
serum2/evidence/fixtures.py): whole-ModSlot30 single_field replacement,
control = skeleton default (empty slot), treatment = a real Aardvark-shaped
route dict with destModuleID/destModuleParamID/destModuleParamName/
destModuleTypeString/plainParams all corpus-real (transplanted from
Aardvark's real ModSlot0 -> VoiceFilter.kParamFreq route), varying ONLY
`source`. Every candidate source id tested here (6, 25, 26, 27, 29, 31) is a
real value observed in Aardvark's own preset body -- none invented.
"""
import sys
sys.path.insert(0, r"D:/ableton claude")
import pickle
from serum2.evidence import harness
from serum2.evidence.spec import (ExperimentSpec, Mutation, Prerequisite, Stimulus,
                                  MeasurementPlan, TargetSpec, SINGLE_FIELD)

VF_TARGET = TargetSpec("VoiceFilter0.plainParams.kParamFreq", "VoiceFilter", "kParamFreq")
# real amount from Aardvark's own ModSlot0->VoiceFilter.kParamFreq route -- reused
# unchanged across candidates so the ONLY declared difference is `source`.
REAL_AMOUNT = 29.682552814483643

# note_len >= render_seconds: stays in the sustain phase for the whole render,
# deliberately avoiding a note-off release-to-near-silence tail. A first pass
# with note_len=3.5/render=4.0 showed BOTH control and treatment reporting an
# identical spurious ~0.5 Hz / huge depth "detection" -- traced to the
# release tail decaying near the log(eps) floor, which the log-domain
# detrend cannot represent as a low-order polynomial (a much harsher kink
# than the synthetic validation's ADSR case). Held-sustain avoids it.
STIM_LONG_SUSTAIN = Stimulus(note=48, velocity=110, note_len=4.5, render_seconds=4.0)

# candidate source ids: real values observed in Aardvark's ModSlot0/4/5/6/12/14.
# 6 is the known-static negative control (Aardvark ModSlot0, already shown flat
# under the old aggregate method); the rest are untested under ANY discriminating
# method.
CANDIDATES = {
    "SRC-6":  {"source_id": 6,  "label": "Aardvark ModSlot0 (source=6) -- negative control, known static"},
    "SRC-25": {"source_id": 25, "label": "Aardvark ModSlot4 (source=25) -- untested"},
    "SRC-26": {"source_id": 26, "label": "Aardvark ModSlot5 (source=26) -- untested"},
    "SRC-27": {"source_id": 27, "label": "Aardvark ModSlot6 (source=27) -- untested"},
    "SRC-29": {"source_id": 29, "label": "Aardvark ModSlot12 (source=29) -- untested"},
    "SRC-31": {"source_id": 31, "label": "Aardvark ModSlot14 (source=31) -- untested"},
}


def route_for(source_id):
    return {
        "destModuleID": 0, "destModuleParamID": 3,
        "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
        "plainParams": {"kParamAmount": REAL_AMOUNT}, "source": [source_id, 0],
    }


def build_spec(exp_id, source_id, label):
    route = route_for(source_id)
    return ExperimentSpec(
        experiment_id=exp_id,
        mutations=[Mutation("ModSlot30", route, "Aardvark-shaped route, source=%d (%s)" % (source_id, label))],
        prerequisites=[Prerequisite("host:Filter 1 On", 1.0)],
        baseline_overrides=[],
        isolation_level=SINGLE_FIELD,
        claim_subject="modulation_source_id:%d" % source_id,
        claim_predicate="produces_periodic_modulation",
        measurement_plans=[
            MeasurementPlan(
                metric="modulation_frequency_hz",
                target=VF_TARGET,
                expected_direction="increase",  # any nonzero detected freq vs 0.0 baseline counts as "increase"
                threshold=0.05,
                stimulus=STIM_LONG_SUSTAIN,
                kernel_artifact="modulation_frequency_hz.py",
            ),
            MeasurementPlan(
                metric="modulation_depth",
                target=VF_TARGET,
                expected_direction="increase",
                threshold=0.02,
                stimulus=STIM_LONG_SUSTAIN,
                kernel_artifact="modulation_depth.py",
            ),
        ],
        notes="15.2.5 candidate scan: %s. control=empty ModSlot30, treatment=route with source=[%d,0]." % (label, source_id),
    )


if __name__ == "__main__":
    records = {}
    for exp_id, info in CANDIDATES.items():
        spec = build_spec(exp_id, info["source_id"], info["label"])
        rec = harness.run(spec)
        freq_m = rec.causal_measurements[0]
        depth_m = rec.causal_measurements[1]
        print("%-8s (%s)" % (exp_id, info["label"]))
        print("   gates=%s" % rec.gate_completeness())
        print("   freq : base=%.3f treat=%.3f delta=%+.3f status=%s" %
              (freq_m.baseline, freq_m.treatment, freq_m.delta, freq_m.status))
        print("   depth: base=%.5f treat=%.5f delta=%+.5f status=%s" %
              (depth_m.baseline, depth_m.treatment, depth_m.delta, depth_m.status))
        print("   persistence: %s %s" % (rec.persistence_observation["status"], rec.persistence_observation.get("detail")))
        records[exp_id] = rec

    out = r"D:/ableton claude/experiments/_lfo_source_records.pkl"
    pickle.dump(records, open(out, "wb"))
    print("\nsaved %d records -> %s" % (len(records), out))
