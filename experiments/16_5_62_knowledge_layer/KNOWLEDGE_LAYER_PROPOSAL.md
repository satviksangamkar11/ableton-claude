# Knowledge Acquisition Layer — Full System Design

**Status: DESIGN ONLY. No code. Requires ROADMAP.md amendment before any implementation.**

Designs a teaching / knowledge-acquisition layer above the existing evidence
chain: the producer can be taught from transcripts, manuals, and direct
explanation, and converts that teaching into reliable Serum 2 knowledge through
experiment rather than through storage.

Scope of this document: the complete system. Build sequencing is §18; nothing in
§18 is authorized by this document.

---

## 1. The problem

The naive implementation is dangerous and must never be built:

```
transcript says "source X makes it wider"
        ↓
store as fact:  source_X → width
```

That is hallucination with a citation attached. The correct shape:

```
transcript says "source X makes it wider"
        ↓
ExternalClaim(verbatim, source_ref, status=UNVERIFIED_EXTERNAL)
        ↓
   translatable into an ExperimentSpec?
        ↓                        ↓
      YES                       NO
        ↓                        ↓
  ExperimentSpec          UNTRANSLATABLE
        ↓                 (record exactly what is missing)
  harness → EvidenceRecord
        ↓
  ClaimEngine → ClaimGroup → CapabilityContract
```

The external claim never becomes knowledge. It becomes, at most, *a reason to
run an experiment*. The experiment becomes knowledge.

---

## 2. Grounding — what the existing code already enforces

Read before designing (`serum2/evidence/`, `serum2/findings.py`). These four
facts constrain every decision below.

**a. `ClaimEngine` forbids prose.**
`claim.py:419` — *"Groups records mechanically. No prose interpretation anywhere."*
A transcript is pure prose. There is no legitimate path from a transcript into
`ClaimEngine.add()`. Any design creating one is wrong by construction.

**b. `findings.py` is the precedent, enforced by import topology.**
> *"A finding NEVER writes capability status. It may motivate a brand new
> ExperimentSpec... The finding itself has no write path into admission.py or
> capability_contract.py, by construction: this module imports nothing from
> either, and nothing in either imports this module."*

The Knowledge layer must be isolated the same way — by import topology, testable
as a regression assertion, not by convention or review.

**c. The Knowledge ledger is NOT the Findings ledger.**
`findings.py` requires `evidence_refs` and forbids a finding existing *"from
recollection or prose alone."* External claims are born from prose and have no
evidence refs. Opposite provenance rules. Two ledgers, one rule each:

| Ledger | Born from | Required reference | May motivate |
|---|---|---|---|
| Findings | evidence exposed a question | `evidence_refs` (content-hashed) | ExperimentSpec |
| Knowledge | a human said something | `source_ref` (locator + verbatim) | ExperimentSpec |

**d. Testability is bounded by the kernel inventory, not by Serum.**
`serum2/evidence/kernels/` contains exactly ten kernels:

```
wholesignal_centroid     windowed_mean_centroid    centroid_zero_crossing_rate
overall_rms_db           attack_onset_rms_db       decay_window_rms_db
sustain_window_rms_db    tail_rms_db
modulation_depth         modulation_frequency_hz   stereo_width
```

`spec.py:227` refuses any measurement plan without a `kernel_artifact`:
> *"a live measurement must carry explicit identity; falling back to
> METRICS[metric] silently produces evidence with measurement_definition_id=None,
> which cannot be admitted into any comparability cohort"*

So *brightness* is testable (centroid), *width* is testable (`stereo_width`),
and *warmth* is **untestable — because no warmth kernel exists**, not because
Serum is unknown. The system must say exactly that. This is the single most
useful output of the entire layer.

---

## 3. The core rule

> **An ExternalClaim may raise the PRIORITY of an experiment.
> It may never raise the STATUS of a capability.**

Corollaries, each of which becomes a test:

1. Ten sources agreeing produce a strong *hypothesis*, never `CAUSAL_VERIFIED`.
2. A claim agreeing with existing evidence adds nothing to that evidence. It is
   redundant, not confirmatory.
