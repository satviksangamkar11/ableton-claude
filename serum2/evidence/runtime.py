"""Runtime condition verification.

The spec DECLARES that a prerequisite is held identical across arms. That is
intent, not fact. This module reads the ACTUAL value back out of both arms as
they were really executed, and reports whether the declaration held.

Without this, a mis-specified experiment silently produces evidence that looks
clean -- exactly the failure this project keeps proving is the dangerous one.
"""
from dataclasses import dataclass, asdict
from typing import Any, List

from .canonical import canonical_json


@dataclass(frozen=True)
class PrerequisiteObservation:
    field_path: str
    declared_value: Any
    control_actual: Any
    treatment_actual: Any
    identical: bool          # did it actually hold identical across arms?
    matches_declared: bool   # did the actual value match what was declared?

    def ok(self, must_hold_identical: bool) -> bool:
        return self.matches_declared and (self.identical or not must_hold_identical)


def _equal(a, b):
    try:
        return canonical_json(a) == canonical_json(b)
    except TypeError:
        return a == b


def read_host_param(synth, name):
    params = synth.get_parameters_description()
    for p in params:
        if p["name"] == name:
            return synth.get_parameter(p["index"])
    raise KeyError("host parameter not found: %r" % (name,))


def observe_prerequisites(prerequisites, control_body, treatment_body,
                          control_synth, treatment_synth) -> List[PrerequisiteObservation]:
    """Read every declared prerequisite back from both executed arms."""
    out = []
    for p in prerequisites:
        if p.field_path.startswith("body:"):
            key = p.field_path.split("body:", 1)[1]
            c_actual = control_body.get(key)
            t_actual = treatment_body.get(key)
        elif p.field_path.startswith("host:"):
            name = p.field_path.split("host:", 1)[1]
            c_actual = read_host_param(control_synth, name) if control_synth else None
            t_actual = read_host_param(treatment_synth, name) if treatment_synth else None
        else:
            raise ValueError("prerequisite field_path must start with 'body:' or 'host:': %r"
                             % (p.field_path,))

        identical = _equal(c_actual, t_actual)
        matches = _equal(t_actual, p.declared_value) if not isinstance(p.declared_value, float) \
            else (t_actual is not None and abs(float(t_actual) - float(p.declared_value)) < 1e-6)
        out.append(PrerequisiteObservation(
            field_path=p.field_path,
            declared_value=p.declared_value,
            control_actual=c_actual,
            treatment_actual=t_actual,
            identical=identical,
            matches_declared=bool(matches),
        ))
    return out


def verification_summary(prerequisites, observations):
    by_path = {o.field_path: o for o in observations}
    failures = []
    for p in prerequisites:
        o = by_path.get(p.field_path)
        if o is None:
            failures.append("%s: not observed" % p.field_path)
            continue
        if not o.matches_declared:
            failures.append("%s: actual %r != declared %r"
                            % (p.field_path, o.treatment_actual, p.declared_value))
        if p.must_hold_identical and not o.identical:
            failures.append("%s: NOT identical across arms (control=%r treatment=%r)"
                            % (p.field_path, o.control_actual, o.treatment_actual))
    return {
        "verified": not failures,
        "failures": failures,
        "observations": [asdict(o) for o in observations],
    }


def observe_prerequisites_from_readings(prerequisites, control_body, treatment_body,
                                        control_host_readings, treatment_host_readings):
    """Same as observe_prerequisites, but host values are supplied as readings
    captured inside the live arm (the engine is gone by the time we get here)."""
    out = []
    for p in prerequisites:
        if p.field_path.startswith("body:"):
            key = p.field_path.split("body:", 1)[1]
            c_actual = control_body.get(key)
            t_actual = treatment_body.get(key)
        elif p.field_path.startswith("host:"):
            c_actual = control_host_readings.get(p.field_path)
            t_actual = treatment_host_readings.get(p.field_path)
        else:
            raise ValueError("prerequisite field_path must start with 'body:' or 'host:': %r"
                             % (p.field_path,))
        identical = _equal(c_actual, t_actual)
        if isinstance(p.declared_value, float) and isinstance(t_actual, (int, float)):
            matches = abs(float(t_actual) - float(p.declared_value)) < 1e-6
        else:
            matches = _equal(t_actual, p.declared_value)
        out.append(PrerequisiteObservation(
            field_path=p.field_path, declared_value=p.declared_value,
            control_actual=c_actual, treatment_actual=t_actual,
            identical=identical, matches_declared=bool(matches)))
    return out
