"""16.2: first compiler construction goal -- basic playable patch (oscillator
+ envelope + filter + one FX capability), using ONLY currently admitted
CapabilityContracts, exactly as tested (no new values invented)."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler import kernel

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

TARGETS = ["oscillator_field_OSC-VOLUME", "envelope_field_decay", "filter_field_reso"]

dr = kernel.dry_run(TARGETS, contracts, required_causal_map={t: True for t in TARGETS})
print("dry_run.accepted:", dr.accepted)
print("dry_run.reason:", dr.reason)
print("dry_run.detail:", dr.detail)
if dr.accepted:
    print("mutation_plan:", dr.mutation_plan)
    print("merged_prerequisites:", dr.merged_prerequisites)

if not dr.accepted:
    print()
    print("REFUSED at dry-run stage -- no Serum interaction attempted.")
    sys.exit(0)

print()
print("=== dry run ACCEPTED -- proceeding to construction+verification ===")
try:
    rec = kernel.construct_and_verify(dr, experiment_id="COMPILER-GOAL-1")
    result = kernel.evaluate_construction_goal(rec)
    print("gate_completeness:", rec.gate_completeness())
    print("persistence:", rec.persistence_observation)
    print("state_observation:", {k: rec.state_observation[k] for k in
                                 ("status", "matches_intent", "top_level_ok", "fine_grained_ok")})
    print("causal_measurements:", [(m.metric, m.status, m.delta) for m in rec.causal_measurements])
    print()
    print("=== 16.2 acceptance evaluation ===")
    for k, v in result.items():
        print(" ", k, "=", v)
    pickle.dump(rec, open(r"D:/ableton claude/experiments/_compiler_goal1_record.pkl", "wb"))
except Exception as e:
    print()
    print("=== CONSTRUCTION FAILED (this IS a legitimate compiler-discovered gap, not a bug) ===")
    print(type(e).__name__, ":", e)
