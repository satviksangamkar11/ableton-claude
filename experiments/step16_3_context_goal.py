"""16.3.6: re-run the compiler goal with RequiredContext admission wired in.
Two cases: bare skeleton (must refuse pre-Serum), and a caller-supplied
context body containing FXDistortion (must accept and construct)."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler import kernel
from serum2 import bridge, codec

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
skel_meta, skel_body = bridge.capture_v8_skeleton(VST3)

TARGETS_3 = ["oscillator_field_OSC-VOLUME", "envelope_field_decay", "filter_field_reso"]
TARGETS_4 = TARGETS_3 + ["fx_field_distortion_drive"]

print("=== Case A: 3-capability goal against bare skeleton -> ACCEPT/construct/verify ===")
dr = kernel.dry_run(TARGETS_3, contracts, required_causal_map={t: True for t in TARGETS_3}, base_body=skel_body)
print("accepted:", dr.accepted, "reason:", dr.reason)
if dr.accepted:
    rec = kernel.construct_and_verify(dr, experiment_id="CTX-GOAL-3")
    print("overall_pass:", kernel.evaluate_construction_goal(rec)["overall_pass"])

print()
print("=== Case B: 4-capability goal against bare skeleton -> REFUSE, pre-Serum, CONTEXT_NOT_SATISFIED ===")
dr4_bare = kernel.dry_run(TARGETS_4, contracts, required_causal_map={t: True for t in TARGETS_4}, base_body=skel_body)
print("accepted:", dr4_bare.accepted)
print("reason:", dr4_bare.reason)
print("detail:", dr4_bare.detail)
assert dr4_bare.reason == kernel.REFUSED_CONTEXT_NOT_SATISFIED
assert dr4_bare.accepted is False

print()
print("=== Case C: 4-capability goal against a caller-supplied context body (real FXDistortion present) ===")
AARD = r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\Factory\Arp\ARP - Aardvark.SerumPreset"
_, aard_body = codec.load_preset_file(AARD)
context_body = dict(skel_body)
context_body["FXRack0"] = aard_body["FXRack0"]

dr4_ctx = kernel.dry_run(TARGETS_4, contracts, required_causal_map={t: True for t in TARGETS_4}, base_body=context_body)
print("accepted:", dr4_ctx.accepted, "reason:", dr4_ctx.reason)
print("mutation_plan:", dr4_ctx.mutation_plan)
if dr4_ctx.accepted:
    rec = kernel.construct_and_verify(dr4_ctx, experiment_id="CTX-GOAL-4",
                                      skeleton=(skel_meta, context_body))
    result = kernel.evaluate_construction_goal(rec)
    print("gate_completeness:", rec.gate_completeness())
    print("persistence:", rec.persistence_observation)
    print("state_observation matches_intent:", rec.state_observation.get("matches_intent"))
    print("causal_measurements:", [(m.metric, m.status, m.delta) for m in rec.causal_measurements])
    print("overall_pass:", result["overall_pass"])
    pickle.dump(rec, open(r"D:/ableton claude/experiments/_compiler_goal4_ctx_record.pkl", "wb"))
