"""MeasurementDefinition: WHAT was measured and HOW.

Identity is the measurement KERNEL (audio -> scalar), never the render wrapper
that historically hosted it -- wrappers are execution plumbing, covered by
ExecutionEpoch. Two copy-pasted wrappers around the same kernel must remain
comparable; two different algorithms sharing a metric name must not.

Deliberately EXCLUDES threshold and expected_direction: those are decision
policy (ClaimDefinition), not measurement identity. Changing a threshold
re-derives verdicts without invalidating a single observation.
"""
import ast
import hashlib
import importlib
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

from .canonical import digest

KERNEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kernels")
_STDLIB_PREFIXES = ("os", "sys", "math", "json", "hashlib", "dataclasses",
                    "typing", "ast", "importlib", "struct", "re", "copy",
                    "tempfile", "glob", "platform", "collections", "itertools")


def artifact_hash(path: str) -> str:
    """Content hash of the kernel artifact file itself."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _third_party_imports(path: str, seen=None):
    """Transitive import closure, computed automatically -- no hand-maintained
    'actually used' list, which would silently rot as helpers gain imports."""
    if seen is None:
        seen = set()
    src = open(path, "r", encoding="utf8").read()
    tree = ast.parse(src)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                found.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
            elif node.level > 0:
                # relative import within our package -- recurse
                base = os.path.dirname(path)
                for a in node.names:
                    cand = os.path.join(base, a.name + ".py")
                    if os.path.exists(cand) and cand not in seen:
                        seen.add(cand)
                        found |= _third_party_imports(cand, seen)
    return {m for m in found if not m.startswith(_STDLIB_PREFIXES)}


def scoped_dependency_lock(path: str) -> Dict[str, Any]:
    """Versions of exactly the third-party packages reachable from this kernel.
    Scoped so an unrelated package upgrade does not orphan the measurement."""
    mods = sorted(_third_party_imports(path))
    versions = {}
    for m in mods:
        try:
            versions[m] = getattr(importlib.import_module(m), "__version__", "unknown")
        except Exception as e:
            versions[m] = "<unavailable: %s>" % type(e).__name__
    return {"packages": versions,
            "lock_id": digest({"packages": versions}, 12)}


@dataclass(frozen=True)
class MeasurementTargetRef:
    field_path: str
    module: Optional[str] = None
    parameter: Optional[str] = None


@dataclass(frozen=True)
class MeasurementDefinition:
    metric_name: str
    kernel_artifact: str                 # filename under kernels/
    implementation_artifact_hash: str
    target: MeasurementTargetRef
    runtime_dependency_lock: Dict[str, Any]

    @property
    def measurement_definition_id(self) -> str:
        return "%s:%s" % (self.metric_name, digest({
            "metric_name": self.metric_name,
            "implementation_artifact_hash": self.implementation_artifact_hash,
            "target": asdict(self.target),
            "lock_id": self.runtime_dependency_lock.get("lock_id"),
        }, 12))

    def to_dict(self):
        d = asdict(self)
        d["measurement_definition_id"] = self.measurement_definition_id
        return d


def define(metric_name: str, kernel_artifact: str, target: MeasurementTargetRef):
    path = os.path.join(KERNEL_DIR, kernel_artifact)
    if not os.path.exists(path):
        raise FileNotFoundError("kernel artifact not archived: %s" % path)
    return MeasurementDefinition(
        metric_name=metric_name,
        kernel_artifact=kernel_artifact,
        implementation_artifact_hash=artifact_hash(path),
        target=target,
        runtime_dependency_lock=scoped_dependency_lock(path),
    )


def load_kernel(defn: MeasurementDefinition):
    """Re-executable: a definition can be run again from its archived artifact."""
    mod = importlib.import_module(
        "serum2.evidence.kernels.%s" % defn.kernel_artifact[:-3])
    return mod.kernel
