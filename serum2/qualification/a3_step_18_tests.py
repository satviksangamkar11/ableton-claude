"""16.5.69.2-A3-18: Step 18 acceptance tests.

Test groups:
  1. Route dataclass contracts (pure unit, no VST3)
  2. ControlCapability registry contracts (pure unit, no VST3)
  3. Route resolution — verify empirical claims about CBOR/host mappings (VST3)
  4. Generic pipeline — no-semantic-branching proof (pure unit, mock arms)
  5. Architecture boundary — MODULATION_TOPOLOGY adapter produces SKIPPED (pure unit)

No H1 rerun. No broad 53-test regression.
"""

from __future__ import annotations

import copy
import pytest

from serum2.qualification.a3_route import MutationRoute, BehaviorRoute
from serum2.qualification.a3_capability import (
    ControlCapability,
    get_capability,
    ALL_CAPABILITIES,
    FILTER_RESONANCE, FILTER_TYPE, OSC1_ENABLE,
    OSC1_UNISON, ENV1_ATTACK, OSC1_WAVETABLE, MODULATION_SLOT,
)
from serum2.qualification.a3_generic_pipeline import (
    qualify_capability,
    _check_generation_gate,
    _build_arms,
    MutationReceipt,
)


# ===========================================================================
# Group 1: Route dataclass contracts
# ===========================================================================

class TestMutationRoute:
    def test_cbor_body_requires_path(self):
        with pytest.raises(ValueError, match="requires path"):
            MutationRoute(adapter="cbor_body")

    def test_host_param_requires_host_param(self):
        with pytest.raises(ValueError, match="requires host_param"):
            MutationRoute(adapter="host_param")

    def test_cbor_string_requires_path(self):
        with pytest.raises(ValueError, match="requires path"):
            MutationRoute(adapter="cbor_string")

    def test_unknown_adapter_rejected(self):
        with pytest.raises(ValueError, match="Unknown adapter"):
            MutationRoute(adapter="magic_write")

    def test_valid_cbor_body(self):
        r = MutationRoute(adapter="cbor_body", path="Env0.plainParams.kParamAttack")
        assert r.adapter == "cbor_body"
        assert r.path == "Env0.plainParams.kParamAttack"

    def test_valid_host_param(self):
        r = MutationRoute(adapter="host_param", host_param="A Unison")
        assert r.adapter == "host_param"
        assert r.host_param == "A Unison"

    def test_valid_not_supported(self):
        r = MutationRoute(adapter="NOT_SUPPORTED")
        assert r.adapter == "NOT_SUPPORTED"

    def test_frozen(self):
        r = MutationRoute(adapter="cbor_body", path="x")
        with pytest.raises(Exception):
            r.path = "y"  # type: ignore


class TestBehaviorRoute:
    def test_unknown_metric_rejected(self):
        with pytest.raises(ValueError, match="Unknown metric"):
            BehaviorRoute(metric="loudness_lufs")

    def test_not_observable(self):
        b = BehaviorRoute(metric="NOT_OBSERVABLE")
        assert not b.is_observable

    def test_observable(self):
        b = BehaviorRoute(metric="overall_rms_db")
        assert b.is_observable

    def test_exercise_context_tuple(self):
        b = BehaviorRoute(
            metric="overall_rms_db",
            exercise_context=(("Filter 1 On", 1.0),),
        )
        assert b.exercise_context == (("Filter 1 On", 1.0),)

    def test_frozen(self):
        b = BehaviorRoute(metric="overall_rms_db")
        with pytest.raises(Exception):
            b.metric = "spectral_centroid_hz"  # type: ignore


# ===========================================================================
# Group 2: ControlCapability registry contracts
# ===========================================================================

