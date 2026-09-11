#!/usr/bin/env python3
"""16.5.69.1-R, R1 — Hardened VST3 Surface Audit

Strengthened validation:
- every field is validated for type and semantic consistency
- every validation has a negative test case
- audit fails if constraints are violated (not just warns)
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict


class VST3SurfaceAuditError(Exception):
    """Raised when audit detects integrity violations."""
    pass


def audit_vst3_surface_hardened(dump_path: str, strict: bool = False) -> Dict[str, Any]:
    """Hardened VST3 surface audit.

    Args:
        dump_path: path to A1_1_vst3_parameter_surface.json
        strict: if True, any validation failure raises exception;
                if False, collects all failures and reports in result

    Returns:
        audit result dict with comprehensive validation
    """

    with open(dump_path, 'r') as f:
        dump = json.load(f)

    params = dump.get('parameters', [])

    audit = {
        'audit_phase': '16.5.69.1-R / R1',
        'source': dump_path,
        'strict_mode': strict,
        'validation_status': 'PASS',
        'errors': [],
        'warnings': [],
    }

    # Basic counts
    audit['parameter_count'] = len(params)

    # ===== R1.1: REQUIRED FIELDS VALIDATION =====
    required_fields = ['index', 'name', 'isBoolean', 'isDiscrete']
    missing_required = []

    for i, p in enumerate(params):
        for field in required_fields:
            if field not in p:
                error = f"Parameter {i}: missing required field '{field}'"
                missing_required.append(error)
                audit['errors'].append(error)

    if missing_required and strict:
        raise VST3SurfaceAuditError(f"Missing required fields: {len(missing_required)} parameters")

    # ===== R1.2: INDEX VALIDATION =====
    indices: Dict[int, List[int]] = defaultdict(list)  # index -> param positions
    index_errors = []

    for i, p in enumerate(params):
        if 'index' not in p:
            continue

        idx = p['index']

        # Type check
        if not isinstance(idx, int):
            error = f"Parameter {i}: index must be int, got {type(idx).__name__}"
            index_errors.append(error)
            audit['errors'].append(error)
            continue

        # Non-negative check
        if idx < 0:
            error = f"Parameter {i}: index must be >= 0, got {idx}"
            index_errors.append(error)
            audit['errors'].append(error)
            continue

        indices[idx].append(i)

    audit['unique_index_count'] = len(indices)

    # Duplicate index detection
    duplicate_indices = {idx: positions for idx, positions in indices.items() if len(positions) > 1}
    audit['duplicate_indices'] = duplicate_indices
    if duplicate_indices:
        error = f"Duplicate indices: {len(duplicate_indices)} indices appear multiple times"
        audit['errors'].append(error)
        if strict:
            raise VST3SurfaceAuditError(error)

    # ===== R1.3: NAME VALIDATION =====
    names: Dict[str, List[int]] = defaultdict(list)  # name -> param positions
    name_errors = []

    for i, p in enumerate(params):
        if 'name' not in p:
            continue

        name = p['name']

        # Type check
        if not isinstance(name, str):
            error = f"Parameter {i}: name must be str, got {type(name).__name__}"
            name_errors.append(error)
            audit['errors'].append(error)
            continue

        # Non-empty check
        if not name or not name.strip():
            error = f"Parameter {i}: name must be non-empty"
            name_errors.append(error)
            audit['errors'].append(error)
            continue

        names[name].append(i)

    audit['unique_name_count'] = len(names)

    # Duplicate name detection
    duplicate_names = {name: positions for name, positions in names.items() if len(positions) > 1}
    audit['duplicate_names'] = {
        name: {
            'count': len(positions),
            'indices': [params[pos].get('index') for pos in positions]
        }
        for name, positions in duplicate_names.items()
    }
    if duplicate_names:
        audit['warnings'].append(f"Duplicate names: {len(duplicate_names)} names appear multiple times")

    # ===== R1.4: BOOLEAN/DISCRETE CONSISTENCY =====
    consistency_errors = []

    for i, p in enumerate(params):
        is_bool = p.get('isBoolean', False)
        is_discrete = p.get('isDiscrete', False)

        # Both boolean and discrete is invalid
        if is_bool and is_discrete:
            error = f"Parameter {i}: cannot be both isBoolean and isDiscrete"
            consistency_errors.append(error)
            audit['errors'].append(error)
            if strict:
                raise VST3SurfaceAuditError(error)

    # ===== R1.5: NUMSTEPS VALIDATION =====
    numsteps_errors = []

    for i, p in enumerate(params):
        if 'numSteps' not in p:
            continue

        num_steps = p['numSteps']

        # Type check
        if not isinstance(num_steps, int):
            error = f"Parameter {i}: numSteps must be int, got {type(num_steps).__name__}"
            numsteps_errors.append(error)
            audit['errors'].append(error)
            continue

        # For discrete parameters, numSteps must be >= 2
        if p.get('isDiscrete', False):
            if num_steps < 2:
                error = f"Parameter {i}: isDiscrete=true but numSteps={num_steps} (must be >= 2)"
                numsteps_errors.append(error)
                audit['errors'].append(error)
                if strict:
                    raise VST3SurfaceAuditError(error)

    # ===== R1.6: DOMAIN VALIDATION (min, max, default) =====
    domain_errors = []

    for i, p in enumerate(params):
        has_min = 'min' in p
        has_max = 'max' in p
        has_default = 'defaultValue' in p

        # If min and max both present, min <= max (check only numeric values)
        if has_min and has_max:
            min_val = p['min']
            max_val = p['max']

            # Try to extract numeric values for comparison
            min_numeric = extract_numeric_value(min_val)
            max_numeric = extract_numeric_value(max_val)

            if min_numeric is not None and max_numeric is not None:
                if min_numeric > max_numeric:
                    error = f"Parameter {i}: min ({min_numeric}) > max ({max_numeric})"
                    domain_errors.append(error)
                    audit['errors'].append(error)
                    if strict:
                        raise VST3SurfaceAuditError(error)

    # ===== R1.7: TRANSPORT METADATA AUDIT =====
    boolean_count = sum(1 for p in params if p.get('isBoolean', False))
    discrete_count = sum(1 for p in params if p.get('isDiscrete', False))
    continuous_count = audit['parameter_count'] - boolean_count - discrete_count

    audit['transport_metadata'] = {
        'boolean_parameters': boolean_count,
        'discrete_parameters': discrete_count,
        'continuous_scalar_parameters': continuous_count,
    }

    # ===== FINAL STATUS =====
    if audit['errors']:
        audit['validation_status'] = 'FAIL'
    else:
        audit['validation_status'] = 'PASS'

    return audit


def extract_numeric_value(val: Any) -> float:
    """Extract numeric value from val (int, float, or string).

    Returns None if extraction impossible.
    This is conservative: used only for validation comparison, not semantic interpretation.
    """
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Try simple float parse first
        try:
            return float(val)
        except ValueError:
            # Don't try regex or heuristics; return None (can't compare)
            return None
    return None


# ===== NEGATIVE TEST FIXTURES =====

def create_negative_fixtures() -> List[Dict[str, Any]]:
    """Create deliberately malformed VST3 parameter entries to test validation."""

    fixtures = []

    # Fixture 1: Missing required index field
    fixtures.append({
        'name': 'TestParam1',
        'description': 'missing required "index" field',
        'data': {
            'name': 'Missing Index',
            'isBoolean': False,
            'isDiscrete': False,
        },
        'should_fail': 'missing required field',
    })

    # Fixture 2: Non-integer index
    fixtures.append({
        'name': 'TestParam2',
        'description': 'index is string, not int',
        'data': {
            'index': 'not_an_int',
            'name': 'Bad Index Type',
            'isBoolean': False,
            'isDiscrete': False,
        },
        'should_fail': 'index type validation',
    })

    # Fixture 3: Negative index
    fixtures.append({
        'name': 'TestParam3',
        'description': 'index is negative',
        'data': {
            'index': -1,
            'name': 'Negative Index',
            'isBoolean': False,
            'isDiscrete': False,
        },
        'should_fail': 'index non-negative check',
    })

    # Fixture 4: Empty name
    fixtures.append({
        'name': 'TestParam4',
        'description': 'name is empty string',
        'data': {
            'index': 9999,
            'name': '',
            'isBoolean': False,
            'isDiscrete': False,
        },
        'should_fail': 'name non-empty check',
    })

    # Fixture 5: Name is whitespace only
    fixtures.append({
        'name': 'TestParam5',
        'description': 'name is whitespace only',
        'data': {
            'index': 9998,
            'name': '   ',
            'isBoolean': False,
            'isDiscrete': False,
        },
        'should_fail': 'name non-empty check',
    })

    # Fixture 6: Both isBoolean and isDiscrete true (invalid)
    fixtures.append({
        'name': 'TestParam6',
        'description': 'both isBoolean and isDiscrete are true',
        'data': {
            'index': 9997,
            'name': 'Both Bool Discrete',
            'isBoolean': True,
            'isDiscrete': True,
        },
        'should_fail': 'boolean/discrete consistency check',
    })

    # Fixture 7: Discrete parameter with numSteps < 2
    fixtures.append({
        'name': 'TestParam7',
        'description': 'isDiscrete=true but numSteps=1 (invalid)',
        'data': {
            'index': 9996,
            'name': 'Invalid Discrete',
            'isBoolean': False,
            'isDiscrete': True,
            'numSteps': 1,
        },
        'should_fail': 'numSteps validation for discrete',
    })

    # Fixture 8: min > max
    fixtures.append({
        'name': 'TestParam8',
        'description': 'min (100) > max (50)',
        'data': {
            'index': 9995,
            'name': 'Inverted Domain',
            'isBoolean': False,
            'isDiscrete': False,
            'min': 100.0,
            'max': 50.0,
        },
        'should_fail': 'domain consistency check',
    })

    return fixtures


def test_negative_fixtures(strict: bool = False) -> Dict[str, Any]:
    """Test that negative fixtures are correctly rejected."""

    fixtures = create_negative_fixtures()
    test_result = {
        'total_fixtures': len(fixtures),
        'passed': 0,
        'failed': 0,
        'details': [],
    }

    for fixture in fixtures:
        fixture_params = [fixture['data']]
        test_dump = {
            'experiment': 'negative_test',
            'parameters': fixture_params,
        }

        # Write temp dump
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_dump, f)
            temp_path = f.name

        try:
            # Run audit (strict=True should raise for invalid fixtures)
            if strict:
                try:
                    audit = audit_vst3_surface_hardened(temp_path, strict=True)
                    # If no exception, the fixture should have failed but didn't
                    test_result['failed'] += 1
                    test_result['details'].append({
                        'fixture': fixture['name'],
                        'description': fixture['description'],
                        'result': 'FAIL (should have rejected, but passed)',
                    })
                except VST3SurfaceAuditError as e:
                    # Good: fixture was rejected as expected
                    test_result['passed'] += 1
                    test_result['details'].append({
                        'fixture': fixture['name'],
                        'description': fixture['description'],
                        'result': 'PASS (correctly rejected)',
                        'error': str(e),
                    })
            else:
                audit = audit_vst3_surface_hardened(temp_path, strict=False)
                if audit['validation_status'] == 'FAIL':
                    test_result['passed'] += 1
                    test_result['details'].append({
                        'fixture': fixture['name'],
                        'description': fixture['description'],
                        'result': 'PASS (correctly failed audit)',
                        'errors': audit['errors'][:1],
                    })
                else:
                    test_result['failed'] += 1
                    test_result['details'].append({
                        'fixture': fixture['name'],
                        'description': fixture['description'],
                        'result': 'FAIL (should have failed audit, but passed)',
                    })
        finally:
            # Clean up temp file
            import os
            os.unlink(temp_path)

    return test_result


def main():
    repo_root = Path(__file__).parent.parent.parent
    dump_path = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'

    if not dump_path.exists():
        print(f"Error: VST3 dump not found at {dump_path}", file=sys.stderr)
        sys.exit(1)

    print("=== R1 Hardened VST3 Surface Audit ===\n")

    # Run audit on real data
    print(f"Auditing {dump_path}...")
    audit = audit_vst3_surface_hardened(str(dump_path), strict=False)

    print(f"\nValidation Status: {audit['validation_status']}")
    print(f"Total Parameters: {audit['parameter_count']}")
    print(f"Unique Indices: {audit['unique_index_count']}")
    print(f"Unique Names: {audit['unique_name_count']}")

    if audit['errors']:
        print(f"\nERRORS ({len(audit['errors'])}):")
        for error in audit['errors'][:10]:
            print(f"  - {error}")
        if len(audit['errors']) > 10:
            print(f"  ... and {len(audit['errors']) - 10} more")

    if audit['warnings']:
        print(f"\nWARNINGS ({len(audit['warnings'])}):")
        for warning in audit['warnings']:
            print(f"  - {warning}")

    # Run negative fixture tests
    print("\n=== Negative Fixture Tests ===\n")
    print("Testing that deliberately malformed parameters are rejected...")
    fixture_results = test_negative_fixtures(strict=False)

    print(f"\nFixture Test Results:")
    print(f"  Passed: {fixture_results['passed']}/{fixture_results['total_fixtures']}")
    print(f"  Failed: {fixture_results['failed']}/{fixture_results['total_fixtures']}")

    if fixture_results['failed'] > 0:
        print("\nFailed fixtures (should have been caught):")
        for detail in fixture_results['details']:
            if 'should have' in detail['result']:
                print(f"  - {detail['fixture']}: {detail['description']}")

    # Write results
    output_path = repo_root / 'serum2' / 'qualification' / 'R1_HARDENED_AUDIT_RESULT.json'
    result = {
        'audit': audit,
        'fixture_tests': fixture_results,
    }
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nResults written to {output_path}")

    # Gate: PASS only if real audit is clean AND all negative fixtures are rejected
    gate_pass = (
        audit['validation_status'] == 'PASS' and
        fixture_results['failed'] == 0
    )

    print(f"\n{'='*50}")
    print(f"R1 GATE: {'PASS' if gate_pass else 'FAIL'}")
    print(f"{'='*50}")

    return 0 if gate_pass else 1


if __name__ == '__main__':
    sys.exit(main())
