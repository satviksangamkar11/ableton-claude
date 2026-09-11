"""16.5.69.2-A3-20: Modulation source and destination tables.

Empirically derived in Step 20.

SOURCE TYPE IDs (first element of ModSlot.source):
  Confirmed via audio causality (spectral centroid std ratio):
    6  = LFO1  (LFO0 in CBOR), proven causal at 1996x std
    7  = LFO2  (LFO1 in CBOR), driven_by_LFO1 confirmed
    8  = LFO3  (LFO2 in CBOR), driven_by_LFO2 confirmed
    9  = LFO4  (LFO3 in CBOR), driven_by_LFO3 confirmed
    10 = LFO5  (LFO4 in CBOR), driven_by_LFO4 confirmed
    11-15 = LFO6-LFO10 (LFO5-LFO9 in CBOR), inferred pattern
    2-5 = Env1-Env4 (Env0-Env3 in CBOR), produce modulation at ~519 std
    16 = Velocity (no modulation at constant MIDI velocity)
    17 = Note (no measurable modulation)
    18 = ModWheel (zero by default = no modulation)
  NOT_SUPPORTED: 1 (produces no modulation, unknown type)

SOURCE second element:
  0 for all primary source instances.
  Higher values appear in corpus but semantics unresolved; NOT_SUPPORTED here.

DESTINATION PARAMETER IDs (from corpus analysis):
  VoiceFilter kParamFreq: paramID=3
  VoiceFilter kParamReso: paramID=4
  VoiceFilter kParamDrive: paramID=5
  VoiceFilter kParamWet: paramID=1
  Oscillator kParamVolume: paramID=1
  Oscillator kParamPan: paramID=2
  Oscillator kParamFine: paramID=5
  WTOsc kParamWarp: paramID=0
  WTOsc kParamTablePos: paramID=1
  Env kParamAttack: paramID=0
  Env kParamDecay: paramID=2
  Env kParamSustain: paramID=3
  Env kParamRelease: paramID=4
  LFO kParamRate: paramID=0
  Macro kParamValue: paramID=0

MODULE IDs:
  Filter1 = destModuleID=0, Filter2 = destModuleID=1
  Osc1 = destModuleID=0, Osc2 = destModuleID=1, Osc3 = destModuleID=2
  Env1 = destModuleID=0, Env2 = destModuleID=1, ...
  LFO1 = destModuleID=0, LFO2 = destModuleID=1, ...
  Macro1 = destModuleID=0, ...

AMOUNT:
  User-facing: normalized [-1.0, +1.0]
  Serum internal: kParamAmount = amount * 100  (range: -100.0 to +100.0)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModulationSource:
    name: str
    source_type_id: int
    source_bus_id: int = 0
    cbor_module_key: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class ModulationDestination:
    name: str
    dest_module_type_string: str
    dest_module_param_name: str
    dest_module_param_id: int
    dest_module_id: int
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Source table — empirically proven
# ---------------------------------------------------------------------------

_SOURCES: dict[str, ModulationSource] = {
    # LFOs (source_type_id = cbor_lfo_index + 6)
    "LFO1":  ModulationSource("LFO1",  6,  0, "LFO0",  "Proven: 1996x centroid std vs baseline"),
    "LFO2":  ModulationSource("LFO2",  7,  0, "LFO1",  "Proven: driven_by_LFO1"),
    "LFO3":  ModulationSource("LFO3",  8,  0, "LFO2",  "Proven: driven_by_LFO2"),
    "LFO4":  ModulationSource("LFO4",  9,  0, "LFO3",  "Proven: driven_by_LFO3"),
    "LFO5":  ModulationSource("LFO5", 10,  0, "LFO4",  "Proven: driven_by_LFO4"),
    "LFO6":  ModulationSource("LFO6", 11,  0, "LFO5",  "Pattern extrapolation; NOT behavior-verified"),
    "LFO7":  ModulationSource("LFO7", 12,  0, "LFO6",  "Pattern extrapolation"),
    "LFO8":  ModulationSource("LFO8", 13,  0, "LFO7",  "Pattern extrapolation"),
    "LFO9":  ModulationSource("LFO9", 14,  0, "LFO8",  "Pattern extrapolation"),
    "LFO10": ModulationSource("LFO10",15,  0, "LFO9",  "Pattern extrapolation"),
    # Envelopes (source_type_id = cbor_env_index + 2)
    "Env1":  ModulationSource("Env1",  2,  0, "Env0",  "Inferred: type 2 produces ~519 centroid std"),
    "Env2":  ModulationSource("Env2",  3,  0, "Env1",  "Inferred: type 3"),
    "Env3":  ModulationSource("Env3",  4,  0, "Env2",  "Inferred: type 4"),
    "Env4":  ModulationSource("Env4",  5,  0, "Env3",  "Inferred: type 5"),
    # MIDI sources (behavior: constant during a held note → low std)
    "Velocity":  ModulationSource("Velocity",  16, 0, None, "Type 16, no modulation at constant velocity"),
    "ModWheel":  ModulationSource("ModWheel",  18, 0, None, "Type 18, zero by default"),
    "Note":      ModulationSource("Note",      17, 0, None, "Type 17, constant during a note"),
}


def get_source(name: str) -> ModulationSource:
    src = _SOURCES.get(name)
    if src is None:
        raise ValueError("Unknown modulation source: {!r}. Known: {}".format(
            name, sorted(_SOURCES.keys())))
    return src


def list_sources() -> list[str]:
    return sorted(_SOURCES.keys())


# ---------------------------------------------------------------------------
# Destination table — from corpus paramID analysis
# ---------------------------------------------------------------------------

_DESTINATIONS: dict[str, ModulationDestination] = {
    # VoiceFilter (Filter1 = moduleID 0, Filter2 = moduleID 1)
    "Filter1.Cutoff":    ModulationDestination("Filter1.Cutoff",    "VoiceFilter", "kParamFreq", 3, 0),
    "Filter1.Resonance": ModulationDestination("Filter1.Resonance", "VoiceFilter", "kParamReso", 4, 0),
    "Filter1.Drive":     ModulationDestination("Filter1.Drive",     "VoiceFilter", "kParamDrive", 5, 0),
    "Filter1.Wet":       ModulationDestination("Filter1.Wet",       "VoiceFilter", "kParamWet", 1, 0),
    "Filter2.Cutoff":    ModulationDestination("Filter2.Cutoff",    "VoiceFilter", "kParamFreq", 3, 1),
    "Filter2.Resonance": ModulationDestination("Filter2.Resonance", "VoiceFilter", "kParamReso", 4, 1),
    "Filter2.Drive":     ModulationDestination("Filter2.Drive",     "VoiceFilter", "kParamDrive", 5, 1),
    "Filter2.Wet":       ModulationDestination("Filter2.Wet",       "VoiceFilter", "kParamWet", 1, 1),
    # Oscillators (Osc1=0, Osc2=1, Osc3=2)
    "Osc1.Volume":       ModulationDestination("Osc1.Volume",       "Oscillator",  "kParamVolume",  1, 0),
    "Osc1.Pan":          ModulationDestination("Osc1.Pan",          "Oscillator",  "kParamPan",     2, 0),
    "Osc1.Fine":         ModulationDestination("Osc1.Fine",         "Oscillator",  "kParamFine",    5, 0),
    "Osc1.Coarse":       ModulationDestination("Osc1.Coarse",       "Oscillator",  "kParamCoarsePit", 6, 0),
    "Osc2.Volume":       ModulationDestination("Osc2.Volume",       "Oscillator",  "kParamVolume",  1, 1),
    "Osc2.Pan":          ModulationDestination("Osc2.Pan",          "Oscillator",  "kParamPan",     2, 1),
    "Osc2.Fine":         ModulationDestination("Osc2.Fine",         "Oscillator",  "kParamFine",    5, 1),
    "Osc3.Volume":       ModulationDestination("Osc3.Volume",       "Oscillator",  "kParamVolume",  1, 2),
    "Osc3.Pan":          ModulationDestination("Osc3.Pan",          "Oscillator",  "kParamPan",     2, 2),
    # Wavetable oscillator
    "Osc1.WarpAmt":      ModulationDestination("Osc1.WarpAmt",      "WTOsc",       "kParamWarp",    0, 0),
    "Osc1.TablePos":     ModulationDestination("Osc1.TablePos",     "WTOsc",       "kParamTablePos",1, 0),
    "Osc2.WarpAmt":      ModulationDestination("Osc2.WarpAmt",      "WTOsc",       "kParamWarp",    0, 1),
    "Osc2.TablePos":     ModulationDestination("Osc2.TablePos",     "WTOsc",       "kParamTablePos",1, 1),
    # Envelopes (Env1=0, Env2=1, Env3=2, Env4=3)
    "Env1.Attack":       ModulationDestination("Env1.Attack",       "Env",         "kParamAttack",  0, 0),
    "Env1.Decay":        ModulationDestination("Env1.Decay",        "Env",         "kParamDecay",   2, 0),
    "Env1.Sustain":      ModulationDestination("Env1.Sustain",      "Env",         "kParamSustain", 3, 0),
    "Env1.Release":      ModulationDestination("Env1.Release",      "Env",         "kParamRelease", 4, 0),
    "Env2.Attack":       ModulationDestination("Env2.Attack",       "Env",         "kParamAttack",  0, 1),
    "Env2.Decay":        ModulationDestination("Env2.Decay",        "Env",         "kParamDecay",   2, 1),
    "Env2.Sustain":      ModulationDestination("Env2.Sustain",      "Env",         "kParamSustain", 3, 1),
    "Env2.Release":      ModulationDestination("Env2.Release",      "Env",         "kParamRelease", 4, 1),
    # LFO modulation (LFO1=0, LFO2=1, ...)
    "LFO1.Rate":         ModulationDestination("LFO1.Rate",         "LFO",         "kParamRate",    0, 0),
    "LFO2.Rate":         ModulationDestination("LFO2.Rate",         "LFO",         "kParamRate",    0, 1),
    "LFO1.Smooth":       ModulationDestination("LFO1.Smooth",       "LFO",         "kParamSmooth",  1, 0),
    # Macros (Macro1=0, Macro2=1, ...)
    "Macro1":            ModulationDestination("Macro1",            "Macro",       "kParamValue",   0, 0),
    "Macro2":            ModulationDestination("Macro2",            "Macro",       "kParamValue",   0, 1),
    "Macro3":            ModulationDestination("Macro3",            "Macro",       "kParamValue",   0, 2),
    "Macro4":            ModulationDestination("Macro4",            "Macro",       "kParamValue",   0, 3),
}


def get_destination(name: str) -> ModulationDestination:
    dst = _DESTINATIONS.get(name)
    if dst is None:
        raise ValueError("Unknown modulation destination: {!r}. Known: {}".format(
            name, sorted(_DESTINATIONS.keys())))
    return dst


def list_destinations() -> list[str]:
    return sorted(_DESTINATIONS.keys())


# ---------------------------------------------------------------------------
# Amount conversion
# ---------------------------------------------------------------------------

def normalize_to_cbor_amount(amount: float) -> float:
    """Convert user-facing normalized amount [-1.0, +1.0] to Serum's kParamAmount [-100, +100]."""
    clamped = max(-1.0, min(1.0, float(amount)))
    return clamped * 100.0


def cbor_amount_to_normalized(cbor_amount: float) -> float:
    """Convert Serum's kParamAmount [-100, +100] to normalized [-1.0, +1.0]."""
    return cbor_amount / 100.0
