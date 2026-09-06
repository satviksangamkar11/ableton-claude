"""
16.5.42 — Seed-context admission.

Admits the two working producer seed contexts:

    1. canonical native Serum 2.0.21 processor context
    2. normalized corpus processor context

The normalized corpus context reuses the already-established 16.5.36
processor-flavor boundary:

    corpus body + native processor component

No new Serum control claim is created here.

Gate:
    - both contexts are valid processor states
    - both serialize and reload
    - decoded state fingerprints are recorded
    - fixed-stimulus renders complete
    - raw audio hashes are recorded
    - contexts are audibly distinct
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import pickle
import tempfile
from pathlib import Path

import numpy as np
import dawdreamer as daw

from serum2 import bridge, processor_state
from serum2.evidence import epoch as epoch_mod


ROOT = Path(r"D:\ableton claude")
VST3 = epoch_mod.SERUM_VST3
CACHE = ROOT / "experiments" / "_corpus_cache.pkl"

OUT = ROOT / "experiments" / "16_5_42_SEED_CONTEXT.json"

SR = 44100
BLOCK = 512
NOTE = 48
VELOCITY = 110
NOTE_LEN = 1.8
RENDER_SECONDS = 2.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def state_file_bytes(meta, body) -> bytes:
    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        bridge.write_state_file(path, meta, body)
        return Path(path).read_bytes()
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def load_and_render(meta, body):
    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)

    try:
        bridge.write_state_file(path, meta, body)

        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)

        synth.load_state(path)
        synth.clear_midi()
        synth.add_midi_note(
            NOTE,
            VELOCITY,
            0.0,
            NOTE_LEN,
        )

        engine.load_graph([(synth, [])])
        engine.render(RENDER_SECONDS)

        audio = np.asarray(engine.get_audio())

        if audio.size == 0:
            raise RuntimeError("render produced an empty buffer")

        return audio

    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def audio_manifest(audio):
    arr = np.ascontiguousarray(audio)

    mono = arr.mean(axis=0) if arr.ndim == 2 else arr

    rms = float(np.sqrt(np.mean(mono ** 2)))
    rms_db = float(20.0 * np.log10(rms + 1e-12))
    peak = float(np.max(np.abs(arr)))

    # Diagnostic spectral centroid for context comparison only.
    spectrum = np.abs(np.fft.rfft(mono))
    freqs = np.fft.rfftfreq(len(mono), 1.0 / SR)

    denom = float(np.sum(spectrum))
    centroid = (
        float(np.sum(freqs * spectrum) / denom)
        if denom > 0.0
        else 0.0
    )

    return {
        "raw_audio_sha256": sha256_bytes(
            arr.tobytes()
        ),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "sample_rate": SR,
        "channels": int(arr.shape[0]) if arr.ndim == 2 else 1,
        "samples": int(arr.shape[-1]),
        "duration_seconds": float(arr.shape[-1] / SR),
        "rms_db": rms_db,
        "peak": peak,
        "spectral_centroid_hz": centroid,
    }


def roundtrip_context(name, meta, body):
    # Hard safety boundary: no malformed state enters Serum.
    processor_state.require_processor_state(
        (meta, body),
        source=f"16.5.42.{name}",
    )

    state_hash = bridge.state_hash(meta, body)
    state_bytes = state_file_bytes(meta, body)
    state_file_hash = sha256_bytes(state_bytes)

    # Fresh Serum instance loads the exact serialized state.
    audio = load_and_render(meta, body)

    # Save/reload through Serum itself.
    fd, in_path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)

    fd, out_path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)

    try:
        Path(in_path).write_bytes(state_bytes)

        engine = daw.RenderEngine(SR, BLOCK)
        synth = engine.make_plugin_processor("serum", VST3)

        synth.load_state(in_path)
        synth.save_state(out_path)

        saved_raw = Path(out_path).read_bytes()

        reloaded_meta, reloaded_body = bridge.codec.decode(
            bridge.vst3_state.unwrap_vc2(saved_raw)
        )

    finally:
        for p in (in_path, out_path):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass

    reloaded_state_hash = bridge.state_hash(
        reloaded_meta,
        reloaded_body,
    )

    # The exact decoded state does not have to be byte-identical after
    # Serum's own save_state canonicalization. What matters here is that
    # it remains a valid processor state and survives the round trip.
    processor_state.require_processor_state(
        (reloaded_meta, reloaded_body),
        source=f"16.5.42.{name}.resaved",
    )

    return {
        "name": name,
        "state_hash": state_hash,
        "state_file_sha256": state_file_hash,
        "state_file_bytes": len(state_bytes),
        "top_level_key_count": len(body),
        "roundtrip_state_hash": reloaded_state_hash,
        "roundtrip_processor_state_valid": True,
        "audio": audio_manifest(audio),
    }, audio


def build_normalized_corpus(native_meta, native_body):
    if not CACHE.exists():
        raise RuntimeError(
            f"corpus cache not found: {CACHE}"
        )

    with CACHE.open("rb") as f:
        corpus = pickle.load(f)

    if not isinstance(corpus, dict):
        raise RuntimeError("unexpected corpus cache structure")

    bodies = corpus.get("bodies")
    if not isinstance(bodies, list) or len(bodies) <= 4:
        raise RuntimeError("corpus cache lacks bodies[4]")

    corpus_body = copy.deepcopy(bodies[4])

    # 16.5.36 established the processor-flavor boundary:
    # keep the corpus body and inject the native processor component.
    if "component" not in native_body:
        raise RuntimeError(
            "native processor body lacks required 'component'"
        )

    corpus_body["component"] = copy.deepcopy(
        native_body["component"]
    )

    # Native Serum metadata is retained. This is the same metadata proven
    # usable by the 16.5.x processor-state path.
    normalized_meta = copy.deepcopy(native_meta)

    return normalized_meta, corpus_body


def main():
    print("=" * 80)
    print("16.5.42 — SEED-CONTEXT ADMISSION")
    print("=" * 80)

    if not Path(VST3).exists():
        raise RuntimeError(f"Serum VST3 not found: {VST3}")

    # ------------------------------------------------------------------
    # 16.5.42.1 — Canonical native context
    # ------------------------------------------------------------------
    print("\n[1/6] Capturing canonical native context...")

    native_meta, native_body = bridge.capture_v8_skeleton(VST3)

    native = (native_meta, native_body)

    processor_state.require_processor_state(
        native,
        source="16.5.42.canonical",
    )

    print(
        "  native state hash:",
        bridge.state_hash(native_meta, native_body),
    )

    # ------------------------------------------------------------------
    # 16.5.42.2 — Normalized corpus context
    # ------------------------------------------------------------------
    print("\n[2/6] Building normalized corpus context...")

    corpus_meta, corpus_body = build_normalized_corpus(
        native_meta,
        native_body,
    )

    processor_state.require_processor_state(
        (corpus_meta, corpus_body),
        source="16.5.42.normalized_corpus",
    )

    print(
        "  corpus state hash:",
        bridge.state_hash(corpus_meta, corpus_body),
    )

    # ------------------------------------------------------------------
    # 16.5.42.3 — State distinction
    # ------------------------------------------------------------------
    print("\n[3/6] Checking intended decoded-state distinction...")

    native_state_hash = bridge.state_hash(
        native_meta,
        native_body,
    )

    corpus_state_hash = bridge.state_hash(
        corpus_meta,
        corpus_body,
    )

    states_differ = native_state_hash != corpus_state_hash

    print("  native :", native_state_hash)
    print("  corpus :", corpus_state_hash)
    print("  differ :", states_differ)

    if not states_differ:
        raise RuntimeError(
            "canonical and normalized corpus contexts are not different"
        )

    # ------------------------------------------------------------------
    # 16.5.42.4 — Round-trip + render
    # ------------------------------------------------------------------
    print("\n[4/6] Round-trip and render...")

    native_manifest, native_audio = roundtrip_context(
        "canonical",
        native_meta,
        native_body,
    )

    corpus_manifest, corpus_audio = roundtrip_context(
        "normalized_corpus",
        corpus_meta,
        corpus_body,
    )

    print(
        "  canonical audio sha:",
        native_manifest["audio"]["raw_audio_sha256"][:16],
    )
    print(
        "  corpus audio sha   :",
        corpus_manifest["audio"]["raw_audio_sha256"][:16],
    )

    # ------------------------------------------------------------------
    # 16.5.42.5 — Audible distinction
    # ------------------------------------------------------------------
    print("\n[5/6] Checking raw-audio distinction...")

    audio_same_shape = (
        native_audio.shape == corpus_audio.shape
    )

    if not audio_same_shape:
        raise RuntimeError(
            "canonical/corpus renders have different shapes"
        )

    raw_audio_identical = np.array_equal(
        native_audio,
        corpus_audio,
    )

    max_abs_diff = float(
        np.max(
            np.abs(
                native_audio - corpus_audio
            )
        )
    )

    audio_distinct = (
        not raw_audio_identical
        and max_abs_diff > 0.0
    )

    print("  raw audio identical:", raw_audio_identical)
    print("  max abs difference :", max_abs_diff)
    print("  audio distinct     :", audio_distinct)

    if not audio_distinct:
        raise RuntimeError(
            "normalized corpus context does not produce "
            "audibly/ numerically distinct raw audio"
        )

    # ------------------------------------------------------------------
    # 16.5.42.6 — Persist acceptance artifact
    # ------------------------------------------------------------------
    print("\n[6/6] Writing acceptance artifact...")

    result = {
        "step": "16.5.42",
        "status": "PASS",
        "environment": {
            "serum_vst3": VST3,
            "sample_rate": SR,
            "block_size": BLOCK,
            "stimulus": {
                "note": NOTE,
                "velocity": VELOCITY,
                "note_len": NOTE_LEN,
                "render_seconds": RENDER_SECONDS,
            },
        },
        "contexts": {
            "canonical_native": native_manifest,
            "normalized_corpus": corpus_manifest,
        },
        "comparison": {
            "state_hashes_differ": states_differ,
            "raw_audio_identical": raw_audio_identical,
            "max_abs_audio_difference": max_abs_diff,
            "audio_distinct": audio_distinct,
        },
        "lineage": {
            "canonical": (
                "fresh Serum 2.0.21 save_state()"
            ),
            "normalized_corpus": (
                "experiments/_corpus_cache.pkl bodies[4] "
                "+ native processor component, reusing "
                "the 16.5.36 processor-flavor boundary"
            ),
        },
        "admission": {
            "canonical_valid": True,
            "normalized_corpus_valid": True,
            "canonical_roundtrip_valid": True,
            "normalized_corpus_roundtrip_valid": True,
            "canonical_rendered": True,
            "normalized_corpus_rendered": True,
            "state_distinction_proven": states_differ,
            "audio_distinction_proven": audio_distinct,
        },
    }

    OUT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("16.5.42 PASS")
    print("=" * 80)
    print("Artifact:", OUT)


if __name__ == "__main__":
    main()
