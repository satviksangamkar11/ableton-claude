"""16.5.69.2-A3-21C: MCP-facing semantic control plane.

Public API for controlling Serum. Callers see semantic operations only.
No VST3 indices, ModSlot IDs, CBOR paths, or module IDs exposed.

Usage:
  from serum2.qualification.a3_mcp_control_plane import (
      ParameterController, ModulationController
  )

  # Parameters
  body, result = ParameterController.set_parameter(
      body, target="Filter.Resonance", value=90.0
  )

  # Modulation
  body, entry = ModulationController.create_modulation(
      body, source="LFO1", destination="Filter1.Cutoff", amount=0.37
  )
"""

from __future__ import annotations

from typing import Optional, NamedTuple

from serum2.qualification.a3_modulation_adapter import (
    write_modulation,
    read_slot,
    remove_modulation,
    set_modulation_amount,
    ModulationSlotEntry,
)


class ParameterControlResult(NamedTuple):
    """Result of a parameter control operation."""
    semantic_id: str
    value_set: float
    success: bool
    error: Optional[str] = None


class ModulationControlResult(NamedTuple):
    """Result of a modulation control operation."""
    slot_index: int
    source: str
    destination: str
    amount_normalized: float
    success: bool
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# ParameterController — semantic parameter interface
# ---------------------------------------------------------------------------

class ParameterController:
    """Control synthesis parameters via semantic targets, not VST3 indices."""

    @staticmethod
    def set_parameter(
        body: dict,
        *,
        target: str,
        value: float,
    ) -> tuple[dict, ParameterControlResult]:
        """Set a parameter by semantic target name.

        Args:
            body:   CBOR body dict.
            target: Semantic target (e.g., "Filter.Resonance").
            value:  Value in parameter's native range.

        Returns:
            (new_body, result) where new_body has the parameter written.

        Note:
            This is a placeholder. The actual implementation would:
            1. Look up target in semantic table
            2. Resolve to mutation route (host_param or cbor_body)
            3. Write via appropriate adapter
            4. For host_param: caller must use set_parameter() separately on VST3
            5. For cbor_body: caller can use this to update body, then load state

            For Step 21, we expose this interface but note that parameter
            control via this module is advisory for host_param routes.
        """
        # For now, this is a stub; the actual implementation would
        # consult the target registry and write appropriately.
        # Full parameter control requires VST3 host_param integration.
        return body, ParameterControlResult(
            semantic_id=target,
            value_set=value,
            success=False,
            error="Parameter control requires VST3 set_parameter() integration; "
                  "not exposed in CBOR-only interface",
        )


# ---------------------------------------------------------------------------
# ModulationController — semantic modulation interface
# ---------------------------------------------------------------------------

class ModulationController:
    """Control modulation routing via semantic source/destination names."""

    @staticmethod
    def create_modulation(
        body: dict,
        *,
        source: str,
        destination: str,
        amount: float,
        slot_index: Optional[int] = None,
    ) -> tuple[dict, ModulationControlResult]:
        """Create a modulation route.

        Args:
            body:        CBOR body dict.
            source:      Semantic source name (e.g., "LFO1").
            destination: Semantic destination name (e.g., "Filter1.Cutoff").
            amount:      Normalized amount in [-1.0, +1.0].
            slot_index:  Optional slot (0-63); auto-selected if None.

        Returns:
            (new_body, result) where new_body has the modulation written.

        Raises:
            ValueError: on unknown source/destination or no available slots.
        """
        try:
            new_body, entry = write_modulation(
                body, source=source, destination=destination, amount=amount,
                slot_index=slot_index
            )
            return new_body, ModulationControlResult(
                slot_index=entry.slot_index,
                source=entry.source_name,
                destination=entry.destination_name,
                amount_normalized=entry.amount_normalized,
                success=True,
            )
        except ValueError as e:
            return body, ModulationControlResult(
                slot_index=-1,
                source=source,
                destination=destination,
                amount_normalized=amount,
                success=False,
                error=str(e),
            )

    @staticmethod
    def update_modulation_amount(
        body: dict,
        *,
        slot_index: int,
        amount: float,
    ) -> tuple[dict, ModulationControlResult]:
        """Update the amount of an existing modulation route.

        Args:
            body:       CBOR body dict.
            slot_index: Slot to update (0-63).
            amount:     New normalized amount in [-1.0, +1.0].

        Returns:
            (new_body, result) where new_body has the amount updated.

        Raises:
            ValueError: if slot is empty or out of range.
        """
        try:
            # Read current entry to get source/destination for result
            entry = read_slot(body, slot_index)
            if entry is None:
                return body, ModulationControlResult(
                    slot_index=slot_index,
                    source="UNKNOWN",
                    destination="UNKNOWN",
                    amount_normalized=amount,
                    success=False,
                    error="ModSlot{} is empty".format(slot_index),
                )

            new_body, amount_cbor = set_modulation_amount(body, slot_index, amount)
            return new_body, ModulationControlResult(
                slot_index=slot_index,
                source=entry.source_name,
                destination=entry.destination_name,
                amount_normalized=amount,
                success=True,
            )
        except ValueError as e:
            return body, ModulationControlResult(
                slot_index=slot_index,
                source="UNKNOWN",
                destination="UNKNOWN",
                amount_normalized=amount,
                success=False,
                error=str(e),
            )

    @staticmethod
    def remove_modulation(
        body: dict,
        *,
        slot_index: int,
    ) -> tuple[dict, ModulationControlResult]:
        """Remove a modulation route.

        Args:
            body:       CBOR body dict.
            slot_index: Slot to clear (0-63).

        Returns:
            (new_body, result) where new_body has the slot cleared.

        Raises:
            ValueError: if slot_index out of range.
        """
        try:
            # Read current entry for result
            entry = read_slot(body, slot_index)
            new_body = remove_modulation(body, slot_index)
            return new_body, ModulationControlResult(
                slot_index=slot_index,
                source=entry.source_name if entry else "UNKNOWN",
                destination=entry.destination_name if entry else "UNKNOWN",
                amount_normalized=0.0,
                success=True,
            )
        except ValueError as e:
            return body, ModulationControlResult(
                slot_index=slot_index,
                source="UNKNOWN",
                destination="UNKNOWN",
                amount_normalized=0.0,
                success=False,
                error=str(e),
            )

    @staticmethod
    def read_modulation(body: dict, slot_index: int) -> Optional[ModulationControlResult]:
        """Read a modulation route.

        Returns:
            ModulationControlResult with the current state, or None if slot empty.
        """
        entry = read_slot(body, slot_index)
        if entry is None:
            return None
        return ModulationControlResult(
            slot_index=entry.slot_index,
            source=entry.source_name,
            destination=entry.destination_name,
            amount_normalized=entry.amount_normalized,
            success=True,
        )
