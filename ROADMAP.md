# ROADMAP — Authoritative Step Register

**This file is the only authoritative step register for the project.**

- `CLAUDE.md` — permanent policy. Never contains step numbers.
- `ROADMAP.md` — this file. Authoritative execution register and step numbering.
- `GATES.md` — scoped gate/evidence documentation. **Historical.** Not a roadmap.
- `PROOF_PLAN.md` — scoped proof methodology (v5→v8 bridge). **Historical.** Not a roadmap.

Established at 16.5.56 after discovering that step numbers 16.5.44–16.5.55 had been
reassigned to different work than the frozen plan reserved them for, with no document
in the repository recording the frozen plan at all.

---

## Objective (unchanged)

Build a trustworthy AI music producer for **Serum 2.0.21** under **Ableton Live 12.3
Suite** that can understand, construct, verify, expand its Serum-specific knowledge,
optimize, and produce music, with all Serum-specific behaviour grounded in an auditable
evidence chain.

**Finish line:** `16.6` — a 124 BPM, A-minor, 16-bar Ableton arrangement with three
Serum roles (bass, pad, lead) across four sections, rendered to master and stems,
objectively verified, fully audit-traceable, and approved by human audition.

---

## State machine

| State | Meaning |
|---|---|
| `FROZEN` | Number, goal and gate are fixed. Implementation may not be reshaped. |
| `PROVISIONAL` | Goal is fixed; number and implementation may be reshaped once its dependency gate clears. |
| `RESERVED` | Conditional branch. Executes only if a named condition holds. |
| `ACTIVE` | Currently being executed. |
| `BLOCKED` | Dependency gate failed. Reason recorded. |
| `COMPLETE` | Gate passed. Evidence recorded. |
| `SUPERSEDED` | Displaced or replaced. **Reason and replacement must be recorded.** |

**Transition rule:** `PROVISIONAL → ACTIVE` only after its dependency gate has passed
empirically. Not on expectation.

**Immutability rule:** a frozen step number's original meaning is permanent. Work that
displaced it is recorded alongside, never in place of it. Numbers are never recycled to
make history look clean.

---

## Integrity invariants

All three are required. Any one alone is insufficient.

| Invariant | Question | Current value |
|---|---|---|
| **Count** | Did our inventory change? | 37 contracts — 26 CAUSAL_VERIFIED, 8 STRUCTURAL_ONLY, 3 NEGATIVE_EVIDENCE |
| **Provenance** | Did our epistemic justification change? | capability identity + evidence fingerprint + execution epoch + measurement definition + context fingerprint + prerequisite values + admission provenance |
| **Runtime** | Are we executing under the profile that was qualified? | harness epoch `7978c9be5b2107e9…` |

Count integrity proves inventory integrity. Provenance integrity proves epistemic
integrity. Runtime integrity proves the qualification applies to the executing host.

A frontier count can remain exactly `37 / 26 / 8 / 3` while canonical-context evidence
is incorrectly transferred to authorize corpus-context execution. Counts cannot detect
that. Provenance can.

---

## Part 1 — Historical reconciliation (16.5.39 → 16.5.55)

Frozen numbers are immutable. Commits verified against `git log` at 16.5.56.

### Executed as frozen

| Frozen # | Original intent | Actual commits | Status |
|---|---|---|---|
| 16.5.39 | Processor-state safety fence + PatchContext | `654bf47` processor-state validation guard | COMPLETE |
| 16.5.40 | Evidence disposition ledger + replayability | `b109c62` evidence disposition and replay enforcement | COMPLETE |
| 16.5.41 | Current capability qualification semantics | `51b8107` current semantics audit | COMPLETE |
| 16.5.42 | Seed-context admission | `09ddc3a`, `4fe87ca`, `b0f6a06`, `d2c210b` | COMPLETE |
| 16.5.43 | Foundational loudness/duration revalidation | `55fff64` (43.1), `42fa694` (43.2), `67b4baf`, `e2533d2`, `af6af3c` (43.3) | COMPLETE |

Note: 16.5.39–16.5.42 were committed without step numbers in their messages. Mapping
above is by content and chronology.

### Displaced — reserved meaning never executed

