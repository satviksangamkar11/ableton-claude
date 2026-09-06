from __future__ import annotations

import copy
import hashlib
import json
import pickle
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, r"D:\ableton claude")

ROOT = Path(r"D:\ableton claude")
CORPUS_CACHE = ROOT / "experiments" / "g8e_test3_coexistence_corpus_cache.pkl"
SEED_CONTEXT = ROOT / "experiments" / "16_5_42_SEED_CONTEXT.json"
ARTIFACT = ROOT / "experiments" / "16_5_43_1_CORPUS_ENV_FORENSICS.json"

EXPECTED_CORPUS_HASH = "220cf7ee652d5c4e"


def canonical_hash(obj: Any) -> str:
    data = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_pickle(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


def field_info(plain: dict[str, Any], name: str) -> dict[str, Any]:
    present = name in plain
    value = plain.get(name)
    return {
        "present": present,
        "value": value,
        "python_type": type(value).__name__ if present else None,
    }


def env0_snapshot(body: dict[str, Any]) -> dict[str, Any]:
    env0 = body.get("Env0")

    if not isinstance(env0, dict):
        return {
            "Env0_present": False,
            "Env0_type": type(env0).__name__,
            "plainParams_present": False,
            "plainParams_keys": [],
            "fields": {},
            "Env0_keys": [],
        }

    plain = env0.get("plainParams")
    if not isinstance(plain, dict):
        plain = {}

    names = (
        "kParamAttack",
        "kParamDecay",
        "kParamSustain",
        "kParamRelease",
    )

    return {
        "Env0_present": True,
        "Env0_type": type(env0).__name__,
        "plainParams_present": "plainParams" in env0,
        "plainParams_keys": sorted(plain.keys()),
        "fields": {
            name: field_info(plain, name)
            for name in names
        },
        "Env0_keys": sorted(env0.keys()),
    }


def reconstruct_normalized_corpus() -> tuple[dict[str, Any], str]:
    if not CORPUS_CACHE.exists():
        raise FileNotFoundError(CORPUS_CACHE)

    if not SEED_CONTEXT.exists():
        raise FileNotFoundError(SEED_CONTEXT)

    corpus = load_pickle(CORPUS_CACHE)

    if not isinstance(corpus, dict):
        raise TypeError("Corpus cache root is not a dict.")

    bodies = corpus.get("bodies")
    if not isinstance(bodies, list):
        raise TypeError("Corpus cache has no bodies list.")

    if len(bodies) <= 4:
        raise ValueError("Corpus cache does not contain bodies[4].")

    body = copy.deepcopy(bodies[4])

    seed_context = json.loads(
        SEED_CONTEXT.read_text(encoding="utf-8")
    )

    native_processor = copy.deepcopy(
        seed_context["native"]["processor_component"]
    )
    native_metadata = copy.deepcopy(
        seed_context["native"]["metadata"]
    )

    body["component"] = native_processor

    normalized = {
        "metadata": native_metadata,
        "body": body,
    }

    digest = canonical_hash(normalized)

    return normalized, digest


def compare_env(
    canonical: dict[str, Any],
    corpus: dict[str, Any],
) -> dict[str, Any]:

    comparison: dict[str, Any] = {}

    for name in (
        "kParamAttack",
        "kParamDecay",
        "kParamSustain",
        "kParamRelease",
    ):
        c = canonical["fields"].get(name, {})
        p = corpus["fields"].get(name, {})

        comparison[name] = {
            "canonical": c,
            "corpus": p,
            "equal": (
                c.get("present") == p.get("present")
                and c.get("value") == p.get("value")
                and c.get("python_type") == p.get("python_type")
            ),
        }

    return comparison


def main() -> None:
    print("=" * 80)
    print("16.5.43.1 — CORPUS ENV FORENSICS")
    print("=" * 80)

    normalized, corpus_hash = reconstruct_normalized_corpus()

    print()
    print("NORMALIZED CORPUS")
    print(f"Hash:     {corpus_hash}")
    print(f"Expected: {EXPECTED_CORPUS_HASH}")

    if corpus_hash != EXPECTED_CORPUS_HASH:
        raise RuntimeError(
            "STOP: normalized corpus hash mismatch."
        )

    corpus_body = normalized["body"]

    # ------------------------------------------------------------
    # Build a fresh native Serum state through the existing project
    # infrastructure. This is diagnostic only.
    # ------------------------------------------------------------

    from serum2.evidence.harness import EvidenceHarness

    harness = EvidenceHarness()

    native_state = harness.capture_native_state()

    if not isinstance(native_state, dict):
        raise TypeError(
            "EvidenceHarness.capture_native_state() did not return a dict."
        )

    canonical_env = env0_snapshot(native_state)
    corpus_env = env0_snapshot(corpus_body)

    comparison = compare_env(
        canonical_env,
        corpus_env,
    )

    print()
    print("-" * 80)
    print("CANONICAL ENV0")
    print("-" * 80)
    print(json.dumps(canonical_env, indent=2, default=str))

    print()
    print("-" * 80)
    print("CORPUS ENV0")
    print("-" * 80)
    print(json.dumps(corpus_env, indent=2, default=str))

    print()
    print("-" * 80)
    print("FIELD COMPARISON")
    print("-" * 80)
    print(json.dumps(comparison, indent=2, default=str))

    # ------------------------------------------------------------
    # Diagnostic constructions.
    #
    # These DO NOT create EvidenceRecords.
    # These DO NOT update capabilities.
    # These DO NOT update CurrentCapabilityView.
    # ------------------------------------------------------------

    plain = corpus_body.get("Env0", {}).get("plainParams", {})

    baseline_release = plain.get("kParamRelease")

    arms: dict[str, dict[str, Any]] = {}

    def make_arm(
        name: str,
        *,
        decay: float | None = None,
        sustain: float | None = None,
        release: float | None = None,
        description: str,
    ) -> None:
        body = copy.deepcopy(corpus_body)

        env0 = body.setdefault("Env0", {})
        params = env0.setdefault("plainParams", {})

        if decay is not None:
            params["kParamDecay"] = decay

        if sustain is not None:
            params["kParamSustain"] = sustain

        if release is not None:
            params["kParamRelease"] = release

        arms[name] = {
            "description": description,
            "body": body,
            "env_snapshot": env0_snapshot(body),
            "body_hash": canonical_hash(body),
        }

    make_arm(
        "A_baseline",
        description="Corpus baseline",
    )

    make_arm(
        "B_sustain_0.3_decay_0.02",
        decay=0.02,
        sustain=0.3,
        description="Sustain=0.3, Decay=0.02",
    )

    make_arm(
        "C_sustain_1.0_decay_0.02",
        decay=0.02,
        sustain=1.0,
        description="Explicit Sustain=1.0, Decay=0.02",
    )

    make_arm(
        "D_baseline_release_decay_0.02",
        decay=0.02,
        release=baseline_release,
        description="Baseline Release value, Decay=0.02",
    )

    make_arm(
        "E_release_1.0_decay_0.02",
        decay=0.02,
        release=1.0,
        description="Release=1.0, Decay=0.02",
    )

    print()
    print("-" * 80)
    print("DIAGNOSTIC ARMS")
    print("-" * 80)

    for name, arm in arms.items():
        print()
        print(f"{name}: {arm['description']}")
        print(
            json.dumps(
                arm["env_snapshot"],
                indent=2,
                default=str,
            )
        )

    artifact = {
        "experiment": "16.5.43.1",
        "name": "Corpus Env Forensics",
        "classification": "DIAGNOSTIC",
        "seed": {
            "normalized_hash": corpus_hash,
            "expected_hash": EXPECTED_CORPUS_HASH,
            "hash_match": True,
        },
        "canonical_env0": canonical_env,
        "corpus_env0": corpus_env,
        "comparison": comparison,
        "baseline_release": baseline_release,
        "arms": {
            name: {
                "description": arm["description"],
                "env_snapshot": arm["env_snapshot"],
                "body_hash": arm["body_hash"],
            }
            for name, arm in arms.items()
        },
        "guardrails": {
            "creates_evidence_records": False,
            "creates_claims": False,
            "updates_capabilities": False,
            "updates_current_capability_view": False,
        },
    }

    ARTIFACT.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print(f"Artifact written: {ARTIFACT}")
    print("16.5.43.1 FORENSICS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()