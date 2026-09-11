#!/usr/bin/env python3
"""16.5.69.1-R, R2 — Hardened Semantic Mapping Audit

Enforces real mapping integrity gates, not declarative ones.

Critical: semantic→VST3 collision detection.
Every validation has an adversarial fixture.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict


class SemanticMappingAuditError(Exception):
    """Raised when audit detects mapping integrity violations."""
    pass


def audit_semantic_mapping_hardened(
    targets_module_path: str,
    mapping_file_path: str,
    vst3_dump_path: str,
    vst3_audit_path: str,
    strict: bool = False
) -> Dict[str, Any]:
    """Hardened semantic mapping audit.

    Enforces real gates, not declarations.
    """

    # Load targets.py
    repo_root = Path(__file__).parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from serum2.compiler import targets

    # Load mapping file
    with open(mapping_file_path, 'r') as f:
        mapping_data = json.load(f)

    # Validate mapping schema
    if not isinstance(mapping_data, dict):
        raise SemanticMappingAuditError("mapping_data must be a dict")

    mappings = mapping_data.get('mappings', {})
    if not isinstance(mappings, dict):
        raise SemanticMappingAuditError("mappings must be a dict")

    # Load VST3 dump
    with open(vst3_dump_path, 'r') as f:
        vst3_dump = json.load(f)
    vst3_params = vst3_dump.get('parameters', [])

    # Load VST3 audit for duplicate detection
    with open(vst3_audit_path, 'r') as f:
        vst3_audit = json.load(f)
    duplicate_vst3_names = vst3_audit.get('duplicate_names', {})

    # Build VST3 lookup: name -> indices
    vst3_by_name: Dict[str, List[int]] = defaultdict(list)
    for p in vst3_params:
        name = p.get('name')
        idx = p.get('index')
        if name and idx is not None:
            vst3_by_name[name].append(idx)

    # Audit result
    audit = {
        'audit_phase': '16.5.69.1-R / R2',
        'strict_mode': strict,
        'validation_status': 'PASS',
        'errors': [],
        'warnings': [],
        'semantic_targets': len(targets.SEMANTIC_TARGETS),
        'mappings_provided': len(mappings),
        'mappings': [],
        'collisions': [],
        'summary': {},
    }

    resolution_counts = defaultdict(int)

    # ===== R2.1: VALIDATE EACH MAPPING =====

    # First, validate all mapping keys exist in targets.py
    for capability_key in mappings.keys():
        # Check if this capability_key exists in SEMANTIC_TARGETS
        found = False
        for semantic_id, target_ref in targets.SEMANTIC_TARGETS.items():
            if target_ref.capability_key == capability_key:
                found = True
                break
        if not found:
            error = f"Mapping contains unknown capability_key '{capability_key}' not in targets.py"
            audit['errors'].append(error)
            if strict:
                raise SemanticMappingAuditError(error)

    # First pass: collect all VST3 targets mapped to
    vst3_targets_used: Dict[str, List[str]] = defaultdict(list)  # vst3_name -> [semantic_ids]

    for semantic_id, target_ref in sorted(targets.SEMANTIC_TARGETS.items()):
        capability_key = target_ref.capability_key
        vst3_name = mappings.get(capability_key)

        entry = {
            'semantic_id': semantic_id,
            'capability_key': capability_key,
            'mapped_vst3_name': vst3_name,
            'resolution_status': None,
            'vst3_indices': [],
            'issues': [],
        }

        # ===== R2.1b: No mapping provided =====
        if vst3_name is None:
            entry['resolution_status'] = 'UNMAPPED'
            entry['issues'].append('No mapping provided')
            resolution_counts['UNMAPPED'] += 1
            audit['mappings'].append(entry)
            continue

        # ===== R2.1c: VST3 name must be string =====
        if not isinstance(vst3_name, str):
            error = f"mapped VST3 name must be str, got {type(vst3_name).__name__}"
            entry['issues'].append(error)
            audit['errors'].append(error)
            entry['resolution_status'] = 'MALFORMED_MAPPING'
            if strict:
                raise SemanticMappingAuditError(error)
            resolution_counts[entry['resolution_status']] += 1
            audit['mappings'].append(entry)
            continue

        # ===== R2.1d: VST3 name must exist in dump =====
        if vst3_name not in vst3_by_name:
            entry['resolution_status'] = 'VST3_NAME_NOT_FOUND'
            error = f"VST3 name '{vst3_name}' not found in dump (mapping points to nonexistent parameter)"
            entry['issues'].append(error)
            audit['errors'].append(error)
            resolution_counts['VST3_NAME_NOT_FOUND'] += 1
            if strict:
                raise SemanticMappingAuditError(error)
            audit['mappings'].append(entry)
            continue

        # ===== R2.1e: VST3 name must be unique =====
        indices = vst3_by_name[vst3_name]
        if len(indices) > 1:
            entry['resolution_status'] = 'AMBIGUOUS_VST3_NAME'
            entry['vst3_indices'] = indices
            error = f"Ambiguous VST3 name for {semantic_id}: '{vst3_name}' appears at {len(indices)} indices"
            entry['issues'].append(error)
            audit['errors'].append(error)
            resolution_counts['AMBIGUOUS_VST3_NAME'] += 1
            if strict:
                raise SemanticMappingAuditError(error)
            audit['mappings'].append(entry)
            continue

        # ===== R2.1f: Successful resolution =====
        entry['resolution_status'] = 'RESOLVED'
        entry['vst3_indices'] = indices
        resolution_counts['RESOLVED'] += 1

        # Track this VST3 target
        vst3_targets_used[vst3_name].append(semantic_id)

        audit['mappings'].append(entry)

    # ===== R2.2: SEMANTIC→VST3 COLLISION DETECTION (CRITICAL) =====
    for vst3_name, semantic_ids in vst3_targets_used.items():
        if len(semantic_ids) > 1:
            # COLLISION: multiple semantic targets point to same VST3 parameter
            collision = {
                'vst3_name': vst3_name,
                'vst3_index': vst3_by_name[vst3_name][0],
                'semantic_ids': semantic_ids,
                'count': len(semantic_ids),
            }
            audit['collisions'].append(collision)
            error = f"Semantic collision: {semantic_ids} all map to VST3 '{vst3_name}'"
            audit['errors'].append(error)
            if strict:
                raise SemanticMappingAuditError(error)

    # ===== R2.3: GATE CALCULATION =====
    audit['summary'] = {
        'RESOLVED': resolution_counts['RESOLVED'],
        'UNMAPPED': resolution_counts['UNMAPPED'],
        'VST3_NAME_NOT_FOUND': resolution_counts['VST3_NAME_NOT_FOUND'],
        'AMBIGUOUS_VST3_NAME': resolution_counts['AMBIGUOUS_VST3_NAME'],
        'INVALID_SEMANTIC_KEY': resolution_counts['INVALID_SEMANTIC_KEY'],
        'MALFORMED_MAPPING': resolution_counts['MALFORMED_MAPPING'],
        'semantic_collisions': len(audit['collisions']),
    }

    # Final validation status
    if audit['errors']:
        audit['validation_status'] = 'FAIL'
    else:
        audit['validation_status'] = 'PASS'

    return audit


# ===== ADVERSARIAL TEST FIXTURES =====

def create_adversarial_fixtures(vst3_audit_path: str) -> List[Dict[str, Any]]:
    """Create deliberately corrupted mapping fixtures to test validation.

    Fixtures start from known-good mapping and corrupt specific aspects.
    """

    # Load R1 audit to get actual duplicate VST3 name
    with open(vst3_audit_path, 'r') as f:
        audit = json.load(f)
    duplicate_names = audit.get('duplicate_names', {})

    fixtures = []

    # R2-1: SEMANTIC COLLISION (CRITICAL)
    # Two semantic targets both claim the same unique VST3 parameter
    fixtures.append({
        'name': 'R2-1_SemanticCollision',
        'description': 'Two semantic targets both map to "A Level" (same unique VST3)',
        'mutation': {
            'oscillator_field_OSC-ENABLE': 'A Enable',  # Originally something else
            'oscillator_field_OSC-VOLUME': 'A Enable',  # COLLISION: same target
        },
        'should_fail': 'semantic_collision_detection',
        'expect_gate_fail': True,
    })

    # R2-2: INVALID EXISTING MAPPING
    # Change a currently-good mapping to a nonexistent VST3 name
    fixtures.append({
        'name': 'R2-2_InvalidExistingMapping',
        'description': 'Valid mapping changed to point to nonexistent VST3 parameter',
        'mutation': {
            'oscillator_field_OSC-VOLUME': 'THIS_DOES_NOT_EXIST_IN_VST3_DUMP',
        },
        'should_fail': 'vst3_name_not_found_in_existing_mapping',
        'expect_gate_fail': True,
    })

    # R2-3: AMBIGUOUS VST3 NAME
    # If duplicate names exist in VST3 dump, use one
    if duplicate_names:
        dup_name = list(duplicate_names.keys())[0]
        fixtures.append({
            'name': 'R2-3_AmbiguousVST3Name',
            'description': f'Valid mapping changed to point to ambiguous VST3 name "{dup_name}"',
            'mutation': {
                'oscillator_field_OSC-OCTAVE': dup_name,  # This name appears multiple times
            },
            'should_fail': 'ambiguous_vst3_name_for_existing_mapping',
            'expect_gate_fail': True,
        })

    # R2-4: MALFORMED MAPPING VALUE TYPE
    # Mapping value is not a string
    fixtures.append({
        'name': 'R2-4_MalformedMappingType',
        'description': 'Mapping value is int instead of string',
        'mutation': {
            'oscillator_field_OSC-VOLUME': 12345,  # Invalid type
        },
        'should_fail': 'malformed_mapping_type',
        'expect_gate_fail': True,
    })

    # R2-5: UNKNOWN MAPPING KEY
    # Mapping file contains a capability_key not in targets.py
    fixtures.append({
        'name': 'R2-5_UnknownMappingKey',
        'description': 'Mapping contains unknown capability_key not in targets.py',
        'mutation': {
            'fake_capability_key_that_does_not_exist': 'A Enable',
        },
        'should_fail': 'unknown_mapping_key_rejection',
        'expect_gate_fail': True,
        'note': 'Must validate against targets.py vocabulary',
    })

    # R2-P1: POSITIVE TEST - LEGITIMATE UNMAPPED
    # Do nothing to the mapping, just verify an unmapped target stays unmapped
    fixtures.append({
        'name': 'R2-P1_LegitimateUnmapped',
        'description': 'Unmapped semantic target remains unmapped (positive test)',
        'mutation': {},  # No changes
        'should_pass': 'unmapped_targets_allowed',
        'expect_gate_fail': False,
    })

    return fixtures


# R2 fixture expectations — explicit, not inferred
EXPECTED_FIXTURE_OUTCOMES = {
    'R2-1_SemanticCollision': 'FAIL',
    'R2-2_InvalidExistingMapping': 'FAIL',
    'R2-3_AmbiguousVST3Name': 'FAIL',
    'R2-4_MalformedMappingType': 'FAIL',
    'R2-5_UnknownMappingKey': 'FAIL',
    'R2-P1_LegitimateUnmapped': 'PASS',
}


def assert_fixture_outcome(
    fixture_name: str,
    actual_gate_status: str,
    expected: str,
) -> None:
    """Enforce that fixture behaves as expected."""
    if actual_gate_status != expected:
        raise AssertionError(
            f"{fixture_name}: expected gate={expected}, "
            f"but got gate={actual_gate_status}"
        )


def test_adversarial_fixtures(
    targets_module_path: str,
    vst3_dump_path: str,
    vst3_audit_path: str
) -> Dict[str, Any]:
    """Test that adversarial mapping fixtures are correctly rejected."""

    fixtures = create_adversarial_fixtures(vst3_audit_path)
    test_result = {
        'total_fixtures': len(fixtures),
        'passed': 0,
        'failed': 0,
        'details': [],
        'assertion_failures': [],
    }

    # Load real mapping as baseline
    repo_root = Path(__file__).parent.parent.parent
    real_mapping_path = repo_root / 'serum2' / 'qualification' / 'semantic_vst3_mapping.json'

    with open(real_mapping_path, 'r') as f:
        real_mapping = json.load(f)

    for fixture in fixtures:
        fixture_name = fixture['name']
        expected_outcome = EXPECTED_FIXTURE_OUTCOMES.get(fixture_name)

        if not expected_outcome:
            test_result['assertion_failures'].append({
                'fixture': fixture_name,
                'reason': 'fixture not in EXPECTED_FIXTURE_OUTCOMES',
            })
            test_result['failed'] += 1
            continue

        # Create modified mapping
        test_mapping = {
            'mapping_version': real_mapping.get('mapping_version'),
            'mappings': real_mapping.get('mappings', {}).copy(),
        }
        test_mapping['mappings'].update(fixture['mutation'])

        # Write to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_mapping, f)
            temp_path = f.name

        try:
            # Run audit (strict=False to collect errors)
            audit = audit_semantic_mapping_hardened(
                str(targets_module_path),
                temp_path,
                str(vst3_dump_path),
                str(vst3_audit_path),
                strict=False
            )

            actual_outcome = 'PASS' if audit['validation_status'] == 'PASS' else 'FAIL'

            # Verify against explicit expectation
            try:
                assert_fixture_outcome(fixture_name, actual_outcome, expected_outcome)
                test_result['passed'] += 1
                test_result['details'].append({
                    'fixture': fixture_name,
                    'description': fixture['description'],
                    'expected': expected_outcome,
                    'actual': actual_outcome,
                    'result': f'PASS (outcome={expected_outcome})',
                    'errors': audit['errors'][:1] if audit['errors'] else [],
                })
            except AssertionError as e:
                test_result['failed'] += 1
                test_result['assertion_failures'].append({
                    'fixture': fixture_name,
                    'assertion_error': str(e),
                })
                test_result['details'].append({
                    'fixture': fixture_name,
                    'description': fixture['description'],
                    'expected': expected_outcome,
                    'actual': actual_outcome,
                    'result': f'FAIL (assertion violated)',
                    'error': str(e),
                })

        finally:
            import os
            os.unlink(temp_path)

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

    print("=== R2 Hardened Semantic Mapping Audit ===\n")

    # Run audit on real data
    print("Auditing semantic->VST3 mapping...")
    audit = audit_semantic_mapping_hardened(
        str(targets_py),
        str(mapping_file),
        str(vst3_dump),
        str(vst3_audit),
        strict=False
    )

    print(f"\nValidation Status: {audit['validation_status']}")
    print(f"Semantic Targets: {audit['semantic_targets']}")
    print(f"Mappings Provided: {audit['mappings_provided']}")

    print(f"\nResolution Summary:")
    for status, count in sorted(audit['summary'].items()):
        if status != 'semantic_collisions':
            print(f"  {status:25s}: {count}")

    if audit['errors']:
        print(f"\nERRORS ({len(audit['errors'])}):")
        for error in audit['errors'][:5]:
            print(f"  - {error}")
        if len(audit['errors']) > 5:
            print(f"  ... and {len(audit['errors']) - 5} more")

    if audit['collisions']:
        print(f"\nSEMANTIC COLLISIONS ({len(audit['collisions'])}):")
        for collision in audit['collisions']:
            print(f"  - {collision['semantic_ids']} all -> {collision['vst3_name']}")

    # Run adversarial fixture tests
    print("\n=== Adversarial Fixture Tests ===\n")
    print("Testing that deliberately corrupted mappings are rejected...")
    fixture_results = test_adversarial_fixtures(
        str(targets_py),
        str(vst3_dump),
        str(vst3_audit)
    )

    print(f"\nFixture Test Results:")
    print(f"  Passed: {fixture_results['passed']}/{fixture_results['total_fixtures']}")
    print(f"  Failed: {fixture_results['failed']}/{fixture_results['total_fixtures']}")

    if fixture_results['failed'] > 0:
        print("\nFailed fixtures (should have been caught):")
        for detail in fixture_results['details']:
            if 'should have' in detail['result']:
                print(f"  - {detail['fixture']}: {detail['description']}")

    # Write results
    output_path = repo_root / 'serum2' / 'qualification' / 'R2_HARDENED_AUDIT_RESULT.json'
    result = {
        'audit': audit,
        'fixture_tests': fixture_results,
    }
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nResults written to {output_path}")

    # Gate: PASS only if real audit clean AND adversarial fixtures rejected
    gate_pass = (
        audit['validation_status'] == 'PASS' and
        len(audit['collisions']) == 0 and
        fixture_results['failed'] == 0
    )

    print(f"\n{'='*50}")
    print(f"R2 GATE: {'PASS' if gate_pass else 'FAIL'}")
    print(f"{'='*50}")

    return 0 if gate_pass else 1


if __name__ == '__main__':
    sys.exit(main())