| Frozen # | Original intent | Commits | Status | Replacement |
|---|---|---|---|---|
| 16.5.44 | AbletonMCP host-parameter vertical slice | none | SUPERSEDED — never executed | 16.5.57 / 16.5.59 |
| 16.5.46 | Ableton-context requalification | none | SUPERSEDED — never executed | 16.5.60A (conditional) |
| 16.5.47 | Demand-driven sound-design capability campaign | none | SUPERSEDED — never executed | 16.5.62 |
| 16.5.49 | Typed multi-intent producer planner | none | SUPERSEDED — never executed | 16.5.61 |

### Number reused for different work

The work done under these numbers was legitimate and is retained. Only the numbering
collided with reserved meanings.

| Frozen # | Original intent | Actual work committed | Status | Replacement |
|---|---|---|---|---|
| 16.5.45 | Ableton processor-state transport | `02e50fd` Repair EvidenceRecord provenance boundary for baseline_overrides | SUPERSEDED | 16.5.58/16.5.59 |
| 16.5.48 | Live knowledge-expansion loop | `15e31da` Repair evidence → ClaimGroup → CapabilityContract provenance | SUPERSEDED | 16.5.63 |
| 16.5.50 | Multi-intent execution + optimizer | `d119979` Register Sustain in semantic-target vocabulary (+ `0992eec`, `80cefe0`, `b67e4c7`, `152da26`) | SUPERSEDED | 16.5.64 |
| 16.5.51 | Corpus-context transfer boundary | `3e4464a` Final producer-entry prerequisite verification | SUPERSEDED | 16.5.65 |
| 16.5.52 | Arrangement brief compiler | `33c6cad`, `7c62255`, `1513f94`, `e7afe66`, `40711d1`, `d80d391`, `3b89d9a` — semantic vocabulary registration (Env1.Release, Env1.Attack, OSC1.Enable, OSC1.Wavetable, Filter.Resonance, Filter.Type) | SUPERSEDED | 16.5.66 |
| 16.5.53 | Role-state construction + isolated verification | `f431081`, `5ce4efd` First real producer construction path — OSC1.Volume | SUPERSEDED | 16.5.67 |
| 16.5.54 | Automated Ableton arrangement assembly | `abb1a03` Producer verification semantics audit — six independent distinctions | SUPERSEDED | 16.5.68 |
| 16.5.55 | Arrangement render + objective verification | `7b5b974` Representative producer operation-class verification | SUPERSEDED | 16.5.69 |

### Reconciliation finding

Every displaced or reused number belonged to **Ableton or production-path work**. Every
substitute was **compiler or vocabulary work**. Zero Ableton code exists in the
repository: `git log --grep="ableton"` returns only the initial import, and no `.als`
file is present.

The project's centre of gravity must now shift from *"can we compile Serum controls?"*
to *"can compiled Serum state become a reproducible Ableton production artifact?"*

---

## Part 2 — Forward plan

| # | Step | State | Depends on |
|---|---|---|---|
| 16.5.56 | Roadmap reconciliation + authoritative step register | **FROZEN** | — |
| 16.5.57 | AbletonMCP feasibility probe | **FROZEN** | 16.5.56 |
| 16.5.57-Q7c | Processor-state offline injection + Ableton application | **COMPLETE** | 16.5.58 |
| 16.5.58 | Host architecture decision (Option A: Configure/MCP Only) | **ACTIVE** | 16.5.57 |
| 16.5.59 | End-to-end Ableton vertical slice (Configure/MCP constrained) | PROVISIONAL | 16.5.58 |
| 16.5.60 | Save/reopen + host fidelity verification | PROVISIONAL | 16.5.59 |
| 16.5.60A | Conditional Ableton-runtime requalification | **RESERVED** | 16.5.57 binary-hash result |
| 16.5.61 | Typed musical-intent layer | PROVISIONAL / **PARALLEL** | 16.5.41 (met) |
| 16.5.62 | Demand-driven capability expansion | PROVISIONAL | 16.5.60 |
| 16.5.63 | Live knowledge-discovery loop | PROVISIONAL | 16.5.61, 16.5.62 |
| 16.5.64 | Multi-intent execution + bounded optimizer | PROVISIONAL | 16.5.63 |
| 16.5.65 | Corpus-context transfer boundary | PROVISIONAL | 16.5.64 |
| 16.5.66 | Arrangement brief + MIDI source compiler | PROVISIONAL | 16.5.64 |
| 16.5.67 | Role-state construction + isolated verification | PROVISIONAL | 16.5.66 |
| 16.5.68 | Ableton arrangement assembly | PROVISIONAL | 16.5.67, 16.5.60 |
| 16.5.69 | Arrangement render + objective verification | PROVISIONAL | 16.5.68 |
| 16.5.70 | Bounded production correction | PROVISIONAL | 16.5.69 |
| 16.5.71 | Adversarial / regression hardening | PROVISIONAL | 16.5.70 |
| 16.5.72 | Reproducibility + audit-bundle rehearsal | PROVISIONAL | 16.5.71 |
| **16.6** | **Two-context 16-bar acceptance** | **FROZEN** | all above |

