"""16.5.69.2-A3-20: Modulation topology tests.

Test groups:
  TestModulationRoute      (9 tests) — source/destination table, amount conversion
  TestModulationAdapter    (9 tests) — write/read/remove slot, slot selection
  TestVST3Modulation       (4 tests) — persistence + audio causality via VST3

Execution constraints:
  - NO rerun of completed tests (Steps 13-19 suites untouched)
  - Only new tests + directly affected regressions
  - VST3 tests load Serum once per test (not class-scoped to avoid GC issues)
"""

from __future__ import annotations

import copy
import os
import tempfile

import numpy as np
import pytest

from serum2.qualification.a3_modulation_route import (
    ModulationSource,
    ModulationDestination,
    get_source,
    get_destination,
    list_sources,
    list_destinations,
    normalize_to_cbor_amount,
    cbor_amount_to_normalized,
)
from serum2.qualification.a3_modulation_adapter import (
    ModulationSlotEntry,
    find_empty_slot,
    read_slot,
    read_all_slots,
    write_modulation,
    remove_modulation,
    MAX_MODULATION_SLOTS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_body_with_slot(slot_index: int, slot_dict: dict) -> dict:
    body = {"ModSlot{}".format(i): "default" for i in range(MAX_MODULATION_SLOTS)}
    body["ModSlot{}".format(slot_index)] = slot_dict
    return body


def _lfo1_filter_slot(amount_cbor: float = 37.0) -> dict:
    return {
        "destModuleID": 0,
        "destModuleParamID": 3,
        "destModuleParamName": "kParamFreq",
        "destModuleTypeString": "VoiceFilter",
        "plainParams": {"kParamAmount": amount_cbor},
        "source": [6, 0],
    }


# ---------------------------------------------------------------------------
# TestModulationRoute
# ---------------------------------------------------------------------------

class TestModulationRoute:
    def test_get_known_lfo1_source(self):
        src = get_source("LFO1")
        assert src.source_type_id == 6
        assert src.source_bus_id == 0
        assert src.cbor_module_key == "LFO0"

    def test_get_lfo_range_confirmed(self):
        for i, (name, type_id) in enumerate([
            ("LFO1", 6), ("LFO2", 7), ("LFO3", 8), ("LFO4", 9), ("LFO5", 10),
        ]):
            src = get_source(name)
            assert src.source_type_id == type_id, "{}: expected {}, got {}".format(
                name, type_id, src.source_type_id)

    def test_get_envelope_sources(self):
        for name, type_id in [("Env1", 2), ("Env2", 3), ("Env3", 4), ("Env4", 5)]:
            src = get_source(name)
            assert src.source_type_id == type_id

    def test_get_midi_sources(self):
        for name, type_id in [("Velocity", 16), ("ModWheel", 18), ("Note", 17)]:
            src = get_source(name)
            assert src.source_type_id == type_id

    def test_unknown_source_raises(self):
        with pytest.raises(ValueError, match="Unknown modulation source"):
            get_source("BOGUS_SOURCE")

    def test_get_filter1_cutoff_destination(self):
        dst = get_destination("Filter1.Cutoff")
        assert dst.dest_module_type_string == "VoiceFilter"
        assert dst.dest_module_param_name == "kParamFreq"
        assert dst.dest_module_param_id == 3
        assert dst.dest_module_id == 0

    def test_get_filter2_cutoff_destination(self):
        dst = get_destination("Filter2.Cutoff")
        assert dst.dest_module_id == 1
        assert dst.dest_module_param_id == 3

    def test_unknown_destination_raises(self):
        with pytest.raises(ValueError, match="Unknown modulation destination"):
            get_destination("BOGUS.DEST")

    def test_amount_conversion_roundtrip(self):
        for norm in [-1.0, -0.5, 0.0, 0.37, 0.5, 1.0]:
            cbor = normalize_to_cbor_amount(norm)
            assert abs(cbor - norm * 100.0) < 1e-9
            back = cbor_amount_to_normalized(cbor)
            assert abs(back - norm) < 1e-9

    def test_amount_clamped_to_bounds(self):
        assert normalize_to_cbor_amount(1.5) == 100.0
        assert normalize_to_cbor_amount(-2.0) == -100.0


# ---------------------------------------------------------------------------
# TestModulationAdapter
# ---------------------------------------------------------------------------

class TestModulationAdapter:
    def test_find_empty_slot_all_default(self):
        body = {"ModSlot{}".format(i): "default" for i in range(MAX_MODULATION_SLOTS)}
        assert find_empty_slot(body) == 0

    def test_find_empty_slot_skips_occupied(self):
        body = {"ModSlot{}".format(i): "default" for i in range(MAX_MODULATION_SLOTS)}
        body["ModSlot0"] = _lfo1_filter_slot()
        body["ModSlot1"] = _lfo1_filter_slot()
        assert find_empty_slot(body) == 2

    def test_find_empty_slot_none_when_full(self):
        body = {"ModSlot{}".format(i): _lfo1_filter_slot() for i in range(MAX_MODULATION_SLOTS)}
        assert find_empty_slot(body) is None

    def test_write_modulation_lfo1_filter_cutoff(self):
        body = {"ModSlot{}".format(i): "default" for i in range(MAX_MODULATION_SLOTS)}
        new_body, entry = write_modulation(
            body, source="LFO1", destination="Filter1.Cutoff", amount=0.37
        )
        assert entry.slot_index == 0
        assert entry.source_name == "LFO1"
        assert entry.destination_name == "Filter1.Cutoff"
        assert abs(entry.amount_cbor - 37.0) < 1e-9
        slot_dict = new_body["ModSlot0"]
        assert slot_dict["source"] == [6, 0]
        assert slot_dict["destModuleTypeString"] == "VoiceFilter"
        assert slot_dict["destModuleParamName"] == "kParamFreq"
        assert abs(slot_dict["plainParams"]["kParamAmount"] - 37.0) < 1e-9

    def test_write_modulation_does_not_mutate_original(self):
        body = {"ModSlot0": "default"}
        new_body, _ = write_modulation(
            body, source="LFO1", destination="Filter1.Cutoff", amount=0.5
        )
        assert body["ModSlot0"] == "default"
        assert new_body["ModSlot0"] != "default"

    def test_write_modulation_explicit_slot(self):
        body = {"ModSlot{}".format(i): "default" for i in range(MAX_MODULATION_SLOTS)}
        new_body, entry = write_modulation(
            body, source="LFO2", destination="Filter1.Resonance", amount=0.5, slot_index=7
        )
        assert entry.slot_index == 7
        assert entry.source.source_type_id == 7  # LFO2

    def test_read_slot_populated(self):
        body = _make_body_with_slot(0, _lfo1_filter_slot(50.0))
        entry = read_slot(body, 0)
        assert entry is not None
        assert entry.source_name == "LFO1"
        assert entry.destination_name == "Filter1.Cutoff"
        assert abs(entry.amount_cbor - 50.0) < 1e-9
        assert abs(entry.amount_normalized - 0.5) < 1e-9

    def test_read_slot_empty_returns_none(self):
        body = {"ModSlot0": "default"}
        assert read_slot(body, 0) is None

    def test_remove_modulation_clears_slot(self):
        body = _make_body_with_slot(3, _lfo1_filter_slot())
        new_body = remove_modulation(body, 3)
        assert new_body["ModSlot3"] == "default"
        assert body["ModSlot3"] != "default"  # original unchanged


# ---------------------------------------------------------------------------
# TestVST3Modulation — requires DawDreamer + Serum VST3
# ---------------------------------------------------------------------------

def _load_serum(body: dict):
    """Load Serum with given body. Returns (engine, synth) — caller keeps both alive."""
    import dawdreamer as daw
    from serum2 import bridge
    from serum2.evidence import epoch as epoch_mod

    skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
    meta, _ = skeleton

    fd, tmp = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    bridge.write_state_file(tmp, meta, body)
    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor("serum", epoch_mod.SERUM_VST3)
    synth.load_state(tmp)
    os.remove(tmp)
    return engine, synth, skeleton


def _centroid_std(audio: np.ndarray, sr: int = 44100, win_ms: int = 50) -> float:
    n = int(sr * win_ms / 1000)
    cs = []
    for i in range(0, len(audio) - n, n):
        chunk = audio[i:i + n]
        if np.abs(chunk).max() < 1e-6:
            continue
        fft = np.abs(np.fft.rfft(chunk * np.hanning(n)))
        freqs = np.fft.rfftfreq(n, 1 / sr)
        cs.append(np.sum(freqs * fft) / (np.sum(fft) + 1e-10))
    return float(np.std(cs)) if cs else 0.0


@pytest.mark.vst3
class TestVST3Modulation:
    """Requires SERUM_VST3 loaded in DawDreamer."""

    def test_modulation_slot_persists_through_save_state(self):
        from serum2 import bridge, vst3_state, codec
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body_base = skeleton

        body_mod, entry = write_modulation(
            body_base, source="LFO1", destination="Filter1.Cutoff", amount=0.37
        )

        engine, synth, _ = _load_serum(body_mod)

        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        synth.save_state(tmp)
        raw = open(tmp, "rb").read()
        os.remove(tmp)

        icomp = vst3_state.unwrap_vc2(raw)
        _, body_saved = codec.decode(icomp)

        slot = body_saved.get("ModSlot0", {})
        assert isinstance(slot, dict), "ModSlot0 not a dict after round-trip"
        assert slot.get("source") == [6, 0]
        assert slot.get("destModuleTypeString") == "VoiceFilter"
        assert slot.get("destModuleParamName") == "kParamFreq"
        assert abs(slot["plainParams"]["kParamAmount"] - 37.0) < 1e-9

    def test_lfo1_filter_cutoff_audio_causality(self):
        """LFO1→Filter1.Cutoff causes spectral centroid to oscillate (>2x std increase)."""
        from serum2 import bridge
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body_base = skeleton

        # Baseline: filter on, no LFO mod
        engine_b, synth_b, _ = _load_serum(body_base)
        synth_b.set_parameter(203, 1.0)   # Filter 1 On
        synth_b.set_parameter(205, 0.35)  # Filter 1 Freq
        synth_b.add_midi_note(60, 100, 0.0, 1.9)
        engine_b.load_graph([(synth_b, [])])
        engine_b.render(2.0)
        audio_base = np.array(synth_b.get_audio()).mean(axis=0)
        std_base = _centroid_std(audio_base)

        # Modulated: LFO1 at 2 Hz → Filter Cutoff
        body_mod = copy.deepcopy(body_base)
        body_mod["ModSlot0"] = {
            "destModuleID": 0, "destModuleParamID": 3,
            "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
            "plainParams": {"kParamAmount": 80.0}, "source": [6, 0],
        }
        body_mod["LFO0"] = {
            "curveData": {}, "pathData": {},
            "plainParams": {"kParamRate": 2.0, "kParamMode": "Free", "kParamDefaultMode": 0.0},
        }

        engine_m, synth_m, _ = _load_serum(body_mod)
        synth_m.set_parameter(203, 1.0)
        synth_m.set_parameter(205, 0.35)
        synth_m.add_midi_note(60, 100, 0.0, 1.9)
        engine_m.load_graph([(synth_m, [])])
        engine_m.render(2.0)
        audio_mod = np.array(synth_m.get_audio()).mean(axis=0)
        std_mod = _centroid_std(audio_mod)

        ratio = std_mod / (std_base + 1e-10)
        assert ratio > 2.0, (
            "Expected LFO1→Filter causality (std ratio > 2), got {:.2f}. "
            "std_base={:.1f}, std_mod={:.1f}".format(ratio, std_base, std_mod)
        )

    def test_write_modulation_api_matches_raw_slot(self):
        """write_modulation() produces same body structure as hand-crafted slot."""
        from serum2 import bridge
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body_base = skeleton

        # Via adapter
        body_api, entry = write_modulation(
            body_base, source="LFO1", destination="Filter1.Cutoff", amount=0.37
        )

        # Hand-crafted
        body_raw = copy.deepcopy(body_base)
        body_raw["ModSlot0"] = _lfo1_filter_slot(37.0)

        # Both should produce identical ModSlot0
        assert body_api["ModSlot0"] == body_raw["ModSlot0"]

    def test_remove_modulation_clears_slot_in_serum(self):
        """After remove_modulation, save_state shows slot as 'default' or absent."""
        from serum2 import bridge, vst3_state, codec
        from serum2.evidence import epoch as epoch_mod

        skeleton = bridge.capture_v8_skeleton(epoch_mod.SERUM_VST3)
        meta, body_base = skeleton

        # Write a modulation
        body_mod, entry = write_modulation(
            body_base, source="LFO1", destination="Filter1.Cutoff", amount=0.5
        )
        # Remove it
        body_cleared = remove_modulation(body_mod, entry.slot_index)

        engine, synth, _ = _load_serum(body_cleared)

        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        synth.save_state(tmp)
        raw = open(tmp, "rb").read()
        os.remove(tmp)

        icomp = vst3_state.unwrap_vc2(raw)
        _, body_saved = codec.decode(icomp)

        slot = body_saved.get("ModSlot{}".format(entry.slot_index))
        # Serum may serialize the slot as 'default', an empty dict, or absent
        is_empty = (slot is None or slot == "default" or
                    (isinstance(slot, dict) and
                     (slot.get("plainParams") in (None, "default", {}))))
        assert is_empty, "Expected cleared slot, got: {!r}".format(slot)
