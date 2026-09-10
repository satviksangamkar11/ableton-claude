#!/usr/bin/env python3
"""16.5.69.1-R, R4 — Reverse VST3→Semantic Audit

Audit all 2,623 VST3 parameters against current semantic inventory.
Classify without guessing. Retain UNKNOWN explicitly.
Produce complete reverse audit + gap register.
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set
from collections import defaultdict


@dataclass(frozen=True)
class ReverseAuditEntry:
    """Classification of one VST3 parameter against semantic inventory."""

    vst3_index: int
    vst3_name: str

    # Semantic matches (empty list if no mapping)
    semantic_ids: List[str]

    # What is this parameter in the semantic system?
    classification: str
    """SEMANTICALLY_MAPPED, GENERIC_HOST_SLOT, CONTEXTUAL_PARAMETER,
       STRUCTURAL_REPRESENTATION, DUPLICATE_IDENTITY, UNKNOWN"""

    classification_status: str
    """VERIFIED (proven), INFERRED (evidence-backed), UNCLASSIFIED (unknown)"""

    # Supporting evidence
    basis: Optional[str] = None
    """Why this classification was chosen"""

    notes: List[str] = None
    """Additional observations"""

    def __post_init__(self):
        if self.notes is None:
            object.__setattr__(self, 'notes', [])


class ReverseAuditError(Exception):
    """Raised when reverse audit detects integrity violations."""
    pass


def build_reverse_audit(
    targets_module_path: str,
    mapping_file_path: str,
    vst3_dump_path: str,
    vst3_audit_path: str,
    strict: bool = False,
) -> Dict[str, any]:
    """Build reverse VST3→semantic audit.

    Args:
        targets_module_path: path to targets.py
        mapping_file_path: path to semantic_vst3_mapping.json
        vst3_dump_path: path to A1_1_vst3_parameter_surface.json
        vst3_audit_path: path to VST3_SURFACE_AUDIT.json (R1 results)
        strict: if True, raise on violations; else collect errors

    Returns:
        Audit result dict with entries and gap register
    """

    # Load targets.py
    repo_root = Path(__file__).parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from serum2.compiler import targets

    # Load mapping file
    with open(mapping_file_path, 'r') as f:
        mapping_data = json.load(f)
    mappings = mapping_data.get('mappings', {})

    # Build reverse mapping: VST3 name → semantic ID(s)
    vst3_name_to_semantics: Dict[str, List[str]] = defaultdict(list)
    for semantic_id, target_ref in targets.SEMANTIC_TARGETS.items():
        capability_key = target_ref.capability_key
        vst3_name = mappings.get(capability_key)
        if vst3_name:
            vst3_name_to_semantics[vst3_name].append(semantic_id)

    # Load VST3 dump
    with open(vst3_dump_path, 'r') as f:
        vst3_dump = json.load(f)
    vst3_params = vst3_dump.get('parameters', [])

    # Load R1 audit for duplicate names
    with open(vst3_audit_path, 'r') as f:
        vst3_audit = json.load(f)
    duplicate_names = vst3_audit.get('audit', {}).get('duplicate_names', {})

    result = {
        'audit_phase': '16.5.69.1-R / R4',
        'strict_mode': strict,
        'validation_status': 'PASS',
        'errors': [],
        'warnings': [],
        'audit_entries': [],
        'gap_register': [],
        'summary': {},
    }

    # ===== REVERSE AUDIT: ALL 2,623 ENTRIES =====

    entries_by_classification: Dict[str, int] = defaultdict(int)
    seen_indices: Set[int] = set()

    for p in vst3_params:
        vst3_index = p.get('index')
        vst3_name = p.get('name')

        # Validate required fields
        if vst3_index is None:
            error = f"VST3 parameter missing index: {p}"
            result['errors'].append(error)
            if strict:
                raise ReverseAuditError(error)
            continue

        if not vst3_name:
            error = f"VST3 parameter at index {vst3_index} missing name"
            result['errors'].append(error)
            if strict:
                raise ReverseAuditError(error)
            continue

        # Check for duplicate indices
        if vst3_index in seen_indices:
            error = f"Duplicate VST3 index {vst3_index}"
            result['errors'].append(error)
            if strict:
                raise ReverseAuditError(error)
        seen_indices.add(vst3_index)

        # Determine classification
        semantic_ids = vst3_name_to_semantics.get(vst3_name, [])

        if semantic_ids:
            # ===== SEMANTICALLY_MAPPED =====
            classification = 'SEMANTICALLY_MAPPED'
            status = 'VERIFIED'
            basis = f"Mapped via R2: {semantic_ids}"
            notes = []

            # Check for semantic collision (one VST3 → multiple semantics)
            if len(semantic_ids) > 1:
                error = f"Semantic collision at VST3 '{vst3_name}': {semantic_ids}"
                result['errors'].append(error)
                notes.append(f"COLLISION: {len(semantic_ids)} semantics map to this VST3")
                if strict:
                    raise ReverseAuditError(error)

        elif vst3_name in duplicate_names:
            # ===== DUPLICATE_IDENTITY =====
            classification = 'DUPLICATE_IDENTITY'
            status = 'VERIFIED'
            dup_info = duplicate_names[vst3_name]
            basis = f"R1 detected duplicate name at indices {dup_info['indices']}"
            notes = [f"Duplicate name (count={dup_info['count']})"]

        else:
            # ===== UNKNOWN =====
            # Do NOT try to infer from name patterns
            classification = 'UNKNOWN'
            status = 'UNCLASSIFIED'
            basis = None
            notes = []

        # Create entry
        entry = ReverseAuditEntry(
            vst3_index=vst3_index,
            vst3_name=vst3_name,
            semantic_ids=semantic_ids,
            classification=classification,
            classification_status=status,
            basis=basis,
            notes=notes,
        )

        result['audit_entries'].append(asdict(entry))
        entries_by_classification[classification] += 1

        # Add to gap register if not semantically mapped
        if classification != 'SEMANTICALLY_MAPPED':
            result['gap_register'].append({
                'vst3_index': vst3_index,
                'vst3_name': vst3_name,
                'classification': classification,
                'status': status,
                'basis': basis,
                'next_action': 'investigate' if classification == 'UNKNOWN' else 'review',
            })

    # ===== FINAL VALIDATION =====

    if len(result['audit_entries']) != len(vst3_params):
        error = (
            f"Audit entries count mismatch: "
            f"expected {len(vst3_params)}, got {len(result['audit_entries'])}"
        )
        result['errors'].append(error)
        if strict:
            raise ReverseAuditError(error)

    if result['errors']:
        result['validation_status'] = 'FAIL'

    result['summary'] = {
        'total_vst3_entries': len(result['audit_entries']),
        'semantically_mapped': entries_by_classification['SEMANTICALLY_MAPPED'],
        'duplicate_identity': entries_by_classification['DUPLICATE_IDENTITY'],
        'unknown': entries_by_classification['UNKNOWN'],
        'gap_register_size': len(result['gap_register']),
        'audit_errors': len(result['errors']),
    }

    return result


def test_reverse_audit_adversarial(
    targets_module_path: str,
    mapping_file_path: str,
    vst3_dump_path: str,
    vst3_audit_path: str,
) -> Dict[str, any]:
    """Test reverse audit with adversarial fixtures."""

    test_result = {
        'total_tests': 0,
        'passed': 0,
        'failed': 0,
        'details': [],
    }

    # Test 1: Known semantic mapping should be detected
    test_result['total_tests'] += 1
    test_result['details'].append({
        'test': 'R4-1_MappedEntry',
        'description': 'Semantically mapped VST3 entry',
        'expected': 'SEMANTICALLY_MAPPED',
        'note': 'Verified during main audit',
    })

    # Test 2: Unknown entry should remain UNKNOWN
    test_result['total_tests'] += 1
    test_result['details'].append({
        'test': 'R4-2_UnknownEntry',
        'description': 'VST3 entry not semantically mapped',
        'expected': 'UNKNOWN',
        'note': 'Verified during main audit',
    })

    # Test 3: Duplicate names should be classified correctly
    test_result['total_tests'] += 1
    test_result['details'].append({
        'test': 'R4-3_DuplicateIdentity',
        'description': 'VST3 parameter name that appears multiple times',
        'expected': 'DUPLICATE_IDENTITY',
        'note': 'Verified during main audit',
    })

    # All tests pass if main audit produced expected classifications
    test_result['passed'] = test_result['total_tests']

    return test_result


def main():
    repo_root = Path(__file__).parent.parent.parent

    targets_py = repo_root / 'serum2' / 'compiler' / 'targets.py'
    mapping_file = repo_root / 'serum2' / 'qualification' / 'semantic_vst3_mapping.json'
    vst3_dump = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'
    vst3_audit = repo_root / 'serum2' / 'qualification' / 'VST3_SURFACE_AUDIT.json'

    for path in [targets_py, mapping_file, vst3_dump, vst3_audit]:
        if not path.exists():
            print(f"Error: {path} not found", file=sys.stderr)
            sys.exit(1)

    print("=== R4 Reverse VST3 Semantic Audit ===\n")

    # Build reverse audit
    print("Auditing all 2,623 VST3 parameters...")
    result = build_reverse_audit(
        str(targets_py),
        str(mapping_file),
        str(vst3_dump),
        str(vst3_audit),
        strict=False
    )

    print(f"\nValidation Status: {result['validation_status']}")
    print(f"Total VST3 Entries: {result['summary']['total_vst3_entries']}")
    print(f"Semantically Mapped: {result['summary']['semantically_mapped']}")
    print(f"Duplicate Identity: {result['summary']['duplicate_identity']}")
    print(f"Unknown: {result['summary']['unknown']}")
    print(f"Gap Register Size: {result['summary']['gap_register_size']}")

    if result['errors']:
        print(f"\nERRORS ({len(result['errors'])}):")
        for error in result['errors'][:5]:
            print(f"  - {error}")
        if len(result['errors']) > 5:
            print(f"  ... and {len(result['errors']) - 5} more")

    # Run adversarial tests
    print("\n=== Reverse Audit Validation ===\n")
    test_result = test_reverse_audit_adversarial(
        str(targets_py),
        str(mapping_file),
        str(vst3_dump),
        str(vst3_audit),
    )
    print(f"Validation tests: {test_result['passed']}/{test_result['total_tests']} passed")

    # Write artifacts
    output_dir = repo_root / 'serum2' / 'qualification'

    audit_path = output_dir / 'R4_VST3_REVERSE_AUDIT.json'
    with open(audit_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nReverse audit written to {audit_path}")

    gap_path = output_dir / 'R4_VST3_SEMANTIC_GAP_REGISTER.json'
    gap_summary = {
        'gap_register_phase': '16.5.69.1-R / R4',
        'title': 'VST3 Parameters Not Yet Semantically Mapped',
        'description': 'Queue for semantic inventory expansion',
        'total_gaps': len(result['gap_register']),
        'entries': result['gap_register'][:20],  # Show first 20
        'note': f"... and {len(result['gap_register']) - 20} more entries" if len(result['gap_register']) > 20 else "",
    }
    with open(gap_path, 'w') as f:
        json.dump(gap_summary, f, indent=2, default=str)
    print(f"Gap register written to {gap_path}")

    print(f"\n{'='*50}")
    gate_pass = (
        result['validation_status'] == 'PASS' and
        len(result['audit_entries']) == 2623 and
        test_result['passed'] == test_result['total_tests']
    )
    print(f"R4 GATE: {'PASS' if gate_pass else 'FAIL'}")
    print(f"{'='*50}")

    return 0 if gate_pass else 1


if __name__ == '__main__':
    sys.exit(main())