Only 16.5.56, 16.5.57 and 16.6 are frozen. Everything between is provisional and may be
reshaped, merged or split once 16.5.57 reports the host capability boundary. Reshaping a
PROVISIONAL step is a documented refinement recorded here — not a silent reassignment.

---

## Step definitions — frozen steps

### 16.5.56 — Roadmap reconciliation + authoritative step register `FROZEN`

Documentation and audit only. No code, no Serum, no Ableton, no evidence.

- Create this register with immutable frozen numbers and provisional forward plan.
- Mark `GATES.md` and `PROOF_PLAN.md` as historical/scoped.
- Correct factual drift in status documents.
- Record the authority rule in `CLAUDE.md`.

**Gate:** every commit from 16.5.39 onward is represented with a status. No number
carries two different meanings without both being recorded.

### 16.5.57 — AbletonMCP feasibility probe `FROZEN`

Split into two tiers. The project's safety constraints forbid mutation and rendering
unless a task explicitly requires them, so the mutating half is separated and bounded.

**16.5.57a — read-only.** No writes of any kind.

1. **Serum binary hash** in Ableton vs harness epoch `7978c9be5b2107e9…` — asked first,
   because it determines whether any harness qualification transfers at all.
2. Which Ableton instance is reachable; Live version.
3. Can Serum2 be located and its device parameters *read*.
4. Do state-extraction, MIDI, track, render and export interfaces exist.

**16.5.57b — bounded, explicitly authorized, scratch set only.** Never the user's project.

5. Can parameters be mutated and read back.
6. Can tracks, devices, clips and notes be created.
7. Can processor state be imported and extracted.
8. Can audio be rendered; can master and stems be recovered.
9. Can the set be saved, reopened, and the state re-extracted.

**Prior art constraining question 7:** `PROOF_PLAN.md` records that genuine v8 processor
state has already been extracted from Ableton **once, manually** — a `.SerumPreset`
loaded into Ableton-hosted Serum, saved to `.als`, state read from the embedded
`<ProcessorState>` hex block. It also records that Ableton's host loop succeeds where
DawDreamer's `open_editor()` fails. So question 7 is not *"is this possible?"* — it is
**"can the manual extraction be automated, and does the reverse direction work?"**

**Gate:** a machine-readable capability matrix with an explicit yes/no per question. No
inference, no "probably", no "MCP likely exposes this."

### 16.5.58 — Host Architecture Decision `ACTIVE`

Decision artifact: `experiments/16_5_58_host_architecture/ARCHITECTURE_DECISION_16_5_58.md`

**Architecture Selected**: Option A (Configure/MCP Only)

**Status**: SELECTED_CONSTRAINED (as of 2026-09-07)

**Gate Results**:
- **Q7c COMPLETE**: Processor-state offline injection works for initial file open. Visual observation: Serum OSC1.Volume showed 0.50 (injected value).
- **Q8 COMPLETE**: Real-time audio capture works (master + stems via sequential `record_section()` calls).
- **Q9 COMPLETE**: Processor-state persistence FAILS. File SET_A_INJECTED_with_B_state.als becomes unloadable on reopen ("Unknown Compound Stream Type" corruption error).

**Decision Rationale**: 
- Processor-state transport viable for one-time initialization only; NOT for save/close/reopen cycles
- Hybrid architecture rejected (persistence unreliable)
- Option A (Configure/MCP only) selected as the only production-viable architecture
- Scope constrained: parameter control only; cannot construct mod-matrix topology

**Capability Boundary**:
- Covered: VST3 parameters exposed through Configure Mode (read/write via MCP)
- Covered: Real-time audio capture (sequential, max ~5 min per call)
- NOT covered: Mod-matrix topology, unmapped Serum parameters, deep synthesis state
- NOT covered: Batch export (only real-time resampling)

