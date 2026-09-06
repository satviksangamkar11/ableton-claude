# 16.5.48: Shared Context Provenance Repair

## Objective

Repair the evidence → ClaimGroup → CapabilityContract provenance path so that shared baseline_overrides/context from admitted EvidenceRecords can be exposed by CapabilityContract.

This is a pure architecture/provenance repair - no Serum mutations, no new EvidenceRecords, no policy changes.

## Problem Identified

The baseline_overrides field in EvidenceRecord.experiment was being checked but never captured or exposed in CapabilityContract. When EvidenceRecords were promoted to ClaimGroups and then to Contracts, the shared context information was lost.

This prevented the compiler from understanding what baseline conditions were established during evidence collection.

## Solution Implemented

### 1. Shared Context Analysis

For every ClaimGroup, analyzed all supporting EvidenceRecords to determine:
- Do all records have baseline_overrides? (all_have_context)
- Are they identical across records? (identical_context)
- Are they partially present? (partially_present)
- Are they in conflict? (conflict_signature)
- Are they completely missing? (legacy records)

### 2. Provenance Extension

Extended the CapabilityContract.provenance dict (existing generic structure) with a new `shared_context` section:

```json
"shared_context": {
  "status": "IDENTICAL|PARTIAL|CONFLICTING|UNAVAILABLE",
  "all_records_have_baseline_overrides": bool,
  "records_with_baseline_overrides": [list],
  "records_missing_baseline_overrides": [list],
  "context_fields": [list],
  "baseline_overrides_identical": value_or_dict,
  "baseline_overrides": list  // only if IDENTICAL
}
```

Additionally added `measurement_definition_ids` to provenance for traceability.

### 3. Architecture Compliance

- Used ONLY existing generic contract structures (provenance dict)
- No new fields added to CapabilityContract dataclass
- No Sustain-specific shortcuts
- No schema changes to EvidenceRecord
- No policy weakening

### 4. Legacy Record Handling

Historical records that predate baseline_overrides (like 16.5.43.2) are correctly identified as missing context:
- Status marked as "PARTIAL" (some have, some don't)
- Missing records explicitly listed in provenance
- Limitation recorded in contract to indicate context is UNDERSTATED, not absent

## Results

### Sustain Contract Audit

**Target**: envelope_field_sustain
**Status**: CAUSAL_VERIFIED (verified - no regression)
**Supporting evidence**: 
- 16.5.43.2-CORPUS-ENV-SUSTAIN-CORRECTED (legacy, no baseline_overrides)
- 16.5.45-CORPUS-ENV-SUSTAIN-REVALIDATION (repaired, has baseline_overrides)

**Provenance exposed**:
- ✓ mutation_target_path: Env0.plainParams.kParamSustain
- ✓ measurement_definition_id: sustain_window_rms_db:c092f5a1078d
- ✓ shared_context.status: PARTIAL
- ✓ shared_context.baseline_overrides: [{target_path: Env0.plainParams.kParamDecay, value: 0.02}]
- ✓ supporting_evidence: both records preserved
- ✓ measurement_definition_ids: exposed for traceability

### Regression Check

**Before**: 13 CAUSAL_VERIFIED, 0 STRUCTURAL_ONLY, 1 NEGATIVE_EVIDENCE
**After**:  13 CAUSAL_VERIFIED, 0 STRUCTURAL_ONLY, 1 NEGATIVE_EVIDENCE

✓ **No regressions detected**

All 13 previously CAUSAL_VERIFIED contracts remain at that status.
No previously stronger contracts were weakened.

### Admission Tests

✓ All records passed EvidenceDispositionGate.require_admissible()
✓ No rejections in cumulative promotion
✓ Repaired sustain record fingerprint verified: b9484d370ae915b48f6905b91ca8820cb339aefb889f3c83df288a8d2dce8b60

## Artifacts

- **Step script**: experiments/step16_5_48_shared_context_provenance.py
- **Audit file**: experiments/16_5_48_SHARED_CONTEXT_PROVENANCE_AUDIT.json
- **Rebuilt contracts**: experiments/_capability_contracts.pkl (14 contracts, 1 sustain-related)
- **Verification script**: experiments/verify_sustain_provenance.py

## Compiler Integration

The compiler can now determine what baseline context was established for each capability:

```python
for contract in inventory.get("envelope_field_sustain", []):
    prov = contract.provenance
    if "shared_context" in prov:
        context = prov["shared_context"]
        if context["status"] == "IDENTICAL":
            # All supporting records agree on baseline
            use(context["baseline_overrides"])
        elif context["status"] == "PARTIAL":
            # Some records have context, some don't (legacy)
            warn(f"Partial context: {context['records_missing_baseline_overrides']} lack baseline_overrides")
            use(context.get("baseline_overrides"))
        elif context["status"] == "CONFLICTING":
            # Records disagree on baseline
            reject("Conflicting baseline context")
```

## Decision

**SHARED_CONTEXT_PROVENANCE_COMPLETE**

The evidence → ClaimGroup → CapabilityContract provenance path is now repaired.
Shared baseline_overrides/context from admitted EvidenceRecords is exposed through
existing generic contract structures, with no schema changes or policy weakening.