class TestCapabilityRegistry:
    def test_all_required_classes_represented(self):
        classes = {cap.mutation_class for cap in ALL_CAPABILITIES.values()}
        required = {"SCALAR", "ENUM", "BOOLEAN", "INTEGER", "REFERENCE",
                    "ARRAY_OBJECT", "MODULATION_TOPOLOGY"}
        # ARRAY_OBJECT not required to be present yet but all others must be
        required_present = {"SCALAR", "ENUM", "BOOLEAN", "INTEGER", "REFERENCE",
                            "MODULATION_TOPOLOGY"}
        assert required_present <= classes, (
            "Missing mutation classes: {}".format(required_present - classes)
        )

    def test_h1_capabilities_qualified(self):
        for sid in ("Filter.Resonance", "Filter.Type", "OSC1.Enable"):
            cap = get_capability(sid)
            assert cap.qualification_status == "QUALIFIED", \
                "{} should be QUALIFIED".format(sid)

    def test_step_18_capabilities_route_resolved(self):
        for sid in ("OSC1.Unison", "Env1.Attack", "OSC1.Wavetable"):
            cap = get_capability(sid)
            assert cap.qualification_status == "ROUTE_RESOLVED", \
                "{} should be ROUTE_RESOLVED".format(sid)

    def test_modulation_slot_architecture_only(self):
        cap = get_capability("Modulation.Slot0")
        assert cap.qualification_status == "ARCHITECTURE_ONLY"
        assert cap.mutation_route.adapter == "NOT_SUPPORTED"
        assert not cap.behavior_route.is_observable

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get_capability("Nonexistent.Target")

    def test_h1_cbor_body_adapters(self):
        # H1 targets use cbor_body adapter
        for sid in ("Filter.Resonance", "Filter.Type", "OSC1.Enable"):
            cap = get_capability(sid)
            assert cap.mutation_route.adapter == "cbor_body"

    def test_osc1_unison_host_param_adapter(self):
        cap = get_capability("OSC1.Unison")
        assert cap.mutation_route.adapter == "host_param"
        assert cap.mutation_route.host_param == "A Unison"
        assert cap.mutation_route.path is None  # no CBOR path

    def test_osc1_wavetable_cbor_string_adapter(self):
        cap = get_capability("OSC1.Wavetable")
        assert cap.mutation_route.adapter == "cbor_string"
        assert "relativePathToWT" in cap.mutation_route.path

    def test_osc1_enable_routes_differ(self):
        # OSC1.Enable: mutation_route is cbor_body, behavior uses arm-specific host contexts
        cap = get_capability("OSC1.Enable")
        assert cap.mutation_route.adapter == "cbor_body"
        # behavior route has arm-specific host contexts (the disconnect is explicit)
        assert len(cap.behavior_route.baseline_host_context) > 0
        assert len(cap.behavior_route.mutated_host_context) > 0

    def test_filter_resonance_routes_same_path(self):
        # Filter: mutation_route.path maps directly to behavior (no disconnect)
        cap = get_capability("Filter.Resonance")
        assert cap.mutation_route.adapter == "cbor_body"
        # behavior route has exercise context but no arm-specific host contexts
        assert len(cap.behavior_route.baseline_host_context) == 0
        assert len(cap.behavior_route.mutated_host_context) == 0
        assert len(cap.behavior_route.exercise_context) > 0


# ===========================================================================
# Group 3: Route resolution — VST3 empirical proofs
# ===========================================================================