3. A claim disagreeing with evidence does **not** create `BLOCKED_CONTRADICTED`.
   Only evidence contradicts evidence. Prose vs. evidence is recorded as
   `CONFLICTS_WITH_EVIDENCE` **on the claim**, never on the contract.
4. No field may be named or valued so that it reads as true. There is no
   `verified: bool` and no confidence float. Confidence is derived at the claim
   layer from evidence; a second confidence scale over prose is precisely the
   laundering this project forbids.
5. Every artifact derived from a claim is traceable to an exact verbatim quote,
   so a misreading is auditable as an *interpretation error* rather than being
   indistinguishable from a bad source.

---

## 4. Full architecture

```
   TEACHING INPUT                                    PRODUCTION GOAL
   transcript / manual / user statement                    │
          │                                                │
          ▼                                                │
  ┌───────────────────┐                                     │
  │ 1. Source Registry│  immutable, content-hashed          │
  └─────────┬─────────┘                                     │
            ▼                                               │
  ┌───────────────────┐                                     │
  │ 2. Extraction     │  LLM proposes schema                │
  │    (bounded)      │  deterministic validator disposes   │
  └─────────┬─────────┘                                     │
            ▼                                               │
  ┌───────────────────┐                                     │
  │ 3. Knowledge      │  ExternalClaim ledger               │
  │    Ledger         │  epistemic status only              │
  └────┬────────┬─────┘                                     │
       │        │                                           │
       │        ▼                                           │
       │  ┌──────────────┐                                  │
       │  │4.Corroboration│ independence-aware              │
       │  └──────┬───────┘                                  │
       │         ▼                                          │
       │  ┌──────────────┐                                  │
       │  │5. Translation│ → ExperimentSpec | UNTRANSLATABLE│
       │  └──────┬───────┘                                  │
       │         ▼                                          │
       │  ┌──────────────┐                                  │
       │  │6. Experiment │ demand-driven ranked backlog     │
       │  │   Queue      │                                  │
       │  └──────┬───────┘                                  │
       │         ▼                                          │
       │   ══════════════════════════════════════           │
       │    EXISTING EVIDENCE CHAIN (unchanged)             │
       │    harness → EvidenceRecord → ClaimEngine          │
       │           → ClaimGroup → CapabilityContract        │
       │   ══════════════════════════════════════           │
       │         │                                          │
       │         ▼                                          │
       │  ┌──────────────┐                                  │
       └─▶│7. Feedback   │ evidence updates CLAIM status    │
          └──────┬───────┘ (never the reverse)              │
                 │                                          │
   procedural    │                                          ▼
   claims ──────▶ GoalTemplate ──────────────────▶  Goal Model
                  (no evidence required)                    │
                                                            ▼
                                                     World Model
                                                            │
                                                            ▼
                                                        Planner
                                                            │
                                                  Capability Admission
                                                            │
                                                        Compiler
                                                            │
                                                   MCP / Ableton / Serum
                                                            │
                                                    Render → Measure
                                                            │
                                                       Evaluator
                                                            │
                                                    Evidence / Claims
```

The only path from teaching into capability runs through the existing evidence
chain. There is no bypass, and §18 gate P1 asserts this structurally.

---

## 5. Knowledge taxonomy — three types, three destinations

Conflating these is the primary design risk.

### Causal — *"Filter 1 Cutoff down → spectral centroid down"*
**Destination: the existing evidence chain, unchanged.**
The only type that can ever become a `CapabilityContract`. Route:
`ExternalClaim → ExperimentSpec → harness → EvidenceRecord → ClaimGroup → Contract`.
No new machinery. The Knowledge layer's entire job is producing a well-formed
`ExperimentSpec` — and refusing when it cannot.

### Declarative — *"Env 1 is the amplitude envelope"*
**Destination: a mapping hypothesis, tested structurally.**
A claim about *identity*: that a semantic target corresponds to a specific host
parameter. Testable without any causal claim — write it, read it back, observe
whether the amplitude envelope moves.

