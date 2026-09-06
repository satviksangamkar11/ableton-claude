# Serum 2.0.21 v5→v8 Bridge — Proof Plan

**⚠️ This is a historical scoped proof methodology document (v5→v8 bridge era).**

- Not the authoritative roadmap. See [ROADMAP.md](ROADMAP.md) for the authoritative step register.
- This proof plan's technical methodology and findings remain valid for their scoped context.
- Do not treat this as the source of truth for current project direction.

---

## Goal

Determine whether the `.SerumPreset` (v5) → Serum 2.0.21 processor state (v8)
bridge is trustworthy, and specifically resolve the unexplained `IndexError:
invalid vector subscript` crash from the original `ModSlot0-9` transplant test —
without inferring, only by direct evidence.

## Established facts (not to be re-litigated)

- Serum 2.0.21, VST3, Windows. Frozen — never updated/downgraded.
- `.SerumPreset` codec (`serum2/codec.py`) is lossless: 997/997 corpus decodes,
  round-trips exactly.
- `serum2/vst3_state.py`'s `wrap_vc2`/`unwrap_vc2` round-trip functionally
  verified against Serum's own `save_state()` output (audio match, not just
  byte match).
- DawDreamer 0.9.0 hosts Serum 2.0.21 on Windows/Python 3.14; exposes 2,623
  VST3 parameters; direct `set_parameter`/`get_parameter` control is proven
  (`Filter 1 Freq` sweep: 3579 Hz directional centroid shift, exact read-back).
- Serum's mod matrix (source/destination assignment) is **not** host-exposed
  via VST3 — only `Mod N Amount`/`Mod N Out` are automatable. Deep topology
  creation genuinely requires the file/state plane.
- Genuine v8 ground truth obtained via Ableton Live (real host, proper GUI
  message-pump) hosting Serum 2.0.21, loading `PML PD LFO Chords Leave.SerumPreset`,
  saved to `.als`, state extracted from the embedded `<ProcessorState>` hex block.
  This preset's captured v8 state independently confirms non-default content in:
  - `Global0` (kParamMasterVolume, kParamOversampling, ...)
  - `Oscillator0` → `WTOsc0.relativePathToWT` (`/Analog/Basic Shapes.wav`)
  - `VoiceFilter0` (kParamDrive, kParamFreq, kParamReso, kParamType)
  - `ModSlot0` (populated: Oscillator/kParamVolume, amount 42.36, source [6,0])
  - `Env` — **not yet confirmed for this preset**
- v8-populated `ModSlot` schema is structurally identical to v5's: same six
  keys (`destModuleID`, `destModuleParamID`, `destModuleParamName`,
  `destModuleTypeString`, `plainParams`, `source`).
- DawDreamer's `open_editor()` does not reliably route input to Serum's
  custom-painted GUI (confirmed: host param unchanged after a GUI load attempt
  that visually appeared to work). Ableton's real host loop does not have this
  problem.
- Original crash test (`g4i_bisect.py`, `simple_wavetable.SerumPreset`,
  `ModSlot0-9` transplant): **not currently reproducible.**
  - Self-touch (deepcopy + reassign own value, same mechanism): passes.
  - All ten transplanted `ModSlot` values are byte-identical CBOR
    (`a16b706c61696e506172616d736764656661756c74`) between skeleton and
    v5-decoded source. Zero divergence at any level.
  - Shared-object-reference hypothesis: falsified (all 10 decoded objects have
    distinct `id()`; `cbor2.dumps` defaults to `value_sharing=False` anyway).
  - Fresh-process reproduction (Test A) and same-process 6-step replay
    (Test B, matching the original family sequence): **both pass at every
    step**, including the exact position that crashed originally.
  - **New finding**: all six "different" family tests in the replay produced
    byte-identical state (same length, same SHA-256) — meaning
    `simple_wavetable.SerumPreset` is likely near-total-default across
    `Global0`/`Env`/`Oscillator` as well as `ModSlot`, not just `ModSlot`.
    The original bisection's "passes" for those families are therefore
    **contaminated / unverified**, not proven wrong, not proven useless —
    status pending review below.

## Open question

