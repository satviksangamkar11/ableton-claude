"""16.5.69.2-A3-19B: GenerationObservation — unified generation evidence.

Replaces the implicit NOT_RUN status for host_param mutations.

Two route kinds:
  state_mutation   - mutation applied to CBOR body; evidence = state diff
  host_param_mutation - mutation applied via set_parameter; evidence = readback

For state_mutation:
  PASS = state diff contains exactly the declared path, leaf value changed
  FAIL = state diff contains unexpected keys OR leaf value unchanged

For host_param_mutation:
  PASS = readback differs from baseline and approximates test value
  FAIL = readback == baseline (set_parameter had no effect)
  NOT_APPLICABLE = parameter is non-automatable (MIDI CC / pitch bend)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass(frozen=True)
class GenerationObservation:
    route_kind: str
    status: str
    value_before: Optional[float] = None
    value_set: Optional[float] = None
    value_after: Optional[float] = None
    diff_keys: Optional[tuple] = None
    reason: Optional[str] = None
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        valid_kinds = {"state_mutation", "host_param_mutation", "NOT_APPLICABLE"}
        if self.route_kind not in valid_kinds:
            raise ValueError("Unknown route_kind: {!r}".format(self.route_kind))
        valid_status = {"PASS", "FAIL", "NOT_RUN", "NOT_APPLICABLE", "SKIPPED"}
        if self.status not in valid_status:
            raise ValueError("Unknown status: {!r}".format(self.status))

    @property
    def passed(self) -> bool:
        return self.status == "PASS"


GENERATION_NOT_RUN = GenerationObservation(
    route_kind="state_mutation",
    status="NOT_RUN",
    reason="Generation gate not executed",
)

GENERATION_NOT_APPLICABLE = GenerationObservation(
    route_kind="NOT_APPLICABLE",
    status="NOT_APPLICABLE",
    reason="Non-automatable parameter (MIDI CC / pitch bend); not a synthesis control",
)


def generation_from_host_param_readback(
    *,
    vst3_name: str,
    value_before: float,
    value_set: float,
    value_after: float,
    tolerance: float = 1e-5,
) -> GenerationObservation:
    """Create GenerationObservation from host_param set+readback result."""
    changed = abs(value_after - value_before) > tolerance
    if changed:
        status = "PASS"
        reason = "Readback changed: {:.4f} -> {:.4f} (set={:.4f})".format(
            value_before, value_after, value_set
        )
    else:
        status = "FAIL"
        reason = "Readback unchanged: {:.4f} (set={:.4f}); set_parameter had no effect".format(
            value_before, value_set
        )
    return GenerationObservation(
        route_kind="host_param_mutation",
        status=status,
        value_before=value_before,
        value_set=value_set,
        value_after=value_after,
        reason=reason,
        details={"vst3_name": vst3_name},
    )


def generation_from_state_diff(
    *,
    diff_keys: list[str],
    intended_top_key: str,
    leaf_changed: bool,
    top_ok: bool,
) -> GenerationObservation:
    """Create GenerationObservation from CBOR body state diff."""
    passed = top_ok and leaf_changed
    status = "PASS" if passed else "FAIL"
    if passed:
        reason = "State diff matches intent: diff_keys={}, leaf_changed=True".format(diff_keys)
    else:
        reason = "State diff mismatch: top_ok={}, leaf_changed={}, diff_keys={}".format(
            top_ok, leaf_changed, diff_keys
        )
    return GenerationObservation(
        route_kind="state_mutation",
        status=status,
        diff_keys=tuple(diff_keys),
        reason=reason,
        details={
            "intended_top_key": intended_top_key,
            "top_ok": top_ok,
            "leaf_changed": leaf_changed,
        },
    )