Already needed. `mcp_intent.py:86` carries a hand-derived identity decision:
> *"Env 4 (indices 100-104) is an auxiliary modulation envelope, not the amp
> envelope. Mapping Env1.* to Env 4 would silently write to the wrong parameter."*

That is a declarative claim living in a code comment with no provenance. It
should be an `ExternalClaim` with a source and a test.

### Procedural — *"for a pluck: short attack, short decay, low sustain"*
**Destination: the GOAL layer. Not the evidence layer. This is the key insight.**

A recipe is not a claim about Serum — it is a *definition of a target*. "Pluck
means fast attack and short sustain" cannot be falsified by any Serum
measurement, because it is a statement about what the word *pluck* means.

It maps directly onto the contract already built in 16.5.61a:

```python
GoalTemplate(
    name="pluck",
    source_ref=transcript:VIDEO_ID@02:30,
    characteristics=MusicalCharacteristics(
        attack=AttackProfile.PUNCHY,
        sustain_length=SustainLength.SHORT,
    ),
)
```

A `GoalTemplate` requires **no evidence at all**, because it asserts nothing
about Serum. It becomes Serum-specific only when the Planner tries to realize it
and must find capabilities — at which point normal admission applies.

**The consequence is the cleanest property of this design: the dangerous
knowledge type (causal) is the one that already has rigorous machinery, and the
abundant knowledge type (procedural) is the one that needs none.**

---

## 6. Layer 1 — Source Registry

```
source_id        content hash of the retrieved artifact
kind             transcript | manual | user_statement | article
identifier       video id / document id / message id
retrieved_at     timestamp
content_hash     sha256 of stored text
stored_path      local copy — sources must be re-readable at audit time
derived_from     [source_id]  (see §9 independence)
```

Rules:

- A source is **immutable once registered**. Re-retrieval producing different
  content registers a *new* source; it never mutates the old one.
- A source must be stored locally. An audit that cannot re-read the source
  cannot verify an interpretation, and 16.6 criterion 12 requires the audit
  bundle to reconstruct every decision from persisted data alone.
- Registering a source is not ingestion and creates no claims.

---

## 7. Layer 2 — Extraction (where the LLM sits, and its limits)

Extraction turns prose into candidate `ExternalClaim`s. This is the only place
in the system where an LLM makes a judgement, and its authority is deliberately
narrow.

**The LLM proposes; a deterministic validator disposes.**

Permitted:
- Segment a source into candidate statements.
- Quote `verbatim_text` exactly.
- Propose `knowledge_type` and a structured `extracted` triple.
- Propose a `serum_mapping_hypothesis` (which semantic target this might mean).
- Say *"I cannot interpret this"* — a first-class, expected outcome.

Forbidden:
- Assigning `epistemic_status` (the validator does this; ingest is always
  `UNVERIFIED_EXTERNAL`).
- Deciding translatability (§10 does this deterministically).
- Writing to the ledger directly — every write passes the validator.
- Paraphrasing into `verbatim_text`.
- Resolving a target not present in `SEMANTIC_TARGETS`.

### Interpretation is versioned; sources are not

`verbatim_text` is immutable. `extracted` is a **versioned interpretation** with
its own id, because extraction is fallible in a specific and predictable way:

> A teacher says *"open it up and it gets wider."* Extraction reads "wider" as
> stereo width. The teacher meant a wider frequency range.

That error must be correctable without touching the source, and every experiment
generated from the bad interpretation must be traceable and invalidatable:

```
InterpretationRevision(
    claim_id, from_version, to_version,
    reason, revised_by,
    invalidates_experiments=[experiment_id],
)
```

Evidence produced under a superseded interpretation stays valid *as evidence* —
it measured what it measured. What changes is which claim it is evidence *for*.
This distinction is load-bearing: the record is never retracted, only re-linked.

### Unstated context is a permanent confound

A tutorial says *"turn the filter down to make it darker"* — true of that
video's patch, under its oscillators, its resonance, its note range. The context
is almost never stated.