Was the historical bisection infrastructure (`g4i_bisect.py`, `bridge.py`)
actually measuring what we assumed it measured? Until this is settled, no
family's "pass" result (including `ModSlot`'s recent clean replay) can be
trusted as evidence of a working bridge for *non-default* content.

## Proof plan

Dependency chain: **selection correctness → counter correctness →
state-generation equivalence → verified non-default fixtures → Aardvark /
real bridge testing.** Lifecycle experiment runs in parallel (see note).

### 1. `_module_selected` — direct assertions
Call the function directly against known key/prefix pairs (`ModSlot0` vs
`['ModSlot0']`, `ModSlot10` vs `['ModSlot1']`, `Global0` vs `['Global0']`,
etc.) and assert expected true/false. Foundational — if selection is wrong,
every historical family result is contaminated at the source.

### 2. `Filter` presence check
Direct key check: `'Filter' in preset_body` for `simple_wavetable.SerumPreset`.
Resolves whether the persistent `transplanted=0` for `Filter` is a sparse
omission (key absent because it equals default) or a selector bug.

### 3. `transplanted` semantics — bootstrap fixture
Verify against **one** field already trusted from first-conversation decode:
Aardvark's `Env0.kParamAttack = 0.00017601386301917122` — a value specific
enough to not be a default sentinel by coincidence. Compare:
- `reported_transplanted` (the counter)
- `actual_changed_values` (computed diff: does the transplanted key's value
  actually differ from skeleton's?)
- `changed_keys` (which ones)

Resolves whether `transplanted` measures "attempted/matched" or
"actually changed" — these are not the same claim, and the counter has only
ever been used as if it were the second.

### 4. `write_state_file()` equivalence
Run `bridge.write_state_file()` on identical inputs (skeleton +
`simple_wavetable` + `ModSlot0-9`) and compare against the already-known
hash (`b8906e8a42c71a36...`, produced independently by both `g5d` and `g5e`).
Compare:
- length
- SHA-256
- decoded meta
- decoded body

A hash match settles byte equality outright; the decoded comparison is a
diagnostic only needed if it *doesn't* match.

### 5. Function-scope vs. inline-scope lifecycle experiment (parallel to #4)
Does not depend on #4 — reuses already-verified state bytes from `g5d`
rather than newly generated ones, so it can run independently. Rerun the
exact `g5e` scenario but route the load/render step through a separate
`try_load()`-style function (matching `g4i_bisect.py`'s structure exactly)
instead of inline. Tests whether native-object teardown timing between
iterations explains anything, without needing state-generation settled first.

### 6. Verified non-default fixture matrix
Do **not** require one preset with all five families non-default — construct
the matrix from whichever sources actually prove each field:

| Family | Candidate | Status |
|---|---|---|
| `Global0` | `PML PD LFO Chords Leave` (genuine Ableton v8 capture) | confirmed |
| `Oscillator` | `PML PD LFO Chords Leave` (wavetable path) | confirmed |
| `Filter`/`VoiceFilter` | `PML PD LFO Chords Leave` | confirmed |
| `ModSlot` | `PML PD LFO Chords Leave` (ModSlot0) or Aardvark (ModSlot0/1) | confirmed |
| `Env` | — | **check `PML PD LFO Chords Leave` first** before hunting elsewhere |

Likely near-free: one preset (`PML PD LFO Chords Leave`) may satisfy 4-5 of 5
slots already, since its genuine v8 state is already captured and its source
`.SerumPreset` file is already located
(`D:\Producion class\...\PML PD LFO Chords Leave.SerumPreset`).

Each fixture must satisfy the full chain before being trusted:
```
source contains key → bridge selects key → reported as transplanted
→ generated v8 subtree differs from skeleton → state hash changes
```

### 7. Aardvark / real bridge testing
Only after 1-6 pass. First check: does `build_v8_state(aardvark_path,
skeleton, ["ModSlot0"])`'s output hash differ from skeleton's own hash —
*before* any load/render attempt. Then load/render `ModSlot0` alone, per the
original minimal-transplant-matrix intent.

## Status discipline

The historical six-family bisection is **contaminated / unverified**, not
"wrong" and not "proved useless," until steps 1-3 explain why it produced
identical hashes across visibly different test labels.
