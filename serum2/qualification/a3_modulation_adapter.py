"""16.5.69.2-A3-20: Modulation adapter — write modulation routes into CBOR body.

Implements the human-like interface:
    serum.modulation.create(source="LFO1", destination="Filter1.Cutoff", amount=0.37)

The adapter translates source/destination names to the empirically-confirmed
ModSlot CBOR structure and writes it into a copy of the body.

ModSlot full structure (from corpus/Step 20 empirical resolution):
    {
        'destModuleID': int,              # 0=Filter1/Osc1, 1=Filter2/Osc2, etc.
        'destModuleParamID': int,         # parameter index within module
        'destModuleParamName': str,       # e.g. 'kParamFreq'
        'destModuleTypeString': str,      # e.g. 'VoiceFilter'
        'plainParams': {'kParamAmount': float},  # -100 to +100
        'source': [type_id, bus_id],     # e.g. [6, 0] for LFO1
    }

Slot selection:
  Slots 0-63 (ModSlot0-ModSlot63) are available.
  A slot is 'default' (empty) in the CBOR body when no modulation is assigned.
  write_modulation() fills the first available empty slot unless slot_index given.

Persistence:
  Verified: ModSlot persists through save_state→load_state round-trip (Step 20).

Audio causality:
  Verified: LFO1→Filter1.Cutoff produces 1996x centroid std ratio vs baseline (Step 20).

Limitations (NOT_SUPPORTED in this adapter):
  - Removing/replacing a modulation slot (read existing slots first)
  - Modulation from unknown source types (second source element ≠ 0)
  - Macro-to-macro routing (self-referential)
  - Per-voice LFO instances (corpus shows non-zero bus_id, semantics unresolved)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from serum2.qualification.a3_modulation_route import (
    ModulationSource,
    ModulationDestination,
    get_source,
    get_destination,
    normalize_to_cbor_amount,
    cbor_amount_to_normalized,
)


# ---------------------------------------------------------------------------
# ModulationSlotEntry — represents one entry in the modulation matrix
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModulationSlotEntry:
    slot_index: int
    source_name: str
    destination_name: str
    amount_normalized: float   # user-facing [-1.0, +1.0]
    amount_cbor: float         # Serum internal [-100.0, +100.0]
    source: ModulationSource
    destination: ModulationDestination

    @property
    def slot_key(self) -> str:
        return "ModSlot{}".format(self.slot_index)

    def to_cbor_dict(self) -> dict:
        return {
            "destModuleID": self.destination.dest_module_id,
            "destModuleParamID": self.destination.dest_module_param_id,
            "destModuleParamName": self.destination.dest_module_param_name,
            "destModuleTypeString": self.destination.dest_module_type_string,
            "plainParams": {"kParamAmount": self.amount_cbor},
            "source": [self.source.source_type_id, self.source.source_bus_id],
        }


# ---------------------------------------------------------------------------
# Adapter functions
# ---------------------------------------------------------------------------

MAX_MODULATION_SLOTS = 64


def find_empty_slot(body: dict, start: int = 0) -> Optional[int]:
    """Return index of first empty ModSlot (plainParams='default' or absent).

    Returns None if all 64 slots are occupied.
    """
    for i in range(start, MAX_MODULATION_SLOTS):
        key = "ModSlot{}".format(i)
        slot = body.get(key)
        if slot is None or slot == "default":
            return i
        if isinstance(slot, dict):
            plain = slot.get("plainParams")
            if plain is None or plain == "default" or not isinstance(plain, dict):
                return i
    return None


def read_slot(body: dict, slot_index: int) -> Optional[ModulationSlotEntry]:
    """Parse a populated ModSlot into a ModulationSlotEntry.

    Returns None if the slot is empty or unrecognized.
    """
    key = "ModSlot{}".format(slot_index)
    slot = body.get(key)
    if not slot or slot == "default" or not isinstance(slot, dict):
        return None
    plain = slot.get("plainParams")
    if not plain or plain == "default" or not isinstance(plain, dict):
        return None

    amount_cbor = plain.get("kParamAmount", 0.0)
    source_arr = slot.get("source", [])
    if not isinstance(source_arr, list) or len(source_arr) < 2:
        return None

    type_id = source_arr[0]
    bus_id = source_arr[1]
    dst_type = slot.get("destModuleTypeString")
    dst_param = slot.get("destModuleParamName")
    dst_module_id = slot.get("destModuleID")
    dst_param_id = slot.get("destModuleParamID")

    # Reverse-lookup source name
    from serum2.qualification.a3_modulation_route import _SOURCES, _DESTINATIONS
    src_name = None
    for name, src in _SOURCES.items():
        if src.source_type_id == type_id and src.source_bus_id == bus_id:
            src_name = name
            break

    # Reverse-lookup destination name
    dst_name = None
    for name, dst in _DESTINATIONS.items():
        if (dst.dest_module_type_string == dst_type and
                dst.dest_module_param_name == dst_param and
                dst.dest_module_id == dst_module_id and
                dst.dest_module_param_id == dst_param_id):
            dst_name = name
            break

    if src_name is None or dst_name is None:
        return None

    source = _SOURCES[src_name]
    destination = _DESTINATIONS[dst_name]
    return ModulationSlotEntry(
        slot_index=slot_index,
        source_name=src_name,
        destination_name=dst_name,
        amount_normalized=cbor_amount_to_normalized(amount_cbor),
        amount_cbor=amount_cbor,
        source=source,
        destination=destination,
    )


def read_all_slots(body: dict) -> list[ModulationSlotEntry]:
    """Return all recognized (non-empty, parseable) modulation slots."""
    entries = []
    for i in range(MAX_MODULATION_SLOTS):
        entry = read_slot(body, i)
        if entry is not None:
            entries.append(entry)
    return entries


def write_modulation(
    body: dict,
    *,
    source: str,
    destination: str,
    amount: float,
    slot_index: Optional[int] = None,
) -> tuple[dict, ModulationSlotEntry]:
    """Write a modulation route into a copy of body.

    Args:
        body:        CBOR body dict (not mutated; a copy is returned).
        source:      Human-readable source name, e.g. "LFO1".
        destination: Human-readable destination name, e.g. "Filter1.Cutoff".
        amount:      Normalized amount in [-1.0, +1.0].
        slot_index:  Slot to write to (0-63). If None, uses first available slot.

    Returns:
        (new_body, entry) where new_body is the modified body and entry describes
        the written slot.

    Raises:
        ValueError: Unknown source/destination or no empty slots available.
    """
    src = get_source(source)
    dst = get_destination(destination)
    amount_cbor = normalize_to_cbor_amount(amount)

    new_body = copy.deepcopy(body)

    if slot_index is None:
        slot_index = find_empty_slot(new_body)
        if slot_index is None:
            raise ValueError("All {} ModSlots are occupied".format(MAX_MODULATION_SLOTS))
    elif not (0 <= slot_index < MAX_MODULATION_SLOTS):
        raise ValueError("slot_index must be 0-{}, got {}".format(
            MAX_MODULATION_SLOTS - 1, slot_index))

    entry = ModulationSlotEntry(
        slot_index=slot_index,
        source_name=source,
        destination_name=destination,
        amount_normalized=float(amount),
        amount_cbor=amount_cbor,
        source=src,
        destination=dst,
    )

    new_body[entry.slot_key] = entry.to_cbor_dict()
    return new_body, entry


def remove_modulation(body: dict, slot_index: int) -> dict:
    """Clear a modulation slot (reset to 'default')."""
    if not (0 <= slot_index < MAX_MODULATION_SLOTS):
        raise ValueError("slot_index must be 0-{}, got {}".format(
            MAX_MODULATION_SLOTS - 1, slot_index))
    new_body = copy.deepcopy(body)
    new_body["ModSlot{}".format(slot_index)] = "default"
    return new_body


def set_modulation_amount(body: dict, slot_index: int, amount: float) -> tuple[dict, float]:
    """Update the amount of an existing modulation route.

    Args:
        body:       CBOR body dict (not mutated; a copy is returned).
        slot_index: Slot to update (0-63).
        amount:     New normalized amount in [-1.0, +1.0].

    Returns:
        (new_body, amount_cbor) where amount_cbor is the internal representation.

    Raises:
        ValueError: if slot is empty, unrecognizable, or slot_index out of range.
    """
    if not (0 <= slot_index < MAX_MODULATION_SLOTS):
        raise ValueError("slot_index must be 0-{}, got {}".format(
            MAX_MODULATION_SLOTS - 1, slot_index))

    entry = read_slot(body, slot_index)
    if entry is None:
        raise ValueError("ModSlot{} is empty or unrecognizable".format(slot_index))

    new_body = copy.deepcopy(body)
    amount_cbor = normalize_to_cbor_amount(amount)
    key = "ModSlot{}".format(slot_index)
    new_body[key]["plainParams"]["kParamAmount"] = amount_cbor
    return new_body, amount_cbor
