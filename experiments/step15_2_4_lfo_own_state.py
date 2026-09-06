"""15.2.4: LFO own-state. Rate, Shape (pathData), Mode -- construct/mutate/
load/persist only. NO measurement_plans: causal effect requires routing to
something audible, which is 15.2.5's job, not this one. Honestly NOT_RUN,
not asserted either way."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence import harness
from serum2.evidence.spec import ExperimentSpec, Mutation, SINGLE_FIELD

REAL_PATHDATA = {
    'curveVals': [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5,
                 0.5023068342202408, 0.5, 0.5002888736710169],
    'isOpen': False, 'numPoints': 16,
    'xVals': [0.005292837356549088, 0.125, 0.125, 0.2974419037552329, 0.0,
             0.2915922510570054, 0.3004358845521003, 0.6040239045760147,
             0.9066926044974147, 0.2919664986566138, 0.6039913604399674, 1.0,
             0.7437891170099764, 0.8975072307143032, 0.5915191481253617, 0.0],
    'yVals': [1.0, 0.0, 0.0, 0.17814987837240137, 1.0, 0.1719950727001326,
             0.9047192890314022, 0.36424097416148893, 0.9715583280671334,
             0.18300893548208774, 0.35633689162479154, 0.0, 0.0,
             0.979937489425013, 0.0173414349292349, 0.0],
}

specs = {
    "LFO-RATE": ExperimentSpec(
        experiment_id="LFO-RATE",
        mutations=[Mutation("LFO0.plainParams.kParamRate", 12.5, "synthetic: high rate")],
        prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
        claim_subject="lfo_field:LFO.kParamRate", claim_predicate="constructs_mutates_persists",
        measurement_plans=[],
        notes="no causal claim -- LFO0 unrouted, no active mod destination. "
              "control: implicit default rate. treatment: 12.5 Hz.",
    ),
    "LFO-SHAPE": ExperimentSpec(
        experiment_id="LFO-SHAPE",
        mutations=[Mutation("LFO0.pathData", REAL_PATHDATA, "corpus: 'BA - Geiger Wub' real custom curve")],
        prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
        claim_subject="lfo_field:LFO.pathData", claim_predicate="constructs_mutates_persists",
        measurement_plans=[],
        notes="asset-identity capability, kept separate from numeric params, same "
              "principle as OSC-WAVETABLE. control: implicit default (empty {}).",
    ),
    "LFO-MODE": ExperimentSpec(
        experiment_id="LFO-MODE",
        mutations=[Mutation("LFO0.plainParams.kParamMode", "Envelope",
                            "corpus-confirmed real enum value (also 'Free' observed)")],
        prerequisites=[], baseline_overrides=[], isolation_level=SINGLE_FIELD,
        claim_subject="lfo_field:LFO.kParamMode", claim_predicate="constructs_mutates_persists",
        measurement_plans=[],
        notes="sync/trigger behavior. control: implicit default mode. treatment: 'Envelope'.",
    ),
}

records = {}
for eid, spec in specs.items():
    rec = harness.run(spec)
    print("%-10s gates=%s" % (eid, rec.gate_completeness()))
    print("   persistence detail:", rec.persistence_observation.get("detail"))
    records[eid] = rec

import pickle
pickle.dump(records, open(r"D:\ableton claude\experiments\_lfo_own_state_records.pkl", "wb"))
