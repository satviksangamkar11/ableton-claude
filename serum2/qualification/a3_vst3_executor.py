"""16.5.69.2-A3: VST3-backed control executor via DawDreamer.

Real Serum VST3 parameter control. Not a stub.

For each parameter operation:
  - Set via synth.set_parameter()
  - Read back actual value
  - Restore to baseline

Evidence is individual per control, never batched into false unity.
"""

from __future__ import annotations

import tempfile
import os
from pathlib import Path
from typing import Optional

import dawdreamer as daw
import numpy as np

from serum2 import bridge as br


class VST3Executor:
    """Real Serum VST3 control via DawDreamer."""

    def __init__(self, vst3_path: str = "Serum", sr: int = 44100, block_size: int = 512):
        """Initialize VST3 executor.

        Args:
            vst3_path: VST3 plugin identifier (e.g., "Serum")
            sr: sample rate
            block_size: audio block size
        """
        self.vst3_path = vst3_path
        self.sr = sr
        self.block_size = block_size

        # Current state
        self.engine: Optional[daw.RenderEngine] = None
        self.synth: Optional[daw.PluginProcessor] = None
        self.skeleton: Optional[tuple] = None
        self.body: Optional[dict] = None

        # Parameter metadata cache
        self._param_by_name: dict[str, int] = {}
        self._operations = []

    def load_state(self, body: dict, skeleton: tuple) -> None:
        """Load Serum state from CBOR body."""
        self.body = body
        self.skeleton = skeleton

        # Create fresh engine/synth
        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        br.write_state_file(tmp, skeleton, body)

        self.engine = daw.RenderEngine(self.sr, self.block_size)
        self.synth = self.engine.make_plugin_processor("serum", self.vst3_path)
        self.synth.load_state(tmp)
        os.remove(tmp)

        # Build parameter name → index map
        params = self.synth.get_parameters_description()
        self._param_by_name = {p["name"]: p["index"] for p in params}

    def set_parameter(self, semantic_id: str, value: float | int | bool | str) -> None:
        """Set a Serum VST3 parameter by name."""
        if not self.synth or semantic_id not in self._param_by_name:
            raise ValueError(f"Parameter not found: {semantic_id}")

        param_idx = self._param_by_name[semantic_id]
        float_value = float(value) if not isinstance(value, bool) else float(value)
        self.synth.set_parameter(param_idx, float_value)

        self._operations.append({
            "op": "set",
            "semantic_id": semantic_id,
            "value": value,
        })

    def read_parameter(self, semantic_id: str) -> object:
        """Read current Serum VST3 parameter value."""
        if not self.synth or semantic_id not in self._param_by_name:
            raise ValueError(f"Parameter not found: {semantic_id}")

        param_idx = self._param_by_name[semantic_id]
        params = self.synth.get_parameters_description()
        param_info = next(p for p in params if p["index"] == param_idx)

        # Get current value
        value = self.synth.get_parameter(param_idx)

        self._operations.append({
            "op": "read",
            "semantic_id": semantic_id,
            "value": value,
        })
        return value

    def restore_parameter(self, semantic_id: str, baseline: object) -> None:
        """Restore parameter to baseline value."""
        self.set_parameter(semantic_id, baseline)
        self._operations.append({
            "op": "restore",
            "semantic_id": semantic_id,
            "value": baseline,
        })

    def save_state(self) -> dict:
        """Save current Serum state to CBOR body."""
        if not self.synth or not self.skeleton:
            raise RuntimeError("No state loaded")

        fd, tmp = tempfile.mkstemp(suffix=".bin")
        os.close(fd)
        self.synth.save_state(tmp)

        body = br.read_state_file(tmp)
        os.remove(tmp)
        return body

    def cleanup(self) -> None:
        """Clean up engine resources."""
        if self.engine:
            del self.engine
        if self.synth:
            del self.synth
        self.engine = None
        self.synth = None

    def get_operation_log(self) -> list[dict]:
        """Return all operations."""
        return self._operations.copy()