def _load_serum(body):
    """Load Serum from body dict. Returns (engine, synth, by_name). Caller keeps engine alive."""
    import dawdreamer as daw, tempfile, os
    from serum2 import bridge
    from serum2.evidence import epoch as epoch_mod

    meta = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)[0]
    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor("serum", epoch_mod.SERUM_VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    by_name = {p["name"]: p["index"] for p in synth.get_parameters_description()}
    return engine, synth, by_name


@pytest.mark.vst3
class TestRouteResolution:
    """Empirically verifies the route mappings claimed in a3_capability.py."""

    def test_env0_attack_cbor_maps_to_env1_host(self):
        from serum2 import bridge, pathmerge
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        _, body = skeleton

        engine1, synth1, by_name = _load_serum(body)
        default_env1 = synth1.get_parameter(by_name["Env 1 Attack"])

        body2 = copy.deepcopy(body)
        pathmerge.apply_path_value(body2, "Env0.plainParams.kParamAttack", 100.0)
        engine2, synth2, _ = _load_serum(body2)
        new_env1 = synth2.get_parameter(by_name["Env 1 Attack"])

        assert new_env1 != default_env1, "Env0 CBOR write should affect Env 1 Attack host param"
        assert new_env1 > default_env1, "Large kParamAttack should increase host param"

    def test_env1_attack_cbor_maps_to_env2_host(self):
        from serum2 import bridge, pathmerge
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        _, body = skeleton

        engine1, synth1, by_name = _load_serum(body)
        default_env1 = synth1.get_parameter(by_name["Env 1 Attack"])
        default_env2 = synth1.get_parameter(by_name["Env 2 Attack"])

        body2 = copy.deepcopy(body)
        pathmerge.apply_path_value(body2, "Env1.plainParams.kParamAttack", 100.0)
        engine2, synth2, _ = _load_serum(body2)
        new_env1 = synth2.get_parameter(by_name["Env 1 Attack"])
        new_env2 = synth2.get_parameter(by_name["Env 2 Attack"])

        assert abs(new_env1 - default_env1) < 0.001, \
            "Env1 CBOR write should NOT affect Env 1 Attack host"
        assert new_env2 > default_env2, \
            "Env1 CBOR write should increase Env 2 Attack host"

    def test_a_unison_has_no_cbor_path(self):
        """Confirm: no CBOR body diff after set_parameter('A Unison') + save_state."""
        import tempfile, os
        from serum2 import bridge, codec, vst3_state
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        _, body = skeleton

        engine, synth, by_name = _load_serum(body)
        synth.set_parameter(by_name["A Unison"], 0.8)

        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        synth.save_state(tmp)
        raw = open(tmp, "rb").read()
        os.remove(tmp)
        _, saved_body = codec.decode(vst3_state.unwrap_vc2(raw))

        def leaf_diff(orig, saved, path=""):
            diffs = []
            if isinstance(orig, dict) and isinstance(saved, dict):
                for k in set(list(orig.keys()) + list(saved.keys())):
                    p = path + "." + k if path else k
                    if k not in orig:
                        diffs.append(("ADDED", p))
                    elif k not in saved:
                        diffs.append(("REMOVED", p))
                    else:
                        diffs.extend(leaf_diff(orig[k], saved[k], p))
            elif orig != saved:
                diffs.append(("CHANGED", path, orig, saved))
            return diffs

        diffs = leaf_diff(body, saved_body)
        assert not diffs, "A Unison host-param change should produce no CBOR body diffs: {}".format(diffs)

    def test_wavetable_path_persists(self):
        """Confirm: relativePathToWT change survives save_state round-trip."""
        import tempfile, os
        from serum2 import bridge, codec, vst3_state
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        _, body = skeleton

        new_path = "S2 Tables/Analog/808 Harms.wav"
        body2 = copy.deepcopy(body)
        body2["Oscillator0"]["WTOsc0"]["relativePathToWT"] = new_path

        engine, synth, _ = _load_serum(body2)
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        synth.save_state(tmp)
        raw = open(tmp, "rb").read()
        os.remove(tmp)
        _, saved_body = codec.decode(vst3_state.unwrap_vc2(raw))

        saved_path = saved_body["Oscillator0"]["WTOsc0"]["relativePathToWT"]
        assert saved_path == new_path, \
            "relativePathToWT should persist through save_state: got {!r}".format(saved_path)


# ===========================================================================
# Group 4: Generic pipeline — no semantic-ID-specific branching
# ===========================================================================

class TestGenericPipeline:
    """Test that the pipeline dispatches purely on capability fields.

    Uses pure-unit stubs where possible to avoid VST3 I/O.
    The generation gate is pure Python; behavior gate uses stubs.
    """

    @pytest.fixture
    def fake_skeleton(self):
        # Minimal skeleton for pipeline arm building (body only; no VST3 needed for gen gate)
        meta = {}
        body = {
            "VoiceFilter0": {"plainParams": {"kParamResonance": 0.5}},
            "Oscillator0": {"WTOsc0": {"relativePathToWT": "S2 Tables/Default Shapes.wav",
                                        "numFrames": "18432", "numChannels": "1",
                                        "sampleRate": "44100", "flex": "{}"}},
            "Env1": {"plainParams": {"kParamCurve1": 50.0}},
        }
        return (meta, body)

    def test_generation_gate_cbor_body_pass(self, fake_skeleton):
        cap = FILTER_RESONANCE
        body_base, body_mut, _, _ = _build_arms(
            cap, fake_skeleton, baseline_value=0.1, mutated_value=0.9
        )
        result = _check_generation_gate(body_base, body_mut, cap.mutation_route)
        assert result["status"] == "PASS"
        assert result["top_ok"] is True
        assert result["leaf_changed"] is True

    def test_generation_gate_cbor_string_pass(self, fake_skeleton):
        cap = OSC1_WAVETABLE
        body_base, body_mut, _, _ = _build_arms(
            cap, fake_skeleton,
            baseline_value="S2 Tables/Default Shapes.wav",
            mutated_value="S2 Tables/Analog/808 Harms.wav",
        )
        result = _check_generation_gate(body_base, body_mut, cap.mutation_route)
        assert result["status"] == "PASS"

    def test_generation_gate_host_param_not_run(self, fake_skeleton):
        cap = OSC1_UNISON
        body_base, body_mut, _, _ = _build_arms(
            cap, fake_skeleton, baseline_value=0.0, mutated_value=0.9
        )
        result = _check_generation_gate(body_base, body_mut, cap.mutation_route)
        assert result["status"] == "NOT_RUN"

    def test_pipeline_not_supported_returns_skipped(self, fake_skeleton):
        receipt = qualify_capability(
            capability=MODULATION_SLOT,
            skeleton=fake_skeleton,
            baseline_value=None,
            mutated_value=None,
            experiment_id="test_modulation_skipped",
            run_behavior=False,
        )
        assert receipt.generation_status == "SKIPPED"
        assert receipt.behavior_status == "SKIPPED"
        assert receipt.adapter == "NOT_SUPPORTED"

    def test_pipeline_run_behavior_false_skips_audio(self, fake_skeleton):
        """Pipeline with run_behavior=False should not touch VST3 audio."""
        receipt = qualify_capability(
            capability=FILTER_RESONANCE,
            skeleton=fake_skeleton,
            baseline_value=0.1,
            mutated_value=0.9,
            experiment_id="test_no_audio",
            run_behavior=False,
        )
        assert receipt.generation_status == "PASS"
        assert receipt.behavior_status == "NOT_RUN"

    def test_pipeline_host_param_generation_not_run(self, fake_skeleton):
        receipt = qualify_capability(
            capability=OSC1_UNISON,
            skeleton=fake_skeleton,
            baseline_value=0.0,
            mutated_value=0.9,
            experiment_id="test_unison_gen",
            run_behavior=False,
        )
        assert receipt.generation_status == "NOT_RUN"
        assert receipt.adapter == "host_param"

    def test_build_arms_cbor_body_mutates_only_mutated(self, fake_skeleton):
        cap = FILTER_RESONANCE
        body_base, body_mut, bh_ctx, mh_ctx = _build_arms(
            cap, fake_skeleton, baseline_value=None, mutated_value=0.9
        )
        from serum2 import pathmerge
        mut_val = pathmerge.read_path_value(body_mut, cap.mutation_route.path)
        assert mut_val == 0.9
        # baseline should not have the mutated value
        base_val = pathmerge.read_path_value(body_base, cap.mutation_route.path)
        assert base_val != 0.9

    def test_build_arms_host_param_no_body_diff(self, fake_skeleton):
        cap = OSC1_UNISON
        body_base, body_mut, bh_ctx, mh_ctx = _build_arms(
            cap, fake_skeleton, baseline_value=0.0, mutated_value=0.9
        )
        # Bodies should be identical — mutation is in host contexts
        assert body_base == body_mut
        # Host contexts should carry the mutation
        assert ("A Unison", 0.0) in bh_ctx
        assert ("A Unison", 0.9) in mh_ctx

    def test_pipeline_dispatches_without_semantic_id_check(self, fake_skeleton):
        """The pipeline must not branch on semantic_id — prove by running
        three capabilities with different adapters and seeing each dispatches correctly."""
        results = {}
        for cap in (FILTER_RESONANCE, OSC1_UNISON, OSC1_WAVETABLE):
            receipt = qualify_capability(
                capability=cap,
                skeleton=fake_skeleton,
                baseline_value=0.0,
                mutated_value=0.9,
                experiment_id="dispatch_test_{}".format(cap.semantic_id),
                run_behavior=False,
            )
            results[cap.semantic_id] = receipt

        # Different generation statuses reflect different adapters, not semantic IDs
        assert results["Filter.Resonance"].generation_status == "PASS"
        assert results["OSC1.Unison"].generation_status == "NOT_RUN"
        # OSC1.Wavetable: 0.9 is not a valid path but generation gate should show it changed
        assert results["OSC1.Wavetable"].generation_status in ("PASS", "FAIL")


# ===========================================================================
# Group 5: Architecture boundary
# ===========================================================================

class TestArchitectureBoundary:
    def test_modulation_topology_is_not_runnable(self):
        cap = get_capability("Modulation.Slot0")
        assert not cap.can_run_behavior
        assert not cap.behavior_route.is_observable

    def test_modulation_topology_is_not_qualified(self):
        cap = get_capability("Modulation.Slot0")
        assert not cap.is_qualified

    def test_route_resolved_caps_can_run_behavior(self):
        for sid in ("OSC1.Unison", "Env1.Attack", "OSC1.Wavetable"):
            cap = get_capability(sid)
            assert cap.can_run_behavior, \
                "{} should be able to run behavior".format(sid)

    def test_qualified_caps_are_qualified(self):
        for sid in ("Filter.Resonance", "Filter.Type", "OSC1.Enable"):
            cap = get_capability(sid)
            assert cap.is_qualified

    def test_mutation_receipt_dataclass(self):
        from serum2.qualification.a3_behavior_observation import BEHAVIOR_NOT_RUN
        r = MutationReceipt(
            semantic_id="Test.Cap",
            mutation_class="SCALAR",
            adapter="cbor_body",
            generation_status="PASS",
            behavior_status="CAUSAL_VERIFIED",
            behavior_observation=BEHAVIOR_NOT_RUN,
        )
        assert r.is_causal
        r2 = MutationReceipt(
            semantic_id="Test.Cap2",
            mutation_class="INTEGER",
            adapter="host_param",
            generation_status="NOT_RUN",
            behavior_status="NO_OBSERVED_EFFECT",
        )
        assert not r2.is_causal
