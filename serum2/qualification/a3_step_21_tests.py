"""16.5.69.2-A3-21: Final unified control plane tests.

Test groups:
  TestUnifiedCapability    (6 tests) — capability dataclass, status checks
  TestMCPControlPlane      (8 tests) — semantic control operations
  TestAudit                (2 tests) — audit execution and output format

Execution constraints:
  - NO rerun of completed tests (Steps 1-20 untouched)
  - Only new Step 21 tests
  - Do NOT rerun Step 20 tests unless Step 21 code changed them
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from serum2.qualification.a3_unified_capability import (
    UnifiedCapability,
    build_unified_registry,
)
from serum2.qualification.a3_mcp_control_plane import (
    ParameterController,
    ModulationController,
    ParameterControlResult,
    ModulationControlResult,
)
from serum2.qualification.a3_step_21_audit import run_step_21_audit


# ---------------------------------------------------------------------------
# TestUnifiedCapability
# ---------------------------------------------------------------------------

class TestUnifiedCapability:
    def test_create_parameter_capability(self):
        cap = UnifiedCapability(
            semantic_id="Filter.Resonance",
            control_type="PARAMETER",
            qualification_status="CAUSAL_VERIFIED",
            persistence="CBOR_BODY",
            restoration="FULL_SAVE_STATE",
        )
        assert cap.semantic_id == "Filter.Resonance"
        assert cap.is_controllable
        assert cap.is_behavioral

    def test_create_modulation_capability(self):
        cap = UnifiedCapability(
            semantic_id="Modulation.LFO1.Filter1.Cutoff",
            control_type="MODULATION",
            qualification_status="CAUSAL_VERIFIED",
            persistence="CBOR_BODY",
            restoration="FULL_SAVE_STATE",
        )
        assert cap.control_type == "MODULATION"
        assert cap.is_controllable
        assert cap.is_behavioral

    def test_create_resource_capability(self):
        cap = UnifiedCapability(
            semantic_id="Resource.OSC1.Wavetable",
            control_type="RESOURCE",
            qualification_status="ROUTE_RESOLVED",
            persistence="CBOR_BODY",
        )
        assert cap.control_type == "RESOURCE"
        assert cap.is_controllable
        assert not cap.is_behavioral

    def test_unknown_control_type_raises(self):
        with pytest.raises(ValueError, match="control_type"):
            UnifiedCapability(
                semantic_id="Test",
                control_type="BOGUS_TYPE",
                qualification_status="QUALIFIED",
            )

    def test_unknown_status_raises(self):
        with pytest.raises(ValueError, match="qualification_status"):
            UnifiedCapability(
                semantic_id="Test",
                control_type="PARAMETER",
                qualification_status="BOGUS_STATUS",
            )

    def test_to_dict_serialization(self):
        cap = UnifiedCapability(
            semantic_id="Filter.Resonance",
            control_type="PARAMETER",
            qualification_status="QUALIFIED",
            persistence="CBOR_BODY",
            notes="Test capability",
        )
        d = cap.to_dict()
        assert d["semantic_id"] == "Filter.Resonance"
        assert d["is_controllable"] is True
        assert d["notes"] == "Test capability"


# ---------------------------------------------------------------------------
# TestMCPControlPlane
# ---------------------------------------------------------------------------

class TestMCPControlPlane:
    def test_modulation_create_success(self):
        body = {"ModSlot{}".format(i): "default" for i in range(64)}
        new_body, result = ModulationController.create_modulation(
            body, source="LFO1", destination="Filter1.Cutoff", amount=0.37
        )
        assert result.success
        assert result.slot_index == 0
        assert result.source == "LFO1"
        assert result.destination == "Filter1.Cutoff"
        assert abs(result.amount_normalized - 0.37) < 1e-9

    def test_modulation_create_unknown_source(self):
        body = {"ModSlot0": "default"}
        new_body, result = ModulationController.create_modulation(
            body, source="BOGUS", destination="Filter1.Cutoff", amount=0.5
        )
        assert not result.success
        assert result.error is not None

    def test_modulation_create_unknown_destination(self):
        body = {"ModSlot0": "default"}
        new_body, result = ModulationController.create_modulation(
            body, source="LFO1", destination="BOGUS.DEST", amount=0.5
        )
        assert not result.success
        assert result.error is not None

    def test_modulation_update_amount(self):
        body = {
            "ModSlot0": {
                "destModuleID": 0, "destModuleParamID": 3,
                "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
                "plainParams": {"kParamAmount": 50.0}, "source": [6, 0],
            }
        }
        new_body, result = ModulationController.update_modulation_amount(
            body, slot_index=0, amount=0.75
        )
        assert result.success
        assert result.source == "LFO1"
        assert abs(result.amount_normalized - 0.75) < 1e-9
        assert abs(new_body["ModSlot0"]["plainParams"]["kParamAmount"] - 75.0) < 1e-9

    def test_modulation_update_empty_slot_fails(self):
        body = {"ModSlot0": "default"}
        new_body, result = ModulationController.update_modulation_amount(
            body, slot_index=0, amount=0.5
        )
        assert not result.success
        assert result.error is not None

    def test_modulation_remove(self):
        body = {
            "ModSlot0": {
                "destModuleID": 0, "destModuleParamID": 3,
                "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
                "plainParams": {"kParamAmount": 50.0}, "source": [6, 0],
            }
        }
        new_body, result = ModulationController.remove_modulation(body, slot_index=0)
        assert result.success
        assert new_body["ModSlot0"] == "default"

    def test_modulation_read(self):
        body = {
            "ModSlot0": {
                "destModuleID": 0, "destModuleParamID": 3,
                "destModuleParamName": "kParamFreq", "destModuleTypeString": "VoiceFilter",
                "plainParams": {"kParamAmount": 37.0}, "source": [6, 0],
            }
        }
        result = ModulationController.read_modulation(body, 0)
        assert result is not None
        assert result.source == "LFO1"
        assert result.destination == "Filter1.Cutoff"
        assert abs(result.amount_normalized - 0.37) < 1e-9

    def test_modulation_read_empty_slot(self):
        body = {"ModSlot0": "default"}
        result = ModulationController.read_modulation(body, 0)
        assert result is None


# ---------------------------------------------------------------------------
# TestAudit
# ---------------------------------------------------------------------------

class TestAudit:
    def test_audit_execution(self):
        """Run the final audit and verify it produces output."""
        audit = run_step_21_audit()
        assert audit is not None
        assert "total_vst3_parameters" in audit
        assert "discovered_controls" in audit
        assert "by_control_type" in audit

    def test_audit_json_output(self):
        """Verify audit can be written to JSON."""
        audit = run_step_21_audit()
        json_str = json.dumps(audit, indent=2)
        assert len(json_str) > 0
        # Verify it round-trips
        parsed = json.loads(json_str)
        assert parsed["total_vst3_parameters"] == audit["total_vst3_parameters"]
