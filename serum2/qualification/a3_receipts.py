"""16.5.69.2 — A3 Qualification Receipt Schema.

A MutationReceipt is a qualification/interpretation artifact derived from an
existing EvidenceRecord.

IMPORTANT ARCHITECTURAL RULES
-----------------------------
1. EvidenceRecord remains the authoritative observation source.
2. MutationReceipt contains qualification interpretation only.
3. This module performs no Serum/DawDreamer execution.
4. This module performs no measurement.
5. This module performs no target resolution.
6. No collapsed "CONTROL_CAPABLE" boolean is stored here.
7. P1/P2/P3 remain independently representable.
8. Restoration remains NOT_RUN until EvidenceRecord supports it explicitly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# A3 gate status vocabulary
# ---------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"
INCONCLUSIVE = "INCONCLUSIVE"
NOT_RUN = "NOT_RUN"
UNKNOWN = "UNKNOWN"

VALID_GATE_STATUSES = frozenset(
    {
        PASS,
        FAIL,
        INCONCLUSIVE,
        NOT_RUN,
        UNKNOWN,
    }
)


# ---------------------------------------------------------------------------
# GateResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GateResult:
    """Qualification result for exactly one gate.

    `status` is an interpretation of already-recorded evidence.
    `reason` and `details` explain the interpretation.
    `evidence_ref` identifies the underlying EvidenceRecord or artifact.
    """

    status: str
    reason: Optional[str] = None
    evidence_ref: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_GATE_STATUSES:
            raise ValueError(
                f"Invalid A3 gate status: {self.status!r}. "
                f"Expected one of {sorted(VALID_GATE_STATUSES)}."
            )


# ---------------------------------------------------------------------------
# PersistenceResult
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PersistenceResult:
    """Persistence qualification at each independently tested lifecycle.

    IMPORTANT:
    The current EvidenceRecord does not yet establish P1/P2/P3 separately.
    Therefore a3_evaluator.py must leave these NOT_RUN until explicit lifecycle
    evidence exists.

    `overall` may reflect an existing aggregate persistence observation, but it
    must never be used to fabricate P1/P2/P3.
    """

    p1_same_engine: GateResult
    p2_new_instance: GateResult
    p3_fresh_process: GateResult

    overall: GateResult


# ---------------------------------------------------------------------------
# MutationReceipt
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MutationReceipt:
    """A3 qualification summary for one semantic target/test execution.

    This is NOT an EvidenceRecord replacement.

    EvidenceRecord:
        observed what happened.

    MutationReceipt:
        interprets those observations into qualification-level results.
    """

    # -----------------------------------------------------------------------
    # Experiment / target identity
    # -----------------------------------------------------------------------

    experiment_id: str

    semantic_id: str
    capability_key: str

    # Qualified VST3 identity from RESOLVED_TARGET_REGISTRY.
    vst3_name: str
    vst3_index: int

    # -----------------------------------------------------------------------
    # Fine-grained gates
    # -----------------------------------------------------------------------

    generation: GateResult

    persistence: PersistenceResult

    behavior: GateResult

    collateral: GateResult

    restoration: GateResult

    # -----------------------------------------------------------------------
    # Evidence linkage
    # -----------------------------------------------------------------------

    evidence_record_id: Optional[str] = None

    # -----------------------------------------------------------------------
    # Narrow derived qualification claims
    #
    # These are intentionally not a single "CONTROL_CAPABLE" flag.
    # -----------------------------------------------------------------------

    transport_mutable: bool = False
    generation_verified: bool = False

    persistent_p1: bool = False
    persistent_p2: bool = False
    persistent_p3: bool = False

    collateral_safe: bool = False
    behavior_verified: bool = False

    # -----------------------------------------------------------------------
    # Notes
    # -----------------------------------------------------------------------

    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.experiment_id:
            raise ValueError("experiment_id must not be empty")

        if not self.semantic_id:
            raise ValueError("semantic_id must not be empty")

        if not self.capability_key:
            raise ValueError("capability_key must not be empty")

        if not self.vst3_name:
            raise ValueError("vst3_name must not be empty")

        if not isinstance(self.vst3_index, int):
            raise TypeError(
                f"vst3_index must be int, got {type(self.vst3_index).__name__}"
            )

        if self.vst3_index < 0:
            raise ValueError("vst3_index must be >= 0")

    # -----------------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)

    def to_json_dict(self) -> dict[str, Any]:
        """Alias kept explicit for callers that expect JSON-oriented naming."""

        return self.to_dict()


# ---------------------------------------------------------------------------
# Small schema helpers
# ---------------------------------------------------------------------------

def gate_not_run(
    reason: str,
    *,
    evidence_ref: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> GateResult:
    """Construct a deliberate NOT_RUN result."""

    return GateResult(
        status=NOT_RUN,
        reason=reason,
        evidence_ref=evidence_ref,
        details=details or {},
    )


def gate_pass(
    reason: str,
    *,
    evidence_ref: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> GateResult:
    """Construct a PASS result."""

    return GateResult(
        status=PASS,
        reason=reason,
        evidence_ref=evidence_ref,
        details=details or {},
    )


def gate_fail(
    reason: str,
    *,
    evidence_ref: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> GateResult:
    """Construct a FAIL result."""

    return GateResult(
        status=FAIL,
        reason=reason,
        evidence_ref=evidence_ref,
        details=details or {},
    )


def gate_inconclusive(
    reason: str,
    *,
    evidence_ref: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> GateResult:
    """Construct an INCONCLUSIVE result."""

    return GateResult(
        status=INCONCLUSIVE,
        reason=reason,
        evidence_ref=evidence_ref,
        details=details or {},
    )


def gate_unknown(
    reason: str,
    *,
    evidence_ref: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
) -> GateResult:
    """Construct an UNKNOWN result."""

    return GateResult(
        status=UNKNOWN,
        reason=reason,
        evidence_ref=evidence_ref,
        details=details or {},
    )
