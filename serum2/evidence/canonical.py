"""Typed canonicalization for condition identity.

Condition identity decides whether two experiments are comparable at all.
Get it wrong in either direction and the claim layer breaks:

  too narrow  -> genuine contradictions never collide, go undetected
  too broad   -> unrelated experiments falsely flagged as contradicting

DECISION (explicit, so it is reviewable rather than implicit):
a condition signature covers PREREQUISITES + STIMULUS.

  - prerequisites : distinguishes E2a (Macro7 inactive) from E2b (Macro7 active)
  - stimulus      : two experiments with matching prerequisites but different
                    notes/lengths/render windows are NOT the same condition
  - epoch         : NOT included here; it is a hard provenance boundary handled
                    separately, and evidence never mixes across epochs anyway
  - metric/threshold : NOT included; these are assay criteria, not conditions.
                    Comparisons are made per-metric at the measurement level.
"""
import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Stable, sorted, type-faithful encoding. Rejects values that cannot be
    represented -- a mutation we cannot canonically encode is one we cannot
    reliably compare later."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_fallback)


def _fallback(o):
    raise TypeError(
        "value is not canonically serializable: %r (%s)" % (o, type(o).__name__)
    )


def is_canonically_serializable(obj: Any) -> bool:
    try:
        canonical_json(obj)
        return True
    except (TypeError, ValueError):
        return False


def digest(obj: Any, length: int = 16) -> str:
    return hashlib.sha256(canonical_json(obj).encode()).hexdigest()[:length]


def experiment_condition_signature(prerequisites, baseline_overrides=()) -> dict:
    """Shared experimental context: prerequisites AND baseline_overrides, both
    of which are held IDENTICAL across control/treatment arms.

    Deliberately EXCLUDES stimulus and mutations:
      - stimulus is measurement-level; including it here would make an
        experiment look like a different experimental condition merely because
        an audio measurement changed.
      - mutations are the independent variable; including them would put every
        slot index in its own group and destroy slot-index generalization.
    baseline_overrides ARE included: two experiments sharing the same
    prerequisites but different held-constant sibling fields (e.g. Decay
    tested with Sustain=0 vs Sustain=0.5) are NOT the same experimental
    condition and must not be silently pooled.
    """
    conds = sorted(
        [p.field_path, canonical_json(p.declared_value)] for p in prerequisites
    )
    overrides = sorted(
        [m.target_path, canonical_json(m.value)] for m in baseline_overrides
    )
    payload = {"prerequisites": conds, "baseline_overrides": overrides}
    return {"prerequisites": conds, "baseline_overrides": overrides,
            "hash": digest(payload)}


def measurement_condition_signature(experiment_signature: dict, stimulus) -> dict:
    """Experiment condition + this measurement's stimulus. Two measurements are
    comparable only when these match."""
    stim = None if stimulus is None else {
        k: stimulus[k] for k in sorted(stimulus) if stimulus[k] is not None
    }
    payload = {"experiment": experiment_signature.get("hash"), "stimulus": stim}
    return {"experiment_hash": experiment_signature.get("hash"),
            "stimulus": stim,
            "hash": digest(payload)}


def condition_signature(prerequisites, stimulus) -> dict:
    """DEPRECATED single-level signature. Retained only so historical callers
    fail loudly rather than silently comparing across the two-level model."""
    raise NotImplementedError(
        "use experiment_condition_signature() + measurement_condition_signature()"
    )
