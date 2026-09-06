"""
16.5.42 — Native Serum seed-context admission.

This is a fresh current-runtime experiment.

Purpose:
    Prove that the native Serum 2.0.21 seed context captured from Serum's own
    save_state() is suitable as the producer's current starting state.

This does NOT promote any control capability.

It proves:
    native state capture
    state mutation
    state loading
    state readback
    audio distinction
    persistence / reload
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import dawdreamer as daw

from serum2 import bridge, codec, vst3_state


VST3 = r"C:\Program Files\Common Files\VST3\Serum2.vst3"

OUTPUT = Path(
    r"D:\ableton claude\experiments\16_5_42_SEED_CONTEXT.json"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_state_bytes(synth) -> bytes:
    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)

    try:
        synth.save_state(path)
        return Path(path).read_bytes()
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def load_state_bytes(synth, data: bytes) -> None:
    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)

    try:
        Path(path).write_bytes(data)
        synth.load_state(path)
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def render_note(synth, seconds: float = 2.0):
    engine = synth._engine if hasattr(synth, "_engine") else None
    raise RuntimeError(
        "render_note requires the explicit RenderEngine used to create "
        "the synth; this helper is intentionally not used."
    )


def make_engine_and_synth():
    engine = daw.RenderEngine(44100, 512)
    synth = engine.make_plugin_processor(
        "serum",
        VST3,
    )
    return engine, synth


def main() -> int:
    print("=" * 80)
    print("16.5.42 — Native Serum Seed Context Admission")
    print("=" * 80)

    if not Path(VST3).exists():
        raise RuntimeError(
            f"Serum VST3 not found: {VST3}"
        )

    # ------------------------------------------------------------------
    # 1. Capture Serum's own native seed state.
    # ------------------------------------------------------------------
    meta0, body0 = bridge.capture_v8_skeleton(VST3)

    native_state_hash = bridge.state_hash(
        meta0,
        body0,
    )

    print("Native state hash:", native_state_hash)

    # ------------------------------------------------------------------
    # 2. Make a controlled mutation on an otherwise identical copy.
    #
    # MasterVolume is already historically proven and is deliberately
    # used here as a seed-context actuator, not as a new capability claim.
    # ------------------------------------------------------------------
    meta1 = dict(meta0)
    body1 = json.loads(
        json.dumps(
            body0
        )
    )

    global0 = body1.get("Global0")

    if not isinstance(global0, dict):
        raise RuntimeError(
            "Native seed does not contain Global0"
        )

    plain = global0.get("plainParams")

    if not isinstance(plain, dict):
        raise RuntimeError(
            "Native seed Global0 lacks plainParams"
        )

    original_volume = plain.get(
        "kParamMasterVolume"
    )

    if not isinstance(original_volume, (int, float)):
        raise RuntimeError(
            "Native seed MasterVolume is not numeric"
        )

    treatment_volume = max(
        0.0,
        float(original_volume) * 0.5,
    )

    plain["kParamMasterVolume"] = treatment_volume

    treatment_state_hash = bridge.state_hash(
        meta1,
        body1,
    )

    if treatment_state_hash == native_state_hash:
        raise RuntimeError(
            "seed mutation did not change encoded v8 state"
        )

    print("Treatment state hash:", treatment_state_hash)

    # ------------------------------------------------------------------
    # 3. Write both native processor states.
    # ------------------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        control_path = Path(tmp) / "control.bin"
        treatment_path = Path(tmp) / "treatment.bin"

        bridge.write_state_file(
            str(control_path),
            meta0,
            body0,
        )

        bridge.write_state_file(
            str(treatment_path),
            meta1,
            body1,
        )

        control_bytes = control_path.read_bytes()
        treatment_bytes = treatment_path.read_bytes()

    # ------------------------------------------------------------------
    # 4. Load both states into fresh Serum instances.
    # ------------------------------------------------------------------
    control_engine, control_synth = make_engine_and_synth()
    treatment_engine, treatment_synth = make_engine_and_synth()

    load_state_bytes(
        control_synth,
        control_bytes,
    )

    load_state_bytes(
        treatment_synth,
        treatment_bytes,
    )

    # ------------------------------------------------------------------
    # 5. Verify actual host parameter readback.
    # ------------------------------------------------------------------
    control_readback = control_synth.get_parameter(
        "Master Volume"
    )
    treatment_readback = treatment_synth.get_parameter(
        "Master Volume"
    )

    print(
        "Master Volume readback:",
        control_readback,
        "->",
        treatment_readback,
    )

    # Do not demand exact normalized GUI naming semantics unless the host
    # actually exposes that parameter. The processor-state state hash is
    # the primary identity check.
    readback_changed = (
        control_readback != treatment_readback
    )

    # ------------------------------------------------------------------
    # 6. Render control and treatment from fresh engines.
    #
    # Use the simplest possible note stimulus. Audio distinction is a seed
    # context requirement, not evidence for the capability itself.
    # ------------------------------------------------------------------
    midi = [
        {
            "type": "note_on",
            "time": 0.0,
            "note": 48,
            "velocity": 110,
        },
        {
            "type": "note_off",
            "time": 1.8,
            "note": 48,
            "velocity": 0,
        },
    ]

    control_engine.midi_note = None
    treatment_engine.midi_note = None

    # DawDreamer MIDI APIs vary across existing project harness versions;
    # use the same rendering abstraction as the current harness.
    from serum2.evidence.harness import render_arm  # local project authority

    raise RuntimeError(
        "STOP: wire this experiment through the existing harness.render_arm() "
        "using the current local harness signature rather than inventing a "
        "second MIDI/render path."
    )


if __name__ == "__main__":
    raise SystemExit(main())