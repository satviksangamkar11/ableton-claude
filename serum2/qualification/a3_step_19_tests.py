"""16.5.69.2-A3-19: Step 19 acceptance tests.

Test groups:
  1. GenerationObservation dataclass contracts (pure unit)
  2. ParameterEntry inventory classification (pure unit)
  3. Bulk pipeline assembly (pure unit)
  4. VST3 integration: generation check on real Serum (VST3)
  5. Coverage matrix: completeness and consistency checks
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass

from serum2.qualification.a3_generation_observation import (
    GenerationObservation,
    GENERATION_NOT_APPLICABLE,
    GENERATION_NOT_RUN,
    generation_from_host_param_readback,
    generation_from_state_diff,
)
from serum2.qualification.a3_parameter_inventory import (
    ParameterEntry,
    build_inventory,
    summarize_inventory,
    _KNOWN_ROUTES,
)
from serum2.qualification.a3_bulk_pipeline import (
    ParameterQualification,
    coverage_summary,
    p1_for_entry,
    assemble_qualifications,
)
from serum2.qualification.a3_route import MutationRoute


# ===========================================================================
# Group 1: GenerationObservation contracts
# ===========================================================================

class TestGenerationObservation:
    def test_unknown_route_kind_rejected(self):
        with pytest.raises(ValueError, match="Unknown route_kind"):
            GenerationObservation(route_kind="magic", status="PASS")

    def test_unknown_status_rejected(self):
        with pytest.raises(ValueError, match="Unknown status"):
            GenerationObservation(route_kind="host_param_mutation", status="MAYBE")

    def test_not_applicable_sentinel(self):
        assert GENERATION_NOT_APPLICABLE.status == "NOT_APPLICABLE"
        assert not GENERATION_NOT_APPLICABLE.passed

    def test_not_run_sentinel(self):
        assert GENERATION_NOT_RUN.status == "NOT_RUN"
        assert not GENERATION_NOT_RUN.passed

    def test_host_param_pass(self):
        obs = generation_from_host_param_readback(
            vst3_name="A Unison",
            value_before=0.0,
            value_set=0.9,
            value_after=0.9,
        )
        assert obs.status == "PASS"
        assert obs.passed
        assert obs.route_kind == "host_param_mutation"
        assert obs.value_before == 0.0
        assert obs.value_after == 0.9

    def test_host_param_fail_when_unchanged(self):
        obs = generation_from_host_param_readback(
            vst3_name="Broken Param",
            value_before=0.5,
            value_set=0.9,
            value_after=0.5,  # readback == before
        )
        assert obs.status == "FAIL"
        assert not obs.passed

    def test_state_mutation_pass(self):
        obs = generation_from_state_diff(
            diff_keys=["VoiceFilter0"],
            intended_top_key="VoiceFilter0",
            leaf_changed=True,
            top_ok=True,
        )
        assert obs.status == "PASS"
        assert obs.route_kind == "state_mutation"
        assert obs.diff_keys == ("VoiceFilter0",)

    def test_state_mutation_fail_wrong_keys(self):
        obs = generation_from_state_diff(
            diff_keys=["VoiceFilter0", "Env0"],
            intended_top_key="VoiceFilter0",
            leaf_changed=True,
            top_ok=False,
        )
        assert obs.status == "FAIL"

    def test_state_mutation_fail_leaf_unchanged(self):
        obs = generation_from_state_diff(
            diff_keys=["VoiceFilter0"],
            intended_top_key="VoiceFilter0",
            leaf_changed=False,
            top_ok=True,
        )
        assert obs.status == "FAIL"


# ===========================================================================
# Group 2: Parameter inventory classification
# ===========================================================================

def _make_raw_param(index, name, numSteps=2147483647, isDiscrete=False, isAutomatable=True, defaultValue=0.5):
    return {
        "index": index, "name": name, "numSteps": numSteps,
        "isDiscrete": isDiscrete, "isAutomatable": isAutomatable,
        "defaultValue": defaultValue, "isBoolean": False,
        "category": "genericParameter",
    }


class TestParameterInventory:
    def test_total_count_preserved(self):
        raw = [_make_raw_param(i, "Param {}".format(i)) for i in range(10)]
        entries = build_inventory(raw)
        assert len(entries) == 10

    def test_boolean_classification(self):
        raw = [_make_raw_param(0, "Mono Toggle", numSteps=2, isDiscrete=True)]
        entries = build_inventory(raw)
        assert entries[0].mutation_class == "BOOLEAN"

    def test_integer_classification(self):
        raw = [_make_raw_param(0, "A Octave", numSteps=9, isDiscrete=True)]
        entries = build_inventory(raw)
        assert entries[0].mutation_class == "INTEGER"

    def test_scalar_classification(self):
        raw = [_make_raw_param(0, "Filter 1 Freq", numSteps=2147483647)]
        entries = build_inventory(raw)
        assert entries[0].mutation_class == "SCALAR"

    def test_midi_passthrough_classification(self):
        raw = [_make_raw_param(541, "CC0 Chan 1", isAutomatable=False)]
        entries = build_inventory(raw)
        assert entries[0].mutation_class == "MIDI_PASSTHROUGH"
        assert entries[0].controllability == "MIDI_PASSTHROUGH"

    def test_known_routes_get_semantic_id(self):
        known_name = "A Unison"
        raw = [_make_raw_param(44, known_name, numSteps=16, isDiscrete=True)]
        entries = build_inventory(raw)
        assert entries[0].semantic_id == "OSC1.Unison"
        assert entries[0].mutation_route.adapter == "host_param"

    def test_unknown_params_get_unmapped(self):
        raw = [_make_raw_param(99, "Some Unknown Param")]
        entries = build_inventory(raw)
        assert entries[0].semantic_id == "UNMAPPED"

    def test_filter_res_gets_cbor_route(self):
        raw = [_make_raw_param(0, "Filter 1 Res")]
        entries = build_inventory(raw)
        assert entries[0].mutation_route.adapter == "cbor_body"
        assert entries[0].controllability == "CBOR_AND_HOST"

    def test_host_param_only_gets_host_route(self):
        raw = [_make_raw_param(0, "Some Continuous Param")]
        entries = build_inventory(raw)
        assert entries[0].mutation_route.adapter == "host_param"
        assert entries[0].controllability == "HOST_PARAM_ONLY"

    def test_summary_totals(self):
        raw = (
            [_make_raw_param(i, "Auto {}".format(i)) for i in range(5)]
            + [_make_raw_param(100 + i, "CC{}".format(i), isAutomatable=False) for i in range(3)]
        )
        entries = build_inventory(raw)
        summary = summarize_inventory(entries)
        assert summary["automatable_synthesis"] == 5
        assert summary["midi_passthrough"] == 3

    def test_known_routes_coverage(self):
        # All keys in _KNOWN_ROUTES must correspond to real semantic IDs
        for vst3_name, (semantic_id, route) in _KNOWN_ROUTES.items():
            assert len(semantic_id) > 0
            assert semantic_id != "UNMAPPED"
            assert route.adapter in ("cbor_body", "cbor_string", "host_param")


# ===========================================================================
# Group 3: Bulk pipeline assembly
# ===========================================================================

def _make_entry(idx, name, is_auto=True, adapter="host_param"):
    route = MutationRoute(adapter=adapter, host_param=name) if adapter == "host_param" \
        else MutationRoute(adapter="NOT_SUPPORTED")
    mut_class = "MIDI_PASSTHROUGH" if not is_auto else "SCALAR"
    ctrl = "HOST_PARAM_ONLY" if is_auto else "MIDI_PASSTHROUGH"
    return ParameterEntry(
        vst3_index=idx, vst3_name=name,
        num_steps=2147483647, is_discrete=False,
        is_automatable=is_auto, default_value=0.5,
        mutation_class=mut_class, mutation_route=route,
        semantic_id="UNMAPPED", controllability=ctrl,
    )


class TestBulkPipeline:
    def test_p1_host_param_not_applicable(self):
        entry = _make_entry(0, "A Vol")
        p1_status, p1_reason = p1_for_entry(entry)
        assert p1_status == "NOT_APPLICABLE"
        assert "host_param" in p1_reason

    def test_p1_midi_passthrough_not_applicable(self):
        entry = _make_entry(541, "CC0 Chan 1", is_auto=False, adapter="NOT_SUPPORTED")
        p1_status, p1_reason = p1_for_entry(entry)
        assert p1_status == "NOT_APPLICABLE"

    def test_assemble_carries_behavior_status(self):
        entry = _make_entry(0, "A Enable")
        entry.semantic_id = "OSC1.Enable"
        obs_map = {0: generation_from_host_param_readback(
            vst3_name="A Enable", value_before=1.0, value_set=0.0, value_after=0.0
        )}
        behavior_map = {"OSC1.Enable": ("CAUSAL_VERIFIED", "Step 17")}
        quals = assemble_qualifications([entry], obs_map, behavior_status_map=behavior_map)
        assert quals[0].behavior_status == "CAUSAL_VERIFIED"

    def test_assemble_unmapped_gets_not_run_behavior(self):
        entry = _make_entry(99, "Random Param")
        obs_map = {99: GENERATION_NOT_APPLICABLE}
        quals = assemble_qualifications([entry], obs_map)
        assert quals[0].behavior_status == "NOT_RUN"

    def test_coverage_summary_structure(self):
        entries = [_make_entry(i, "P{}".format(i)) for i in range(5)]
        obs_map = {
            i: generation_from_host_param_readback(
                vst3_name="P{}".format(i), value_before=0.5, value_set=0.75, value_after=0.75
            )
            for i in range(5)
        }
        quals = assemble_qualifications(entries, obs_map)
        matrix = coverage_summary(quals)
        assert "total_vst3_parameters" in matrix
        assert "generation_pass" in matrix
        assert "qualified_causal" in matrix
        assert "semantically_identified" in matrix
        assert matrix["total_vst3_parameters"] == 2623

    def test_parameter_qualification_to_dict(self):
        entry = _make_entry(0, "Filter 1 Freq")
        obs = generation_from_host_param_readback(
            vst3_name="Filter 1 Freq", value_before=0.5, value_set=0.75, value_after=0.75
        )
        qual = ParameterQualification(
            vst3_index=0, vst3_name="Filter 1 Freq",
            semantic_id="UNMAPPED", mutation_class="SCALAR",
            controllability="HOST_PARAM_ONLY", generation=obs,
        )
        d = qual.to_dict()
        assert d["vst3_index"] == 0
        assert d["generation"]["status"] == "PASS"
        assert d["p1_status"] == "NOT_RUN"

    def test_is_controllable_pass(self):
        entry = _make_entry(0, "A Vol")
        obs = generation_from_host_param_readback(
            vst3_name="A Vol", value_before=0.5, value_set=0.75, value_after=0.75
        )
        qual = ParameterQualification(
            vst3_index=0, vst3_name="A Vol",
            semantic_id="UNMAPPED", mutation_class="SCALAR",
            controllability="HOST_PARAM_ONLY", generation=obs,
        )
        assert qual.is_controllable

    def test_is_controllable_not_applicable(self):
        qual = ParameterQualification(
            vst3_index=541, vst3_name="CC0 Chan 1",
            semantic_id="UNMAPPED", mutation_class="MIDI_PASSTHROUGH",
            controllability="MIDI_PASSTHROUGH", generation=GENERATION_NOT_APPLICABLE,
        )
        assert qual.is_controllable  # NOT_APPLICABLE is not a failure


# ===========================================================================
# Group 4: VST3 integration
# ===========================================================================

@pytest.mark.vst3
class TestVST3BulkGeneration:
    def test_bulk_generation_all_automatable_pass(self):
        """All 541 automatable params should pass in-process generation check."""
        import dawdreamer as daw, tempfile, os
        from serum2 import bridge
        from serum2.evidence import epoch as epoch_mod
        from serum2.qualification.a3_bulk_pipeline import run_bulk_host_param_generation

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body = skeleton

        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        bridge.write_state_file(tmp, meta, body)
        engine = daw.RenderEngine(44100, 512)
        synth = engine.make_plugin_processor("serum", epoch_mod.SERUM_VST3)
        synth.load_state(tmp)
        os.remove(tmp)
        raw_params = synth.get_parameters_description()

        from serum2.qualification.a3_parameter_inventory import build_inventory
        entries = build_inventory(raw_params)

        observations = run_bulk_host_param_generation(entries, epoch_mod.SERUM_VST3, skeleton)

        auto_entries = [e for e in entries if e.is_automatable]
        gen_pass = sum(1 for e in auto_entries if observations[e.vst3_index].status == "PASS")
        gen_fail = [e for e in auto_entries if observations[e.vst3_index].status == "FAIL"]

        assert gen_pass == len(auto_entries), \
            "Expected all {} automatable params to pass generation; failed: {}".format(
                len(auto_entries),
                [(e.vst3_index, e.vst3_name, observations[e.vst3_index].reason) for e in gen_fail[:5]]
            )

    def test_cbor_body_generation_known_routes(self):
        """Known cbor_body routes should pass state_mutation generation check."""
        from serum2 import bridge
        from serum2.evidence import epoch as epoch_mod
        from serum2.qualification.a3_bulk_pipeline import run_cbor_body_generation
        from serum2.qualification.a3_parameter_inventory import build_inventory
        import dawdreamer as daw, tempfile, os

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body = skeleton
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        bridge.write_state_file(tmp, meta, body)
        engine = daw.RenderEngine(44100, 512)
        synth = engine.make_plugin_processor("serum", epoch_mod.SERUM_VST3)
        synth.load_state(tmp)
        os.remove(tmp)
        raw_params = synth.get_parameters_description()

        entries = build_inventory(raw_params)
        cbor_entries = [e for e in entries if e.mutation_route.adapter == "cbor_body"]

        assert len(cbor_entries) > 0, "Expected at least some cbor_body entries"
        for e in cbor_entries:
            obs = run_cbor_body_generation(e, skeleton)
            assert obs.status == "PASS", \
                "cbor_body generation failed for {} ({}): {}".format(
                    e.vst3_name, e.mutation_route.path, obs.reason
                )

    def test_full_inventory_count(self):
        """Inventory must have exactly 2,623 entries."""
        import dawdreamer as daw, tempfile, os
        from serum2 import bridge
        from serum2.evidence import epoch as epoch_mod
        from serum2.qualification.a3_parameter_inventory import build_inventory

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body = skeleton
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        bridge.write_state_file(tmp, meta, body)
        engine = daw.RenderEngine(44100, 512)
        synth = engine.make_plugin_processor("serum", epoch_mod.SERUM_VST3)
        synth.load_state(tmp)
        os.remove(tmp)
        raw_params = synth.get_parameters_description()

        entries = build_inventory(raw_params)
        assert len(entries) == 2623, "Expected 2623 entries, got {}".format(len(entries))

    def test_automatable_count(self):
        """541 automatable parameters expected."""
        import dawdreamer as daw, tempfile, os
        from serum2 import bridge
        from serum2.evidence import epoch as epoch_mod
        from serum2.qualification.a3_parameter_inventory import build_inventory

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body = skeleton
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        bridge.write_state_file(tmp, meta, body)
        engine = daw.RenderEngine(44100, 512)
        synth = engine.make_plugin_processor("serum", epoch_mod.SERUM_VST3)
        synth.load_state(tmp)
        os.remove(tmp)
        raw_params = synth.get_parameters_description()

        entries = build_inventory(raw_params)
        auto_count = sum(1 for e in entries if e.is_automatable)
        assert auto_count == 541


# ===========================================================================
# Group 5: Coverage matrix integration
# ===========================================================================

@pytest.mark.vst3
class TestCoverageMatrix:
    def test_full_coverage_run(self):
        """End-to-end: run_step_19 produces a valid coverage matrix."""
        from serum2.qualification.a3_step_19_coverage import run_step_19
        matrix = run_step_19()

        # Basic shape checks
        assert matrix["total_vst3_parameters"] == 2623
        assert matrix["inventoried"] == 2623
        assert matrix["automatable_synthesis"] == 541
        assert matrix["midi_passthrough_non_synthesis"] == 2082

        # Generation: all 541 should pass
        assert matrix["generation_pass"] == 541, \
            "Expected 541 generation PASS, got {}".format(matrix["generation_pass"])
        assert matrix["generation_fail"] == 0

        # H1 targets are qualified
        assert matrix["qualified_causal"] == 3  # Filter.Resonance, Filter.Type, OSC1.Enable

        # Semantically identified = H1 (3) + Step 18 (3 route-resolved with semantic IDs)
        # = OSC1.Unison, Env1.Attack, OSC1.Wavetable + Filter.Resonance, Filter.Type, OSC1.Enable
        # But we also have Env 2 Attack -> Env1.Attack, Filter 1 Res -> Filter.Resonance, etc.
        # Count from _KNOWN_ROUTES
        from serum2.qualification.a3_parameter_inventory import _KNOWN_ROUTES
        expected_semantic = len(_KNOWN_ROUTES)
        assert matrix["semantically_identified"] == expected_semantic, \
            "Expected {} semantically identified, got {}".format(
                expected_semantic, matrix["semantically_identified"])

        # Coverage gap is explicit and correct
        assert matrix["unmapped_semantic"] == 2623 - expected_semantic
