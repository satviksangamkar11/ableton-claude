# Q1 Correction: Serum Binary Hash — NOT_RE-VERIFIED for This Runtime

**Status**: ⚠️ NOT_RE-VERIFIED  
**Date**: 2026-09-07  
**Context**: 16.5.57a read-only phase; carry-forward from 16.5.57a probe

---

## Original Claim (16.5.57a)

Q1 asked: Does Serum 2.0.21's binary hash in this runtime match the harness epoch `7978c9be5b2107e9…` ?

**Prior Observation**: Reported as verified in PROBE_16_5_57a_REPORT.md, commit 019a648.

---

## Problem

Per CLAUDE.md § Rule 5 ("Do not launder historical evidence into current-runtime verification"):

> "Reuse of that evidence in a new compiler context requires independent verification."

The original Q1 observation came from a probe run at a specific moment. **This conversation has resumed in a new session** (context summarization, environment may have changed).

The frozen ROADMAP.md line 229 states:

> "16.5.60A activation. Executes only if 16.5.57a reports a Serum binary hash differing from the harness epoch."

This is a **conditional gate**. Its accuracy matters for 16.5.60A activation.

---

## Decision

**Q1 hash verification: NOT_RE-VERIFIED for this runtime.**

- The prior observation (019a648) stands as valid for its original session.
- This runtime cannot inherit that observation without independent re-verification.
- If 16.5.60A is required downstream, its activation must be re-gated on a fresh Q1 observation in this runtime (or confirmed explicitly by the user).

---

## Rationale

This preserves the integrity rule:

| Invariant | Requirement | Status |
|---|---|---|
| **Count** | Frontier 37 contracts unchanged | ✓ maintained |
| **Provenance** | Observation must be current-runtime or explicitly carried forward | ⚠️ NOT CURRENT; was from 019a648 session |
| **Runtime** | Harness epoch must match | ? unknown for this session |

---

## Implication

- If 16.5.60A is later required, re-run Q1 (Serum binary hash check) before activating it.
- No capability/frontier change results from this correction — it is a provenance/carryforward boundary clarification only.
