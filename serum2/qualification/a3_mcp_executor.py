"""16.5.69.2-A3: MCP-backed control executor.

Implements ControlExecutor protocol using Ableton MCP.

In production: real MCP calls to set_device_parameter, read state, restore.
For development/testing: stub MCP that simulates parameter control.

The executor is instantiated with the actual MCP session when available.
"""

from __future__ import annotations

from typing import Any, Optional
import copy


class MCPControlExecutor:
    """MCP-backed executor for parameter control via Ableton Live.

    When MCP is available, this receives the live session and routes
    set/read/restore operations through Ableton's parameter API.

    For development: uses a mock/stub that simulates the behavior.
    """

    def __init__(
        self,
        mcp_session: Optional[Any] = None,
        serum_device_index: int = 0,
        track_index: int = 0,
    ):
        """Initialize MCP executor.

        Args:
            mcp_session: Live MCP session object (or None for stub mode)
            serum_device_index: device index in track chain
            track_index: Ableton track index
        """
        self.mcp = mcp_session
        self.serum_device_index = serum_device_index
        self.track_index = track_index

        # Stub mode: maintain parameter state in memory
        self._stub_state: dict[str, object] = {}

        # Track operations for auditing
        self.operations: list[dict] = []

    def set_parameter(
        self,
        semantic_id: str,
        value: float | int | bool | str,
    ) -> None:
        """Set a parameter value by semantic ID.

        Args:
            semantic_id: VST3 parameter name (e.g., "B Level")
            value: value to set

        Raises:
            RuntimeError: if MCP call fails
        """
        if self.mcp:
            # Real MCP: route through Ableton Live
            self._mcp_set_parameter(semantic_id, value)
        else:
            # Stub mode: store in memory
            self._stub_state[semantic_id] = value

        self.operations.append({
            "operation": "set",
            "semantic_id": semantic_id,
            "value": value,
        })

    def read_parameter(self, semantic_id: str) -> object:
        """Read current parameter value by semantic ID.

        Args:
            semantic_id: VST3 parameter name

        Returns:
            current value

        Raises:
            RuntimeError: if MCP call fails
        """
        if self.mcp:
            # Real MCP: read from Ableton Live
            value = self._mcp_read_parameter(semantic_id)
        else:
            # Stub mode: retrieve from memory
            value = self._stub_state.get(semantic_id, 0.5)

        self.operations.append({
            "operation": "read",
            "semantic_id": semantic_id,
            "value": value,
        })
        return value

    def restore_parameter(
        self,
        semantic_id: str,
        baseline: object,
    ) -> None:
        """Restore parameter to baseline value.

        Args:
            semantic_id: VST3 parameter name
            baseline: value to restore

        Raises:
            RuntimeError: if MCP call fails
        """
        self.set_parameter(semantic_id, baseline)
        self.operations.append({
            "operation": "restore",
            "semantic_id": semantic_id,
            "value": baseline,
        })

    # -----------------------------------------------------------------------
    # Private: MCP integration (to be implemented with real MCP session)
    # -----------------------------------------------------------------------

    def _mcp_set_parameter(self, semantic_id: str, value: object) -> None:
        """Route set_parameter call through Ableton MCP."""
        if not self.mcp:
            return

        # Convert semantic_id to VST3 parameter name
        param_name = semantic_id

        # In real execution:
        # self.mcp.set_device_parameter(
        #     track_index=self.track_index,
        #     device_index=self.serum_device_index,
        #     parameter_name=param_name,
        #     value=value,
        # )

        # For now: stub that stores locally
        self._stub_state[semantic_id] = value

    def _mcp_read_parameter(self, semantic_id: str) -> object:
        """Route read_parameter call through Ableton MCP."""
        if not self.mcp:
            return self._stub_state.get(semantic_id, 0.5)

        # In real execution:
        # return self.mcp.get_device_parameter(
        #     track_index=self.track_index,
        #     device_index=self.serum_device_index,
        #     parameter_name=semantic_id,
        # )

        # For now: stub that retrieves from local state
        return self._stub_state.get(semantic_id, 0.5)

    # -----------------------------------------------------------------------
    # Auditing
    # -----------------------------------------------------------------------

    def get_operation_log(self) -> list[dict]:
        """Return all operations performed by this executor."""
        return copy.deepcopy(self.operations)

    def clear_operation_log(self) -> None:
        """Clear operation history."""
        self.operations = []
