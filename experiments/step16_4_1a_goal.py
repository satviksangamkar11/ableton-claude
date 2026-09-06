"""16.4.1a: blind demand-pull producer goal. Oscillator + Env + Filter
(proven 3-capability base) + Macro.Value + the proven ModSlot->VoiceFilter
modulation route, composed against the BARE skeleton. Nothing here is chosen
to hit a known finding -- outcome is not predicted before running."""
import sys, pickle
sys.path.insert(0, r"D:\ableton claude")
from serum2.compiler import kernel
from serum2 import bridge

contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))
VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
skel_meta, skel_body = bridge.capture_v8_skeleton(VST3)

TARGETS = ["oscillator_field_OSC-VOLUME", "envelope_field_decay", "filter_field_reso",
          "macro_field_value", "modulation_route_voicefilter"]

dr = kernel.dry_run(TARGETS, contracts, required_causal_map={t: True for t in TARGETS}, base_body=skel_body)
print("accepted:", dr.accepted)
print("reason:", dr.reason)
print("detail:", dr.detail)
if dr.accepted:
    print("mutation_plan:", dr.mutation_plan)
    print("merged_prerequisites:", dr.merged_prerequisites)
else:
    print("admissions:")
    for a in dr.admissions:
        print(" ", a.admitted, a.reason, "|", a.detail[:150])
