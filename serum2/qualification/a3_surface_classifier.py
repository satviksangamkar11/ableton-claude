"""16.5.69.2-A3: Surface classification and filtering.

Classifies VST3 parameters into meaningful Serum control categories.

Classification pipeline:
  VST3 parameter name
    ↓
  SurfaceClass enum
    ↓
  meaningful Serum frontier
    ↓
  family grouping
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class SurfaceClass(Enum):
    """Parameter surface classification."""

    SYNTHESIS = "synthesis"
    MODULATION = "modulation"
    RESOURCE = "resource"
    STRUCTURAL = "structural"
    EFFECT = "effect"
    MACRO = "macro"
    MIDI = "midi"
    NON_SYNTHESIS = "non_synthesis"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------

def classify_parameter(vst3_name: str) -> SurfaceClass:
    """Classify a VST3 parameter by name into a surface class.

    Rules are ordered by specificity. First match wins.
    """
    name = vst3_name.strip()

    # MIDI passthrough
    if any(x in name.lower() for x in ["midi", "velocity", "aftertouch", "mod wheel"]):
        return SurfaceClass.MIDI

    # MACRO assignments (Macro1–8, global Macro control)
    if "macro" in name.lower():
        return SurfaceClass.MACRO

    # RESOURCE selectors (wavetable, sample, fx preset)
    if any(x in name.lower() for x in ["wavetable", "sample", "preset", "path"]):
        return SurfaceClass.RESOURCE

    # EFFECT parameters (all FX) — check before SYNTHESIS since effects are specific
    if any(
        x in name.lower()
        for x in [
            "eq",
            "compressor",
            "reverb",
            "delay",
            "chorus",
            "distortion",
            "resonator",
            "vocoder",
            "phaser",
            "flanger",
            "modfilter",
        ]
    ):
        return SurfaceClass.EFFECT

    # MODULATION sources (LFO rate, shape, sync, etc.)
    # Envelope is synthesis; LFO is modulation
    if "lfo" in name.lower():
        return SurfaceClass.MODULATION

    # SYNTHESIS parameters: oscillators and their controls take precedence
    # Check for oscillator prefix (A/B/C) and synthesis-specific terms
    if name.startswith(("A ", "B ", "C ")):
        # Oscillator controls: A Enable, A Level, etc.
        return SurfaceClass.SYNTHESIS

    if any(
        x in name.lower()
        for x in [
            "osc",
            "filter",
            "cutoff",
            "resonance",
            "resonance",
            "pitch",
            "volume",
            "level",
            "pan",
            "attack",
            "decay",
            "sustain",
            "release",
            "warp",
            "unison",
            "detune",
            "spread",
            "mix",
            "env",
        ]
    ):
        return SurfaceClass.SYNTHESIS

    # STRUCTURAL operations (fx on/off, routing topology)
    # Exclude oscillator controls which are synthesis
    if any(
        x in name.lower()
        for x in ["on/off", "bypass", "active", "select", "route"]
    ):
        return SurfaceClass.STRUCTURAL

    # "enable" for non-oscillators is structural
    if "enable" in name.lower() and not name.startswith(("A ", "B ", "C ")):
        return SurfaceClass.STRUCTURAL

    # MODULATION routing (when not part of synthesis)
    if "modulation" in name.lower():
        return SurfaceClass.MODULATION

    # NON_SYNTHESIS catch-all
    return SurfaceClass.NON_SYNTHESIS


def is_meaningful_surface(surface_class: SurfaceClass) -> bool:
    """Return True if the surface class is part of the meaningful control frontier."""
    meaningful = {
        SurfaceClass.SYNTHESIS,
        SurfaceClass.MODULATION,
        SurfaceClass.RESOURCE,
        SurfaceClass.STRUCTURAL,
        SurfaceClass.EFFECT,
        SurfaceClass.MACRO,
    }
    return surface_class in meaningful


def filter_meaningful_parameters(
    vst3_parameters: list[dict],
) -> list[dict]:
    """Filter VST3 parameter list to only meaningful Serum controls.

    Args:
        vst3_parameters: list of {vst3_name, vst3_index, ...} dicts

    Returns:
        filtered list where surface_class is SYNTHESIS, MODULATION, etc.
    """
    result = []
    for param in vst3_parameters:
        vst3_name = param.get("vst3_name", "")
        surface = classify_parameter(vst3_name)
        if is_meaningful_surface(surface):
            result.append({**param, "surface_class": surface.value})
    return result


def group_by_family(
    parameters: list[dict],
) -> dict[str, list[dict]]:
    """Group meaningful parameters by family (Osc1, Osc2, Filter1, Env1, LFO1, FX, etc).

    Args:
        parameters: list of {vst3_name, ...} dicts

    Returns:
        dict where keys are family names and values are parameter lists
    """
    families: dict[str, list[dict]] = {}

    for param in parameters:
        vst3_name = param.get("vst3_name", "").strip()
        family = _extract_family_name(vst3_name)

        if family not in families:
            families[family] = []
        families[family].append(param)

    return families


def _extract_family_name(vst3_name: str) -> str:
    """Extract family name from VST3 parameter name.

    Examples:
        "A Enable" → "Osc1"
        "B Pan" → "Osc2"
        "Filter 1 Cutoff" → "Filter1"
        "Env 1 Attack" → "Env1"
        "LFO 1 Rate" → "LFO1"
        "Master Volume" → "Global"
        "Mod Delay" → "FX"
    """
    name = vst3_name.strip()

    # Oscillators: A/B/C = Osc1/Osc2/Osc3
    if name.startswith("A "):
        return "Osc1"
    if name.startswith("B "):
        return "Osc2"
    if name.startswith("C "):
        return "Osc3"

    # Filters
    if "filter" in name.lower() and "1" in name:
        return "Filter1"
    if "filter" in name.lower() and "2" in name:
        return "Filter2"

    # Envelopes
    if "env" in name.lower():
        for i in range(1, 5):
            if str(i) in name:
                return f"Env{i}"

    # LFOs
    if "lfo" in name.lower():
        for i in range(1, 11):
            if str(i) in name:
                return f"LFO{i}"

    # Macros
    if "macro" in name.lower():
        return "Macro"

    # Global/Master
    if any(x in name.lower() for x in ["master", "global", "main"]):
        return "Global"

    # Effects
    if any(
        x in name.lower()
        for x in [
            "eq",
            "compressor",
            "reverb",
            "delay",
            "chorus",
            "distortion",
            "resonator",
            "vocoder",
            "phaser",
            "flanger",
            "modfilter",
        ]
    ):
        return "FX"

    # Default to "Residual"
    return "Residual"
