import copy

import pytest

from serum2 import bridge
from serum2.processor_state import (
    ProcessorBodyError,
    ProcessorMetadataError,
    ProcessorStateError,
    require_processor_state,
    validate_processor_state,
)


def test_valid_native_skeleton_is_accepted():
    meta = {
        "component": "processor",
        "version": 8.0,
        "product": "Serum2",
        "productVersion": "2.0.21",
        "vendor": "Xfer Records",
    }
    body = {"Global0": {"plainParams": {}}}

    ctx = validate_processor_state(meta, body, source="test")

    assert ctx.component == "processor"
    assert ctx.version == 8.0


def test_missing_component_is_rejected():
    meta = {
        "version": 8.0,
        "product": "Serum2",
        "productVersion": "2.0.21",
    }
    body = {"Global0": {"plainParams": {}}}

    with pytest.raises(ProcessorMetadataError, match="component"):
        validate_processor_state(meta, body)


def test_empty_metadata_is_rejected():
    meta = {}
    body = {"Global0": {"plainParams": {}}}

    with pytest.raises(ProcessorMetadataError):
        validate_processor_state(meta, body)


def test_wrong_component_is_rejected():
    meta = {
        "component": "preset",
        "version": 8.0,
    }
    body = {"Global0": {"plainParams": {}}}

    with pytest.raises(ProcessorMetadataError, match="component"):
        validate_processor_state(meta, body)


def test_wrong_version_is_rejected():
    meta = {
        "component": "processor",
        "version": 5.0,
    }
    body = {"Global0": {"plainParams": {}}}

    with pytest.raises(ProcessorMetadataError, match="version"):
        validate_processor_state(meta, body)


def test_empty_body_is_rejected():
    meta = {
        "component": "processor",
        "version": 8.0,
    }

    with pytest.raises(ProcessorBodyError):
        validate_processor_state(meta, {})


def test_historical_16_5_17_shape_is_rejected():
    """
    Exact regression test for the contamination that caused the false
    negative results from 16.5.17 onward.
    """
    meta = {}
    body = {
        "Oscillator0": {
            "plainParams": {
                "kParamVolume": 0.5,
            }
        }
    }

    with pytest.raises(ProcessorStateError):
        require_processor_state(
            (meta, body),
            source="historical-16.5.17-regression",
        )


def test_validation_does_not_mutate_state():
    meta = {
        "component": "processor",
        "version": 8.0,
    }
    body = {
        "Global0": {
            "plainParams": {
                "kParamMasterVolume": 0.5,
            }
        }
    }

    original_meta = copy.deepcopy(meta)
    original_body = copy.deepcopy(body)

    require_processor_state((meta, body))

    assert meta == original_meta
    assert body == original_body


def test_native_capture_is_valid():
    """
    Integration test against the actual Serum 2.0.21 installation.

    This is intentionally separate from the pure unit tests because it
    requires DawDreamer + the installed Serum VST3.
    """
    skeleton = bridge.capture_v8_skeleton(
        r"C:\Program Files\Common Files\VST3\Serum2.vst3"
    )

    require_processor_state(
        skeleton,
        source="live-serum-2.0.21",
    )

    meta, body = skeleton

    assert meta["component"] == "processor"
    assert float(meta["version"]) == 8.0
    assert body