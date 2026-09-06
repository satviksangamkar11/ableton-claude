"""16.5.5: Structural value admission.

Answers: can the requested VALUE be structurally written to this target?

This is explicitly separate from:
  - capability admission  (can the field be written AT ALL?)
  - causal admission      (will the write produce a detectable effect?)

Three outcomes:
  ACCEPT  -- evidence positively bounds the requested value inside valid range
  REFUSE  -- evidence positively places the requested value outside valid range
  UNKNOWN -- no complete structural evidence; value cannot be admitted or refused

Dispatch is explicit by allowed_operation from the contract. Currently only
MUTATE_NUMERIC is implemented (numeric clamp bounds from NUMERIC_CLAMP_RANGE
probes). MUTATE_ENUM and MUTATE_STRUCTURED return UNKNOWN until evidence for
those types is collected and structured.

The contract's causal witness value plays NO role in this check.
"""
from dataclasses import dataclass
from typing import Any, List, Optional

from ..evidence.structural import derived_structural_bounds, StructuralProbeResult
from ..evidence.capability_contract import MUTATE_NUMERIC

ACCEPT = "ACCEPT"
REFUSE = "REFUSE"
UNKNOWN = "UNKNOWN"
NOT_CHECKED = "NOT_CHECKED"


@dataclass(frozen=True)
class StructuralAdmissionResult:
    status: str                           # ACCEPT | REFUSE | UNKNOWN
    reason: str
    bounds: Optional[StructuralProbeResult]  # None when status is UNKNOWN with no evidence

    def __bool__(self) -> bool:
        return self.status == ACCEPT


def structural_admit(
    resolved_target,
    requested_value: Any,
    structural_records: List,
) -> StructuralAdmissionResult:
    """Check whether requested_value is structurally admissible for the target.

    Dispatches on resolved_target.contract.allowed_operation:
      MUTATE_NUMERIC -> numeric clamp range check via derived_structural_bounds()
      anything else  -> UNKNOWN (no structural evidence type implemented yet)

    Invariants:
    - A REFUSE from MUTATE_NUMERIC means the value is outside proven [min, max].
    - UNKNOWN is never a positive admission -- callers must not treat it as ACCEPT.
    - The contract's own witness value is never used as a bound; only
      structural_observation records produced by NUMERIC_CLAMP_RANGE probes count.
    """
    contract = resolved_target.contract
    operation = getattr(contract, "allowed_operation", None)

    if operation != MUTATE_NUMERIC:
        return StructuralAdmissionResult(
            UNKNOWN,
            "structural admission not implemented for operation %r "
            "(only MUTATE_NUMERIC supported via numeric clamp bounds)" % operation,
            None,
        )

    mutation_path = contract.scope.get("mutation_target_path")
    if mutation_path is None:
        return StructuralAdmissionResult(
            UNKNOWN,
            "contract has no mutation_target_path in scope -- cannot locate structural records",
            None,
        )

    bounds = derived_structural_bounds(mutation_path, structural_records)

    if bounds is None:
        return StructuralAdmissionResult(
            UNKNOWN,
            "no NUMERIC_CLAMP_RANGE probe records found for path %r" % mutation_path,
            None,
        )

    if not bounds.is_complete():
        return StructuralAdmissionResult(
            UNKNOWN,
            "incomplete structural bounds for %r (min=%s max=%s) -- "
            "cannot safely admit or refuse without both bounds"
            % (mutation_path, bounds.minimum, bounds.maximum),
            bounds,
        )

    if bounds.contains(requested_value):
        return StructuralAdmissionResult(
            ACCEPT,
            "%.6f within proven range [%.6f, %.6f]"
            % (requested_value, bounds.minimum, bounds.maximum),
            bounds,
        )

    return StructuralAdmissionResult(
        REFUSE,
        "%.6f is outside proven structural range [%.6f, %.6f]"
        % (requested_value, bounds.minimum, bounds.maximum),
        bounds,
    )
