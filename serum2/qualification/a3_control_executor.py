"""16.5.69.2-A3: Control execution protocol and adapters.

Abstract the execution mechanism (local DawDreamer, Ableton MCP, etc)
from the qualification logic.

ControlExecutor is the narrow boundary between FamilyBulkQualifier
and any concrete control backend.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# ControlExecutor protocol
# ---------------------------------------------------------------------------

class ControlExecutor(Protocol):
    """Protocol for executing parameter control operations.

    Implementations: DawDreamer-backed executor, Ableton MCP adapter, etc.
    """

    def set_parameter(
        self,
        semantic_id: str,
        value: float | int | bool | str,
    ) -> None:
        """Set a parameter value by semantic ID.

        Args:
            semantic_id: semantic target name (e.g., "OSC1.Pitch")
            value: value to set (type depends on parameter)

        Raises:
            ValueError: if semantic_id not found
            RuntimeError: if set fails
        """
        ...

    def read_parameter(
        self,
        semantic_id: str,
    ) -> object:
        """Read current parameter value by semantic ID.

        Args:
            semantic_id: semantic target name

        Returns:
            current value (type depends on parameter)

        Raises:
            ValueError: if semantic_id not found
        """
        ...

    def restore_parameter(
        self,
        semantic_id: str,
        baseline: object,
    ) -> None:
        """Restore parameter to a prior baseline value.

        Args:
            semantic_id: semantic target name
            baseline: value to restore

        Raises:
            ValueError: if semantic_id not found
            RuntimeError: if restore fails
        """
        ...


# ---------------------------------------------------------------------------
# Execution result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParameterExecutionResult:
    """Result of a single set/restore/read operation."""

    semantic_id: str
    operation: str  # "set" | "read" | "restore"
    success: bool
    value_attempted: Optional[object] = None
    value_read: Optional[object] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Null executor for testing
# ---------------------------------------------------------------------------

class NullExecutor:
    """No-op executor for testing framework logic without live audio."""

    def __init__(self):
        self.state: dict[str, object] = {}

    def set_parameter(
        self,
        semantic_id: str,
        value: float | int | bool | str,
    ) -> None:
        self.state[semantic_id] = value

    def read_parameter(self, semantic_id: str) -> object:
        return self.state.get(semantic_id)

    def restore_parameter(
        self,
        semantic_id: str,
        baseline: object,
    ) -> None:
        self.state[semantic_id] = baseline


# ---------------------------------------------------------------------------
# Executor decorator for result tracking
# ---------------------------------------------------------------------------

class ExecutorWithTracking:
    """Wraps a ControlExecutor and records all operations."""

    def __init__(self, executor: ControlExecutor):
        self.executor = executor
        self.operations: list[ParameterExecutionResult] = []

    def set_parameter(
        self,
        semantic_id: str,
        value: float | int | bool | str,
    ) -> None:
        try:
            self.executor.set_parameter(semantic_id, value)
            self.operations.append(
                ParameterExecutionResult(
                    semantic_id=semantic_id,
                    operation="set",
                    success=True,
                    value_attempted=value,
                )
            )
        except Exception as e:
            self.operations.append(
                ParameterExecutionResult(
                    semantic_id=semantic_id,
                    operation="set",
                    success=False,
                    value_attempted=value,
                    error=str(e),
                )
            )
            raise

    def read_parameter(self, semantic_id: str) -> object:
        try:
            value = self.executor.read_parameter(semantic_id)
            self.operations.append(
                ParameterExecutionResult(
                    semantic_id=semantic_id,
                    operation="read",
                    success=True,
                    value_read=value,
                )
            )
            return value
        except Exception as e:
            self.operations.append(
                ParameterExecutionResult(
                    semantic_id=semantic_id,
                    operation="read",
                    success=False,
                    error=str(e),
                )
            )
            raise

    def restore_parameter(
        self,
        semantic_id: str,
        baseline: object,
    ) -> None:
        try:
            self.executor.restore_parameter(semantic_id, baseline)
            self.operations.append(
                ParameterExecutionResult(
                    semantic_id=semantic_id,
                    operation="restore",
                    success=True,
                    value_attempted=baseline,
                )
            )
        except Exception as e:
            self.operations.append(
                ParameterExecutionResult(
                    semantic_id=semantic_id,
                    operation="restore",
                    success=False,
                    value_attempted=baseline,
                    error=str(e),
                )
            )
            raise
