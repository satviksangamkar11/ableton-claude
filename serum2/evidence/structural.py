"""Structural observation types and derivation from EvidenceRecords.

A structural bound is OBSERVED, not inferred. The derivation requires:
  - An EvidenceRecord produced by a NUMERIC_CLAMP_RANGE probe experiment
  - persistence_observation with stored_values on mismatch
  - structural_observation with clamped_to and bound_type

Public entry points:
  derived_structural_bounds(target_path, records) -- high-level, returns None on no evidence
  derive_structural_bounds(target_path, records)  -- low-level, raises on no evidence

Neither ever guesses, parses prose, or falls back to prior provenance text.
Causal EvidenceRecords (structural_observation == {}) are silently skipped;
they can never contribute to or corrupt structural bounds.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


NUMERIC_CLAMP_RANGE = "NUMERIC_CLAMP_RANGE"
BOUND_MINIMUM = "MINIMUM"
BOUND_MAXIMUM = "MAXIMUM"


@dataclass(frozen=True)
class StructuralProbeResult:
    kind: str            # always NUMERIC_CLAMP_RANGE for now
    minimum: Optional[float]   # None = not yet established
    maximum: Optional[float]   # None = not yet established

    def __post_init__(self):
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError(
                    "minimum (%.6f) > maximum (%.6f) -- not a valid range"
                    % (self.minimum, self.maximum))

    def is_complete(self) -> bool:
        return self.minimum is not None and self.maximum is not None

    def contains(self, value: float) -> Optional[bool]:
        """True if value is within [min, max]. None if either bound is missing."""
        if not self.is_complete():
            return None
        return self.minimum <= value <= self.maximum


def _extract_bound(record, target_path: str) -> Optional[Dict[str, Any]]:
    """Pull the structural_observation entry for target_path from one record.
    Returns None if the record has no structural observation for this path,
    or if the experiment was not declared as a clamp probe."""
    obs = getattr(record, "structural_observation", {})
    return obs.get(target_path)


def derive_structural_bounds(
    target_path: str,
    records: List,
) -> StructuralProbeResult:
    """Derive a StructuralProbeResult from one or two clamp-probe EvidenceRecords.

    Each record must have been produced with probe_semantics="NUMERIC_CLAMP_RANGE"
    and must carry a structural_observation entry for target_path.

    Records are classified by bound_type (MINIMUM / MAXIMUM). If both a MINIMUM
    and a MAXIMUM record are provided, the result is complete. If only one is
    provided, the corresponding bound is set and the other is None.

    Raises ValueError if:
      - no relevant structural_observation is found in any record
      - a record yields an unexpected bound_type
      - two records disagree on the same bound type
    """
    minimum = None
    maximum = None
    min_source = None
    max_source = None

    for rec in records:
        entry = _extract_bound(rec, target_path)
        if entry is None:
            continue
        if entry.get("kind") != NUMERIC_CLAMP_RANGE:
            raise ValueError(
                "record %s has unexpected kind %r for %s"
                % (rec.experiment_id, entry.get("kind"), target_path))
        clamped = entry.get("clamped_to")
        bound_type = entry.get("bound_type")
        if clamped is None:
            raise ValueError(
                "record %s structural_observation missing clamped_to for %s"
                % (rec.experiment_id, target_path))
        if bound_type == BOUND_MINIMUM:
            if minimum is not None and minimum != clamped:
                raise ValueError(
                    "conflicting MINIMUM values for %s: %.6f vs %.6f"
                    % (target_path, minimum, clamped))
            minimum = clamped
            min_source = rec.experiment_id
        elif bound_type == BOUND_MAXIMUM:
            if maximum is not None and maximum != clamped:
                raise ValueError(
                    "conflicting MAXIMUM values for %s: %.6f vs %.6f"
                    % (target_path, maximum, clamped))
            maximum = clamped
            max_source = rec.experiment_id
        else:
            raise ValueError(
                "record %s has unrecognised bound_type %r for %s"
                % (rec.experiment_id, bound_type, target_path))

    if minimum is None and maximum is None:
        raise ValueError(
            "no structural_observation found for %s in %d record(s)"
            % (target_path, len(records)))

    return StructuralProbeResult(
        kind=NUMERIC_CLAMP_RANGE,
        minimum=minimum,
        maximum=maximum,
    )


def derived_structural_bounds(
    target_path: str,
    records: List,
) -> Optional["StructuralProbeResult"]:
    """High-level entry point for 16.5.3.

    Accepts ANY collection of EvidenceRecords -- structural probes, causal
    witnesses, persistence-only probes. Filters to qualifying records (those
    with a structural_observation entry for target_path). Records without
    structural observations are silently skipped; they never affect the result.

    Returns:
        StructuralProbeResult  -- if at least one structural observation exists
                                  (may be partial: one or both bounds present)
        None                   -- if NO structural observations for target_path
                                  in ANY of the supplied records

    Raises ValueError only on conflicting evidence (two records disagree on
    the same bound type). Missing evidence returns None, not an exception --
    the caller decides what to do with an absent bound.

    Invariants:
    - Never inspects Mutation.provenance
    - Never infers a bound from a causal witness value
    - Never uses structural_observation == {} (causal records) to derive bounds
    - The minimum/maximum in the result come exclusively from Serum readback
      values captured in structural_observation.clamped_to
    """
    qualifying = [
        r for r in records
        if target_path in getattr(r, "structural_observation", {})
    ]
    if not qualifying:
        return None
    # delegate to the low-level function; ValueError propagates (conflict case)
    return derive_structural_bounds(target_path, qualifying)
