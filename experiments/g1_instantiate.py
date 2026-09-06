import dawdreamer as daw
import sys

VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SR = 44100
engine = daw.RenderEngine(SR, 512)

try:
    synth = engine.make_plugin_processor("serum", VST3)
    print("INSTANTIATE: OK")
except Exception as e:
    print("INSTANTIATE: FAILED ->", repr(e))
    sys.exit(1)

params = synth.get_parameters_description()
print("PARAM COUNT:", len(params))
for p in params[:15]:
    print(" ", p.get('index'), p.get('name'), p.get('default'), p.get('raw_value') if 'raw_value' in p else '')