```
stated_context      {} in the overwhelming majority of cases
context_confound    True whenever stated_context is empty
```

This is *why* external claims can only ever be hypotheses, and it connects
directly to the project's existing context-fingerprint discipline. An
`ExperimentSpec` generated from a context-free claim must declare its own
context explicitly; it may never inherit an assumed one from the teaching.

---

## 8. Layer 3 — The Knowledge Ledger

### ExternalClaim

```
claim_id              stable hash of (source_id, verbatim_text)
source_ref            {source_id, locator}   locator = timestamp / page / line
verbatim_text         exact quote. Never a paraphrase. Immutable.
knowledge_type        CAUSAL | DECLARATIVE | PROCEDURAL | UNCLASSIFIED
epistemic_status      closed vocabulary, below
extracted             {subject, predicate, direction, qualifier}  versioned
extraction_version    integer; see InterpretationRevision
stated_context        {} unless the source explicitly stated conditions
context_confound      bool
serum_mapping         proposed semantic target, or None
translation_result    TranslationResult | None
corroborating         [claim_id]
conflicting           [claim_id]
experiment_refs       [experiment_id] generated from this claim
```

### Epistemic status — closed vocabulary

```
UNVERIFIED_EXTERNAL      default on ingest. Someone said it. Nothing more.
UNTRANSLATABLE           cannot become an ExperimentSpec; reason recorded
                         NO_SEMANTIC_TARGET | NO_KERNEL | NO_DIRECTION
                         NO_STIMULUS | NOT_A_CLAIM | CONTEXT_UNRESOLVABLE
EXPERIMENT_PENDING       a valid ExperimentSpec exists; not yet run
CORROBORATED_UNTESTED    ≥2 independent sources agree; still zero evidence
SUPPORTED_BY_EVIDENCE    an experiment ran and agreed. The CONTRACT carries
                         status; this records only that the claim pointed right
REFUTED_BY_EVIDENCE      an experiment ran and disagreed
CONFLICTS_WITH_EVIDENCE  contradicts an existing contract; the claim is
                         suspect, the contract is untouched
NOT_SERUM_SPECIFIC       general synthesis knowledge; no Serum claim to test
SUPERSEDED               interpretation revised; see InterpretationRevision
```

No `TRUE`. No `VERIFIED`. No confidence float.

### State machine

```
                    ┌──────────────────────┐
                    │ UNVERIFIED_EXTERNAL  │ ◀── ingest
                    └──────────┬───────────┘
                               │ translation gate (§10)
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
      UNTRANSLATABLE   EXPERIMENT_PENDING   NOT_SERUM_SPECIFIC
              │                │
              │ (new kernel or │ experiment runs
              │  target added) │
              └───────▶────────┤
                               ▼
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
   SUPPORTED_BY_       REFUTED_BY_      CONFLICTS_WITH_
     EVIDENCE            EVIDENCE           EVIDENCE

   CORROBORATED_UNTESTED is orthogonal: it may hold alongside
   UNTRANSLATABLE or EXPERIMENT_PENDING, and never alongside any
   evidence-derived status.

   Any state ──▶ SUPERSEDED  (interpretation revised, §7)
```

Transition authority:
- Ingest → `UNVERIFIED_EXTERNAL`: validator only.
- → `UNTRANSLATABLE` / `EXPERIMENT_PENDING`: translation gate only, deterministic.
- → any evidence-derived status: the feedback layer (§12) only, and only when an
  `EvidenceRecord` exists. No other component may write these.
- `UNTRANSLATABLE` is **not terminal**. Adding a kernel or registering a semantic
  target can make a previously untranslatable claim testable. Re-evaluation is
  triggered by kernel/target inventory changes, never by re-reading the source.

---

## 9. Layer 4 — Corroboration and conflict

### Independence is the hard problem

Two YouTube videos both paraphrasing the Serum manual are **not** two
independent sources. Counting them as two manufactures false confidence — the
exact failure this project exists to prevent.

```
independence         INDEPENDENT | DERIVED | UNKNOWN
derived_from         [source_id]
```

Rules:

- Default is `UNKNOWN`, and **`UNKNOWN` counts as a single source** in any
  corroboration tally. Independence must be positively established, never assumed.
- `DERIVED` sources contribute zero additional corroboration weight.
- `CORROBORATED_UNTESTED` requires ≥2 sources each marked `INDEPENDENT`.
- Corroboration count is reported alongside every ranking, never folded into a
  single opaque score.

### Conflict between claims

Two claims conflict when they share a resolved semantic target and assert
opposite directions. A conflict is **informational** — it raises experiment
priority, because a disputed claim is a better experiment candidate than an
agreed one. It never produces a status on either claim beyond mutual
`conflicting` links.

### Conflict between claim and evidence

The claim loses. Status `CONFLICTS_WITH_EVIDENCE` is written to the claim; the
contract is untouched. Two legitimate readings — the source is wrong, or the
source held under context the experiment did not reproduce — are recorded as a
`Finding` in the *existing* findings ledger if and only if evidence exposed a
genuine mechanistic question. Ordinary "a tutorial was wrong" is not epistemic
debt and must not enter that ledger.

---

## 10. Layer 5 — The translation gate

Deterministic. Converts an `ExternalClaim` into an `ExperimentSpec`, or explains
precisely why it cannot.

`spec.py` requires, for a causal experiment: a resolvable `target_path`, an
`isolation_level`, and a `MeasurementPlan` with `metric`, `kernel_artifact`,
`expected_direction`, `threshold`, and `stimulus`. Each is a gate:

| Requirement | Source | Failure |
|---|---|---|
| semantic target | `SEMANTIC_TARGETS` lookup — exact, no fuzzy match | `NO_SEMANTIC_TARGET` |
| metric + kernel | dimension → kernel table over the ten kernels | `NO_KERNEL` |
| direction | `extracted.direction` | `NO_DIRECTION` |
| stimulus | role-appropriate default stimulus | `NO_STIMULUS` |
| isolation | `SINGLE_FIELD` for a single-target claim | — |
| context | §7 confound — spec must declare its own | `CONTEXT_UNRESOLVABLE` |

```
TranslationResult
  translatable        bool
  missing             [reason]
  proposed_target     semantic target name
  proposed_metric     metric name
  proposed_kernel     kernel artifact path
  proposed_direction  increase | decrease | none
  blocking_detail     names the exact missing piece
```

**The negative result is the product.**

> *"'makes it warmer' is UNTRANSLATABLE: NO_KERNEL — no measurement kernel in
> serum2/evidence/kernels/ produces a warmth scalar. Testing this claim requires
> a new kernel, not a new experiment."*

That converts vague teaching into a precise, actionable gap. Most claims will
fail this gate, and that is the system working correctly, not a shortfall.

The gate emits a spec; it never runs one. Execution stays with the harness under
existing safety constraints.

---

## 11. Layer 6 — Experiment queue

Turns the ledger into a ranked backlog for demand-driven discovery.

Ranking inputs, reported separately and never collapsed into one score:

```
independent_source_count     from §9, UNKNOWN counted as 1
disputed                     conflicting claims exist → raises priority
production_demand            a Planner DiscoveryRequest names this target
translatable                 hard filter — untranslatable claims cannot queue
already_covered              a contract already exists → drops priority
```

`production_demand` is what makes this serve production rather than compete with
it: a target both *taught* and *demanded by a real plan* outranks a target that
is merely popular in tutorials.

Output entries cite `claim_id`s and carry **no capability status**.

---

## 12. Layer 7 — Feedback

The only writer of evidence-derived claim status. Runs after an experiment
completes and its `EvidenceRecord` exists.

```
record.outcome_signature()      claim status
─────────────────────────       ────────────
EFFECT + direction matches  →   SUPPORTED_BY_EVIDENCE
EFFECT + direction opposes  →   REFUTED_BY_EVIDENCE
NO_OBSERVED_EFFECT          →   REFUTED_BY_EVIDENCE
INCONCLUSIVE                →   unchanged (EXPERIMENT_PENDING)
NOT_TESTED                  →   unchanged
```