**Frontier Integrity**: 37 contracts (26 CAUSAL_VERIFIED, 8 STRUCTURAL_ONLY, 3 NEGATIVE_EVIDENCE) — unchanged

---

### 16.6 — Two-context 16-bar acceptance `FROZEN`

All criteria required:

1. Malformed or preset-flavor processor state is rejected before rendering.
2. Canonical and normalized-corpus seed contexts are valid, fingerprinted, audibly
   distinct and replayable.
3. Every executed control is currently qualified for its exact runtime profile, context,
   metric, stimulus and prerequisites.
4. No invalidated or context-incomplete record supports any final claim, plan or
   optimizer decision.
5. The producer parses the brief into typed intents and refuses unsupported intent
   without silently choosing a control.
6. A real discovery request creates an isolated experiment; ClaimEngine ingests it;
   retry behaviour changes only because evidence changed.
7. Multi-intent execution verifies each goal independently and adapts within bounded,
   evidence-qualified ranges.
8. The final Ableton set contains three validated Serum roles and a 16-bar four-section
   arrangement.
9. Ableton processor states survive save/reopen and match the audited role contexts.
10. Master and stems render automatically; scheduled roles are audible; planned section
    differences occur; no clipping; master peak at or below −1 dBFS.
11. Harness/Ableton fidelity is judged against empirically calibrated repeatability, not
    assumed byte identity.
12. The audit bundle reconstructs every decision from persisted data alone.
13. **The user approves the final master after audition.** 16.6 cannot be self-certified.

---

## Standing constraints on provisional steps

**16.5.60A activation.** Executes only if 16.5.57a reports a Serum binary hash differing
from the harness epoch. If activated, requalify **only the capabilities the 16.6
production path actually executes** — not the full 37-contract frontier. Bounded by
demand, not by inventory.

**16.5.61 is parallel-capable.** Its dependency is the compiler, not the host. If the
host track blocks, this is the designated parallel work rather than idling. Parallel does
not mean frozen — its implementation stays provisional.

**16.5.61 vocabulary.** `GATES.md` designates *"make darker"* as the hypothesis/refusal
vehicle and explicitly forbids adding `darker` to `SEMANTIC_TARGETS` or fabricating a
spectral-centroid contract. That stands. Supported intents resolve to qualified controls;
`darker` must produce `CAPABILITY_DISCOVERY_NEEDED` and a `DiscoveryRequest`, with no
silent mutation.

**16.5.66 MIDI source.** Musical note content is **not** part of the Serum evidence chain.
For first acceptance, use committed deterministic MIDI fixtures as the authoritative
source. AbletonMCP generators (`generate_chord_progression`, `generate_bassline`,
`generate_melody`, `generate_voiced_progression`) may become adapters later, validated and
frozen before use. Keep musical content and Serum knowledge as separate chains.

**16.5.59 degradation path.** The vertical slice assumes processor-state transport. If
16.5.57 clears parameter mutation but not state transport, the slice substitutes "known
host-parameter configuration" for "known Serum state" and still runs. Declare which at
16.5.58 — do not discover it mid-slice.

**Regression scope.** From 16.5.61 onward, every step asserts context fingerprints and
admission provenance, not frontier counts alone.

---

## Deferred until after 16.6

Not blockers. Revisit only if a concrete production goal hits the specific gap.

- Filter Resonance full context recovery. `16.5.38` is CLOSED: the `host:Filter 1 On`
  prerequisite was verified applied on both arms and produced a real but partial effect
  (delta 1.47 dB vs historical 18.46; baseline −22.17 vs historical −26.38). Remaining
  work is identifying additional context in the `FILTER-RESONANCE` witness record.
- FXEQ / Freq1 brightness research.
- Full revalidation of the remaining historical contract inventory.
- Corpus conversion to processor flavor at rest (boundary injection currently suffices).
- Arbitrary-preset generalization beyond the two admitted seed contexts.
- `WHY-CAPTURE-V8-FAILED-1` — the transient `capture_v8_skeleton` failure at 16.5.17.
- Broad natural-language understanding beyond the accepted production vocabulary.
- Unbounded composition, mixing, mastering, style transfer.

---

## Governing principle

No downstream implementation is frozen until its immediate dependency has been
empirically cleared.
