"""
16.5.41 — Claim / Capability semantic separation.

This module defines semantic interpretation across the evidence stack.

IMPORTANT
---------
This module does not mutate:
    EvidenceRecord
    ClaimGroup
    CapabilityContract

It only computes a read-only semantic view.

Layers
------
Evidence disposition
    What may be admitted from the evidence archive?

Claim status
    What did the ClaimGroup itself establish?

Capability status
    What does the CapabilityContract say this target established?

Current-runtime candidate
    Can this contract be considered for current-runtime qualification?

Current-runtime VERIFIED
    NOT produced here.
    That belongs to 16.5.42 / 16.5.43 after explicit current-runtime
    evidence exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Tuple

from .capability_contract import (
    CAUSAL_VERIFIED,
    STRUCTURAL_ONLY,
    NEGATIVE_EVIDENCE,
    UNSUPPORTED,
    BLOCKED_CONTRADICTED,
)
from .disposition import (
    VALID,
    HISTORICAL_VALID,
    CONTEXT_INCOMPLETE,
    INVALIDATED_ACTUATOR,
)


# ---------------------------------------------------------------------------
# Explicit semantic layer names
# ---------------------------------------------------------------------------

EVIDENCE_DISPOSITION = "evidence_disposition"
CLAIM_STATUS = "claim_status"
CAPABILITY_STATUS = "capability_status"
CURRENT_RUNTIME_STATUS = "current_runtime_status"


# ---------------------------------------------------------------------------
# Current-runtime states
# ---------------------------------------------------------------------------

CURRENT_RUNTIME_NOT_ASSESSED = "CURRENT_RUNTIME_NOT_ASSESSED"
CURRENT_RUNTIME_REQUALIFICATION_REQUIRED = (
    "CURRENT_RUNTIME_REQUALIFICATION_REQUIRED"
)
CURRENT_RUNTIME_CANDIDATE = "CURRENT_RUNTIME_CANDIDATE"


# ---------------------------------------------------------------------------
# Capability semantic classes
# ---------------------------------------------------------------------------

SEMANTIC_REJECTED = "REJECTED"
SEMANTIC_STRUCTURAL = "STRUCTURAL"
SEMANTIC_CAUSAL = "CAUSAL"


@dataclass(frozen=True)
class CapabilitySemanticView:
    """
    Read-only semantic projection.

    historical_admissible:
        Whether historical evidence dispositions permit the historical
        contract to remain usable.

    current_runtime_candidate:
        Whether there is enough admissible evidence to place this target into
        the current-runtime requalification queue.

    current_runtime_status:
        Never means "CURRENT_RUNTIME_VERIFIED" in 16.5.41.
    """

    contract_key: str
    target: str

    capability_status: str

    admissible_evidence: Tuple[str, ...]
    historical_only_evidence: Tuple[str, ...]
    blocked_evidence: Tuple[str, ...]

    historical_admissible: bool
    current_runtime_candidate: bool
    current_runtime_status: str

    semantic_class: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_key": self.contract_key,
            "target": self.target,
            "capability_status": self.capability_status,
            "admissible_evidence": list(self.admissible_evidence),
            "historical_only_evidence": list(self.historical_only_evidence),
            "blocked_evidence": list(self.blocked_evidence),
            "historical_admissible": self.historical_admissible,
            "current_runtime_candidate": self.current_runtime_candidate,
            "current_runtime_status": self.current_runtime_status,
            "semantic_class": self.semantic_class,
            "reason": self.reason,
        }


def _supporting_evidence(contract: Any) -> Tuple[str, ...]:
    provenance = getattr(contract, "provenance", {}) or {}
    return tuple(
        str(x)
        for x in provenance.get("supporting_evidence", ())
    )


def _contract_is_usable(contract: Any) -> bool:
    status = getattr(contract, "status", None)

    return status not in {
        NEGATIVE_EVIDENCE,
        UNSUPPORTED,
        BLOCKED_CONTRADICTED,
    }


def _semantic_class(status: str) -> str:
    if status == CAUSAL_VERIFIED:
        return SEMANTIC_CAUSAL

    if status == STRUCTURAL_ONLY:
        return SEMANTIC_STRUCTURAL

    return SEMANTIC_REJECTED


def evaluate_contract_semantics(
    contract_key: str,
    contract: Any,
    dispositions: Mapping[str, str],
) -> CapabilitySemanticView:
    """
    Evaluate one CapabilityContract against external evidence dispositions.

    Rules
    -----
    1. Capability status remains owned by the CapabilityContract.
       Evidence disposition cannot overwrite it.

    2. INVALIDATED_ACTUATOR and CONTEXT_INCOMPLETE evidence cannot establish
       historical admissibility.

    3. HISTORICAL_VALID evidence may support historical usage, but it cannot
       make the capability current-runtime verified.

    4. At least one VALID supporting record is required before the contract can
       become a current-runtime candidate.

    5. CURRENT_RUNTIME_VERIFIED is impossible here by construction.
       16.5.42 / 16.5.43 must supply that qualification.
    """
    status = str(getattr(contract, "status", "UNKNOWN"))
    supporting = _supporting_evidence(contract)

    admissible = []
    historical_only = []
    blocked = []

    for evidence_id in supporting:
        disposition = dispositions.get(
            evidence_id
        )

        if disposition == VALID:
            admissible.append(evidence_id)
        elif disposition == HISTORICAL_VALID:
            historical_only.append(evidence_id)
        elif disposition in {
            CONTEXT_INCOMPLETE,
            INVALIDATED_ACTUATOR,
        }:
            blocked.append(evidence_id)
        else:
            # No disposition is equivalent to "not safe to use".
            blocked.append(evidence_id)

    contract_usable = _contract_is_usable(contract)

    historical_admissible = (
        contract_usable
        and bool(admissible or historical_only)
        and not blocked
    )

    # A current candidate needs at least one exact VALID evidence source.
    # It still requires explicit current-runtime requalification.
    current_candidate = (
        contract_usable
        and bool(admissible)
        and not blocked
    )

    if current_candidate:
        runtime_status = CURRENT_RUNTIME_CANDIDATE
        reason = (
            "contract is semantically usable and has VALID supporting "
            "evidence, but current-runtime verification is not established"
        )
    elif historical_admissible:
        runtime_status = CURRENT_RUNTIME_REQUALIFICATION_REQUIRED
        reason = (
            "historical evidence is admissible, but no VALID supporting "
            "evidence establishes a current-runtime candidate"
        )
    elif not contract_usable:
        runtime_status = CURRENT_RUNTIME_REQUALIFICATION_REQUIRED
        reason = (
            "contract status itself is not usable for producer capability "
            "semantics"
        )
    elif blocked:
        runtime_status = CURRENT_RUNTIME_REQUALIFICATION_REQUIRED
        reason = (
            "one or more supporting evidence records are blocked or "
            "undispositioned"
        )
    else:
        runtime_status = CURRENT_RUNTIME_REQUALIFICATION_REQUIRED
        reason = "insufficient admissible supporting evidence"

    return CapabilitySemanticView(
        contract_key=str(contract_key),
        target=str(getattr(contract, "target", "<unknown>")),
        capability_status=status,
        admissible_evidence=tuple(admissible),
        historical_only_evidence=tuple(historical_only),
        blocked_evidence=tuple(blocked),
        historical_admissible=historical_admissible,
        current_runtime_candidate=current_candidate,
        current_runtime_status=runtime_status,
        semantic_class=_semantic_class(status),
        reason=reason,
    )


def evaluate_all_contracts(
    contracts: Mapping[Any, Any],
    dispositions: Mapping[str, str],
) -> dict[str, CapabilitySemanticView]:
    """
    Evaluate every contract without changing the contracts.
    """
    result: dict[str, CapabilitySemanticView] = {}

    for key, contract in contracts.items():
        key_string = str(key)

        result[key_string] = evaluate_contract_semantics(
            key_string,
            contract,
            dispositions,
        )

    return result


def semantic_summary(
    views: Mapping[str, CapabilitySemanticView],
) -> dict[str, Any]:
    counts = {
        "historical_admissible": 0,
        "current_runtime_candidates": 0,
        "current_runtime_requalification_required": 0,
    }

    status_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}

    for view in views.values():
        if view.historical_admissible:
            counts["historical_admissible"] += 1

        if view.current_runtime_candidate:
            counts["current_runtime_candidates"] += 1

        if (
            view.current_runtime_status
            == CURRENT_RUNTIME_REQUALIFICATION_REQUIRED
        ):
            counts["current_runtime_requalification_required"] += 1

        status_counts[view.capability_status] = (
            status_counts.get(view.capability_status, 0) + 1
        )

        class_counts[view.semantic_class] = (
            class_counts.get(view.semantic_class, 0) + 1
        )

    return {
        "contract_count": len(views),
        "counts": counts,
        "capability_status_counts": status_counts,
        "semantic_class_counts": class_counts,
        "current_runtime_verified_contracts": 0,
        "note": (
            "16.5.41 intentionally cannot establish "
            "CURRENT_RUNTIME_VERIFIED"
        ),
    }