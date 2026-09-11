#!/usr/bin/env python3
"""16.5.69.1-R, R3 — Conservative ResolvedTarget Record

Dataclass for registry entries: lossless identity + raw metadata.
No inferred semantic classification. No fabricated semantic_mutation_class.
Preserves raw values exactly as they appear in VST3 dump.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ResolvedTarget:
    """Qualified mapping of semantic target to VST3 parameter.

    Frozen: prevents accidental mutation or extension post-creation.
    Conservative: only stores facts proven by R1–R2 audits.
    """

    # ===== SEMANTIC IDENTITY =====
    semantic_id: str
    """Semantic identifier from targets.py (e.g., 'OSC1.Volume')"""

    capability_key: str
    """Capability key from targets.py (e.g., 'oscillator_field_OSC-VOLUME')"""

    # ===== VST3 QUALIFIED IDENTITY =====
    vst3_name: str
    """Exact VST3 parameter name from A1.1 dump"""

    vst3_index: int
    """VST3 parameter index (0–2622 for Serum 2.0.21)"""

    # ===== VST3 TRANSPORT METADATA =====
    # These come directly from A1.1 dump, validated by R1
    vst3_transport_kind: str
    """Transport classification: 'BOOLEAN', 'ENUM', 'SCALAR'"""

    is_boolean: bool
    """From VST3 dump: isBoolean"""

    is_discrete: bool
    """From VST3 dump: isDiscrete"""

    num_steps: Optional[int]
    """From VST3 dump: numSteps (for discrete parameters)"""

    # ===== RAW DOMAIN BOUNDARIES =====
    # Preserved exactly as they appear in VST3 dump
    # No parsing, no conversion, no semantic interpretation
    min_raw: Any
    """Raw min value from VST3 dump (may be string, float, or complex)"""

    max_raw: Any
    """Raw max value from VST3 dump (may be string, float, or complex)"""

    default_raw: Any
    """Raw defaultValue from VST3 dump (may be string, float, or complex)"""

    # ===== SEMANTIC CLASSIFICATION =====
    # Deliberately left UNCLASSIFIED during R3
    # Classification happens only during A3 mutation qualification
    semantic_mutation_class: Optional[str]
    """Semantic mutation class: BOOLEAN, ENUM, SCALAR, CONTEXTUAL, STRUCTURAL, UNKNOWN.

    Must be None during R3.
    Only populated after A3 proves the semantic behavior.
    """

    semantic_classification_status: str
    """Status of semantic classification: 'UNCLASSIFIED', 'CLASSIFIED', 'UNPROVEN'"""

    # ===== PROVENANCE =====
    resolution_status: str
    """How this entry was created: 'RESOLVED_FROM_MAPPING', 'DISCOVERED', etc."""

    mapping_basis: str
    """Evidence chain: e.g., 'R2 semantic_vst3_mapping.json + A1.1 VST3 dump'"""

    # ===== OPTIONAL METADATA =====
    notes: Optional[str] = None
    """Optional developer notes (e.g., 'ambiguous name resolved via R1 audit')"""

    def validate_invariants(self) -> None:
        """Check internal consistency of this record.

        Raises ValueError if invariants violated.
        """
        # Semantic classification must be UNCLASSIFIED during R3
        if self.semantic_mutation_class is not None:
            raise ValueError(
                f"semantic_mutation_class must be None during R3, "
                f"got {self.semantic_mutation_class!r}"
            )

        if self.semantic_classification_status != "UNCLASSIFIED":
            raise ValueError(
                f"semantic_classification_status must be UNCLASSIFIED during R3, "
                f"got {self.semantic_classification_status!r}"
            )

        # VST3 identity must be present and valid
        if not self.vst3_name or not isinstance(self.vst3_name, str):
            raise ValueError(
                f"vst3_name must be non-empty string, got {self.vst3_name!r}"
            )

        if not isinstance(self.vst3_index, int) or self.vst3_index < 0:
            raise ValueError(
                f"vst3_index must be int >= 0, got {self.vst3_index}"
            )

        # Transport metadata must be consistent
        if self.is_boolean and self.is_discrete:
            raise ValueError(
                "parameter cannot be both boolean and discrete"
            )

        if self.is_discrete and (self.num_steps is None or self.num_steps < 2):
            raise ValueError(
                f"discrete parameter must have numSteps >= 2, got {self.num_steps}"
            )

        # Semantic and capability keys must be present
        if not self.semantic_id or not isinstance(self.semantic_id, str):
            raise ValueError(
                f"semantic_id must be non-empty string, got {self.semantic_id!r}"
            )

        if not self.capability_key or not isinstance(self.capability_key, str):
            raise ValueError(
                f"capability_key must be non-empty string, got {self.capability_key!r}"
            )