`record.py:151` is explicit that `NOT_TESTED` and `INCONCLUSIVE` are **not
negative results**. Collapsing them into refutation would manufacture false
contradictions, and the feedback layer must preserve that four-valued domain
exactly as the record does.

Direction is compared against the *versioned* interpretation that generated the
spec. If the interpretation was later revised, the record is re-linked, never
retracted (§7).

---

## 13. GoalTemplate — the procedural path

Lives in `serum2/producer/`, not in the knowledge layer, because it is goal-layer
vocabulary rather than Serum knowledge.

```
name              "pluck", "sub bass", "wide pad"
source_ref        provenance only
characteristics   MusicalCharacteristics   (16.5.61a contract, unchanged)
```

Requires no evidence. Composition rules, when two templates are applied together:

- Same dimension, same value → merge.
- Same dimension, conflicting values → **refuse and report**; the producer must
  not silently pick one. This mirrors the Planner's existing refusal discipline.
- Disjoint dimensions → union.

A template never names a capability. It names only musical characteristics, so
the existing grounding and admission path applies unchanged.

---

## 14. Integration with the producer stack

| Layer | Change | Nature |
|---|---|---|
| `GoalModel` | none | — |
| `GoalTemplate` | new | expands goal vocabulary |
| `WorldModel` | none | — |
| `goal_grounding` | `possible_capabilities` sourced from ledger query instead of Python literals | fixes §16 leak |
| `Planner` | decision rules unchanged; `DiscoveryRequest` gains claim citations | additive |
| Admission / Compiler | none | — |
| Evidence chain | none | — |

The Planner's rules do not change. What changes is that its input carries
provenance, and a `DiscoveryRequest` can state *why* a target is worth testing —
citing the sources that suggested it — instead of citing nothing.

---

## 15. Persistence, replay, audit

16.6 criterion 12 requires the audit bundle to reconstruct every decision from
persisted data alone. For this layer that means:

- Ledger persists as validated JSON, following the `findings.py` pattern:
  `SCHEMA_VERSION`, closed vocabularies, a validator returning a problem list
  rather than raising.
- Source texts stored locally and content-hashed; a hash mismatch is a validation
  problem, exactly as `findings.py` treats a changed `evidence_ref`.
- Interpretation revisions are append-only. History is never rewritten.
- Replay requirement: **ledger + evidence store must reproduce every plan
  decision.** If a plan cited a claim, that claim and its interpretation version
  must be recoverable at that version.

---

## 16. Known defect this layer resolves

`serum2/producer/goal_grounding.py` hardcodes capability suggestions:

```python
possible_capabilities=["OSC1.Volume", "Filter.Cutoff", "Filter.Resonance", "Env1.Attack"]
```

Those associations came from general synthesis knowledge, not evidence. CLAUDE.md
forbids exactly this — *"never invent context from target name alone"* — and the
docstring hedge does not fix it, because the Planner consumes the list directly
as `gap.possible_capabilities`.

**Decision: leave in place until this layer replaces them (§14).** Recorded here
as a known defect, deliberately not logged as a Finding — the findings ledger is
for questions evidence exposed, not for code defects.

---

## 17. Failure modes

Each becomes a test.

| # | Failure | Guard |
|---|---|---|
| F1 | Claim laundered into a capability | Import-topology assertion (§2b) |
| F2 | Corroboration mistaken for evidence | `CORROBORATED_UNTESTED` cannot coexist with an evidence-derived status |
| F3 | Sibling sources counted as independent | `UNKNOWN` independence counts as 1 (§9) |
| F4 | Paraphrase drift | `verbatim_text` immutable; interpretation versioned |
| F5 | Unstated context assumed | `context_confound` set; spec must declare its own |
| F6 | LLM assigns status | Status writes restricted to validator / gate / feedback |
| F7 | `INCONCLUSIVE` read as refutation | Four-valued domain preserved (§12) |
| F8 | Untestable claim reframed as testable | Gate emits `NO_KERNEL`; no fallback metric |
| F9 | Ledger growth outpaces evidence | Report claim:evidence ratio; a large ledger with no experiments is a warning, not progress |

