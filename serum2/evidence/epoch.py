"""Evidence epoch: provenance boundary.

Any change to the Serum binary, our harness source, dependency versions, or
the measurement environment mints a NEW epoch. Evidence never mixes across
epochs -- this is the guard against silently comparing results measured under
different conditions.
"""
import hashlib, json, os, platform, sys, glob

SERUM_VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"
SERUM_BINARY = os.path.join(SERUM_VST3, "Contents", "x86_64-win", "Serum2.vst3")
HARNESS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def serum_binary_sha256():
    return _sha256_file(SERUM_BINARY)


# Code whose changes have DIFFERENT blast radii -- provenance is compositional,
# not one global epoch:
#   EXECUTION  -> how state is built/loaded/rendered   -> gates observations
#   MEASUREMENT-> how a scalar is derived from audio   -> MeasurementDefinition
#   DERIVATION -> claim/evidence interpretation        -> NOT an identity at all
EXECUTION_MODULES = ("bridge.py", "codec.py", "vst3_state.py",
                     "evidence/harness.py", "evidence/runtime.py",
                     "evidence/spec.py", "evidence/epoch.py")
MEASUREMENT_PATHS = ("evidence/measure.py", "evidence/kernels")
DERIVATION_MODULES = ("evidence/claim.py", "evidence/record.py",
                      "evidence/canonical.py", "evidence/measurement.py",
                      "evidence/fixtures.py")


def execution_harness_revision():
    """Hash of EXECUTION code only.

    Measurement kernels are excluded: changing a metric must not orphan the
    Serum knowledge base, it must only separate claims depending on that metric.
    Derivation code is excluded entirely -- it is pure recomputation, so a claim
    engine bugfix should revise conclusions, never invalidate observations.
    """
    h = hashlib.sha256()
    for rel in EXECUTION_MODULES:
        path = os.path.join(HARNESS_ROOT, rel.replace("/", os.sep))
        if os.path.exists(path):
            h.update(rel.encode())
            h.update(_sha256_file(path).encode())
    return h.hexdigest()


def derivation_revision():
    """Forensic metadata only -- records which engine version produced a report.
    Never participates in any comparability decision."""
    h = hashlib.sha256()
    for rel in DERIVATION_MODULES:
        path = os.path.join(HARNESS_ROOT, rel.replace("/", os.sep))
        if os.path.exists(path):
            h.update(rel.encode())
            h.update(_sha256_file(path).encode())
    return h.hexdigest()[:16]


def dependency_lock():
    versions = {}
    for mod in ("dawdreamer", "cbor2", "zstandard", "numpy"):
        try:
            m = __import__(mod)
            versions[mod] = getattr(m, "__version__", "unknown")
        except Exception as e:
            versions[mod] = f"<unavailable: {type(e).__name__}>"
    versions["python"] = sys.version.split()[0]
    return versions


def environment_fingerprint(sample_rate=44100, block_size=512):
    """Captured broadly rather than curated -- this project's repeated lesson
    is that the factor which mattered was not on anyone's list beforehand."""
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_build": " ".join(platform.python_build()),
        "sample_rate": sample_rate,
        "block_size": block_size,
    }


def current_epoch(sample_rate=44100, block_size=512):
    """ExecutionEpoch: Serum binary + execution harness + environment.
    Measurement identity lives in MeasurementDefinition, NOT here."""
    identity = {
        "serum_binary_sha256": serum_binary_sha256(),
        "execution_harness_revision": execution_harness_revision(),
        "dependency_lock": dependency_lock(),
        "environment_fingerprint": environment_fingerprint(sample_rate, block_size),
    }
    blob = json.dumps(identity, sort_keys=True).encode()
    identity["execution_epoch_id"] = hashlib.sha256(blob).hexdigest()[:16]
    identity["evidence_epoch_id"] = identity["execution_epoch_id"]   # back-compat
    identity["derivation_revision"] = derivation_revision()          # forensic only
    return identity