---

## 18. Roadmap reconciliation

Stated plainly rather than designed around.

**ROADMAP.md defers this work.** Under *Deferred until after 16.6*:
> *"Broad natural-language understanding beyond the accepted production vocabulary."*

**And the register exists to stop this exact pattern.** The 16.5.56 finding:
> *"Every displaced or reused number belonged to Ableton or production-path work.
> Every substitute was compiler or vocabulary work... The project's centre of
> gravity must now shift from 'can we compile Serum controls?' to 'can compiled
> Serum state become a reproducible Ableton production artifact?'"*

Nine numbers were lost that way. A teaching engine is knowledge-layer work; built
now, it repeats the substitution.

**The 16.6 bottleneck is reach, not knowledge.** `mcp_intent.py::MCP_HOST_MAP`
holds 7 entries against 37 contracts. 16.6 needs three audibly distinct roles.
The gap is that most verified capabilities cannot be reached through the Option A
path — not that the system knows too little about synthesis.

**The framing that reconciles them:**

> The Knowledge layer is an experiment *prioritizer*, never a knowledge source.

It cannot add capability. It turns *"which of 127 host parameters deserve
experiments?"* into *"these six, because four independent sources say they matter
for bass character, and the Planner has already demanded two of them."* That
accelerates 16.5.62 — the actual blocker.

### Phased build (for later authorization — nothing here is approved)

| Phase | Contents | Gate (CHECK / EXPECT) |
|---|---|---|
| **P1** | Source Registry + ExternalClaim ledger + validator. Manual entry only. | CHECK: import-topology test — module imports nothing from `admission.py` / `capability_contract.py` / `claim.py`, and none import it. EXPECT: pass, mirroring `findings.py`. |
| **P2** | Translation gate | CHECK: *"source X makes it wider"* → EXPECT translatable, proposes `stereo_width`. CHECK: *"makes it warmer"* → EXPECT `UNTRANSLATABLE / NO_KERNEL` naming the missing kernel. |
| **P3** | `GoalTemplate` + composition rules | CHECK: build a "pluck" template. EXPECT: resolves to `MusicalCharacteristics`, touches no contract. CHECK: two templates conflicting on one dimension. EXPECT: refusal, not silent pick. |
| **P4** | Replace hardcoded `possible_capabilities` with ledger query | CHECK: `grep -n 'possible_capabilities=\[' goal_grounding.py`. EXPECT: zero literal lists. CHECK: the 3 Planner tests. EXPECT: pass, or fail loudly because their suggestions were never evidence-backed — the correct outcome, not a regression to paper over. |
| **P5** | Corroboration + independence | CHECK: two `DERIVED` sources. EXPECT: corroboration count 1, not 2. |
| **P6** | Experiment queue | CHECK: ranked output. EXPECT: every entry cites ≥1 `claim_id`; none carries a capability status. |
| **P7** | Feedback layer | CHECK: feed an `INCONCLUSIVE` record. EXPECT: claim status unchanged, not refuted. |
| **P8** | Transcript ingestion + LLM extraction | CHECK: ingest a real transcript. EXPECT: every claim carries exact verbatim + resolvable locator; zero paraphrases. |

P1–P4 are the slice that serves 16.5.62 and fixes §16. P5–P8 are the full
teaching engine and are the part ROADMAP defers past 16.6.

### Regression invariants — all phases

Frontier stays **37 / 26 / 8 / 3**. Harness epoch `7978c9be5b2107e9…` unchanged.
If either moves, the layer has written where it must not.

---

## 19. Non-goals

- Any path from `ExternalClaim` to `CapabilityContract` that skips the harness.
- Automated writes to `SEMANTIC_TARGETS`.
- Numeric confidence scores over prose.
- Changing any existing contract status, count, or hash.
- Autonomous source discovery — the system is *taught*, it does not go looking.
- Treating ledger size as progress. Claims are questions, not knowledge (F9).
