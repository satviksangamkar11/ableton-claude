#!/usr/bin/env python3
"""16.5.69.1-R, R5 — Registry Integrity Adversarial Test Suite

Test that the final R3 registry:
- Rejects corrupted identity
- Rejects fabricated semantic classification
- Rejects heuristic domain values
- Maintains collision detection
- Accepts legitimate structure
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import tempfile
import os


class RegistryIntegrityError(Exception):
    """Raised when registry integrity test fails."""
    pass


def load_r3_registry(registry_path: str) -> Dict[str, Any]:
    """Load the R3 registry result."""
    with open(registry_path, 'r') as f:
        return json.load(f)


def create_adversarial_registry_fixture(
    base_registry: Dict[str, Any],
    fixture_name: str,
) -> Dict[str, Any]:
    """Create deliberately corrupted registry for testing.

    Args:
        base_registry: R3 registry result
        fixture_name: name of the corruption to apply

    Returns:
        Corrupted registry copy
    """

    corrupted = json.loads(json.dumps(base_registry))  # Deep copy

    entries = corrupted.get('entries', [])

    if fixture_name == 'R5-1_RemoveIdentity':
        # Remove required semantic_id field
        if entries:
            del entries[0]['semantic_id']

    elif fixture_name == 'R5-2_ChangeIndex':
        # Change VST3 index to an out-of-range value
        if entries:
            entries[0]['vst3_index'] = 99999

    elif fixture_name == 'R5-3_ChangeVST3Name':
        # Change VST3 name to nonexistent value
        if entries:
            entries[0]['vst3_name'] = 'CORRUPTED_PARAMETER_NAME'

    elif fixture_name == 'R5-4_FabricateSemanticClass':
        # Set semantic_mutation_class when it should be None
        if entries:
            entries[0]['semantic_mutation_class'] = 'BOOLEAN'
            entries[0]['semantic_classification_status'] = 'FABRICATED'

    elif fixture_name == 'R5-5_HeuristicDomain':
        # Set min_raw/max_raw to guessed numeric values
        if entries:
            entries[0]['min_raw'] = 0.0
            entries[0]['max_raw'] = 1.0
            entries[0]['default_raw'] = 0.5

    elif fixture_name == 'R5-6_DuplicateVST3Index':
        # Create collision: two entries with same VST3 index
        if len(entries) > 1:
            entries[1]['vst3_index'] = entries[0]['vst3_index']

    elif fixture_name == 'R5-7_InsertNonexistentTarget':
        # Add an entry with invalid semantic_id
        fake_entry = {
            'semantic_id': 'FAKE_NONEXISTENT_TARGET',
            'capability_key': 'fake_capability',
            'vst3_name': 'Fake Parameter',
            'vst3_index': 99998,
            'vst3_transport_kind': 'SCALAR',
            'is_boolean': False,
            'is_discrete': False,
            'num_steps': None,
            'min_raw': None,
            'max_raw': None,
            'default_raw': None,
            'semantic_mutation_class': None,
            'semantic_classification_status': 'UNCLASSIFIED',
            'resolution_status': 'FAKE',
            'mapping_basis': 'CORRUPTED',
        }
        entries.append(fake_entry)

    elif fixture_name == 'R5-P1_ValidRegistry':
        # No corruption; this is positive test
        pass

    else:
        raise ValueError(f"Unknown fixture: {fixture_name}")

    corrupted['entries'] = entries
    return corrupted


def validate_registry_integrity(
    targets_module_path: str,
    registry: Dict[str, Any],
    fixture_name: str,
    vst3_dump_path: str = None,
) -> tuple[bool, List[str]]:
    """Validate registry integrity.

    Returns:
        (is_valid, error_messages)
    """

    errors = []

    # Load targets.py to verify semantic targets exist
    import sys
    repo_root = Path(__file__).parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from serum2.compiler import targets

    valid_semantic_ids = {sid for sid in targets.SEMANTIC_TARGETS.keys()}

    # Load VST3 dump to validate identities
    if vst3_dump_path is None:
        vst3_dump_path = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'

    vst3_by_name = {}
    if vst3_dump_path.exists() if isinstance(vst3_dump_path, Path) else Path(vst3_dump_path).exists():
        with open(vst3_dump_path, 'r') as f:
            dump = json.load(f)
        for p in dump.get('parameters', []):
            vst3_by_name[p.get('name')] = p.get('index')

    entries = registry.get('entries', [])

    # Check 1: All entries have required fields
    for i, entry in enumerate(entries):
        required_fields = [
            'semantic_id', 'capability_key', 'vst3_name', 'vst3_index',
            'vst3_transport_kind', 'is_boolean', 'is_discrete',
            'semantic_mutation_class', 'semantic_classification_status'
        ]
        for field in required_fields:
            if field not in entry:
                errors.append(f"Entry {i} missing field '{field}'")

    # Check 2: All semantic_ids exist in targets.py
    for i, entry in enumerate(entries):
        sid = entry.get('semantic_id')
        if sid and sid not in valid_semantic_ids:
            errors.append(
                f"Entry {i} references nonexistent semantic_id '{sid}'"
            )

    # Check 3: No duplicate VST3 indices
    indices_seen = {}
    for i, entry in enumerate(entries):
        idx = entry.get('vst3_index')
        if idx in indices_seen:
            errors.append(
                f"Duplicate VST3 index {idx} at entries {indices_seen[idx]} and {i}"
            )
        if idx is not None:
            indices_seen[idx] = i

    # Check 4: semantic_mutation_class must be None
    for i, entry in enumerate(entries):
        smc = entry.get('semantic_mutation_class')
        if smc is not None:
            errors.append(
                f"Entry {i} has fabricated semantic_mutation_class={smc} (must be None)"
            )

    # Check 5: semantic_classification_status must be UNCLASSIFIED
    for i, entry in enumerate(entries):
        scs = entry.get('semantic_classification_status')
        if scs != 'UNCLASSIFIED':
            errors.append(
                f"Entry {i} has invalid semantic_classification_status={scs} (must be UNCLASSIFIED)"
            )

    # Check 6: Raw domain values must not be guessed numerics
    # (If they're numeric in the dump, that's fine. If they're guessed 0.0/1.0, that's bad)
    # For now, just check they exist and are the right type
    for i, entry in enumerate(entries):
        min_raw = entry.get('min_raw')
        max_raw = entry.get('max_raw')
        # If both are numeric 0.0 and 1.0 and defaults to 0.5, likely guessed
        if (isinstance(min_raw, (int, float)) and min_raw == 0.0 and
            isinstance(max_raw, (int, float)) and max_raw == 1.0 and
            entry.get('default_raw') == 0.5):
            errors.append(
                f"Entry {i} has suspicious heuristic domain (0.0-1.0, default 0.5)"
            )

    # Check 7: VST3 identities must be valid and consistent with dump
    for i, entry in enumerate(entries):
        vst3_name = entry.get('vst3_name')
        vst3_index = entry.get('vst3_index')

        # Name must exist in VST3 dump
        if vst3_by_name and vst3_name not in vst3_by_name:
            errors.append(
                f"Entry {i}: VST3 name '{vst3_name}' not found in VST3 dump"
            )

        # If found, index must match
        if vst3_by_name and vst3_name in vst3_by_name:
            actual_index = vst3_by_name[vst3_name]
            if vst3_index != actual_index:
                errors.append(
                    f"Entry {i}: VST3 index mismatch for '{vst3_name}': "
                    f"registry says {vst3_index}, dump says {actual_index}"
                )

        # Index must be in valid range
        if isinstance(vst3_index, int) and (vst3_index < 0 or vst3_index > 2622):
            errors.append(
                f"Entry {i}: VST3 index {vst3_index} out of valid range (0-2622)"
            )

    return (len(errors) == 0, errors)


def test_registry_integrity_adversarial(
    targets_module_path: str,
    registry_path: str,
    vst3_dump_path: str = None,
) -> Dict[str, Any]:
    """Test registry integrity with adversarial fixtures."""

    base_registry = load_r3_registry(registry_path)

    test_result = {
        'total_fixtures': 0,
        'passed': 0,
        'failed': 0,
        'details': [],
    }

    # Fixture specifications
    fixtures = [
        {'name': 'R5-1_RemoveIdentity', 'should_fail': True},
        {'name': 'R5-2_ChangeIndex', 'should_fail': True},
        {'name': 'R5-3_ChangeVST3Name', 'should_fail': True},
        {'name': 'R5-4_FabricateSemanticClass', 'should_fail': True},
        {'name': 'R5-5_HeuristicDomain', 'should_fail': True},
        {'name': 'R5-6_DuplicateVST3Index', 'should_fail': True},
        {'name': 'R5-7_InsertNonexistentTarget', 'should_fail': True},
        {'name': 'R5-P1_ValidRegistry', 'should_fail': False},
    ]

    for fixture_spec in fixtures:
        test_result['total_fixtures'] += 1
        fixture_name = fixture_spec['name']
        should_fail = fixture_spec['should_fail']

        try:
            # Create corrupted registry
            corrupted = create_adversarial_registry_fixture(
                base_registry,
                fixture_name
            )

            # Validate
            is_valid, errors = validate_registry_integrity(
                str(Path(__file__).parent.parent.parent / 'serum2' / 'compiler' / 'targets.py'),
                corrupted,
                fixture_name,
                str(vst3_dump_path) if vst3_dump_path else None
            )

            # Check outcome
            if should_fail:
                # Negative test: should be invalid
                if not is_valid:
                    test_result['passed'] += 1
                    test_result['details'].append({
                        'fixture': fixture_name,
                        'expected': 'INVALID',
                        'actual': 'INVALID',
                        'result': 'PASS (correctly rejected)',
                        'errors': errors[:2],
                    })
                else:
                    test_result['failed'] += 1
                    test_result['details'].append({
                        'fixture': fixture_name,
                        'expected': 'INVALID',
                        'actual': 'VALID',
                        'result': 'FAIL (should have been rejected)',
                    })
            else:
                # Positive test: should be valid
                if is_valid:
                    test_result['passed'] += 1
                    test_result['details'].append({
                        'fixture': fixture_name,
                        'expected': 'VALID',
                        'actual': 'VALID',
                        'result': 'PASS (correctly accepted)',
                    })
                else:
                    test_result['failed'] += 1
                    test_result['details'].append({
                        'fixture': fixture_name,
                        'expected': 'VALID',
                        'actual': 'INVALID',
                        'result': 'FAIL (should have been accepted)',
                        'errors': errors[:2],
                    })

        except Exception as e:
            test_result['failed'] += 1
            test_result['details'].append({
                'fixture': fixture_name,
                'result': 'ERROR',
                'error': str(e),
            })

    return test_result


def main():
    repo_root = Path(__file__).parent.parent.parent

    registry_path = repo_root / 'serum2' / 'qualification' / 'R3_HARDENED_REGISTRY_RESULT.json'
    targets_py = repo_root / 'serum2' / 'compiler' / 'targets.py'
    vst3_dump = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'

    if not registry_path.exists():
        print(f"Error: {registry_path} not found", file=sys.stderr)
        sys.exit(1)

    print("=== R5 Registry Integrity Adversarial Test Suite ===\n")

    print("Testing registry with deliberate corruptions...")
    test_result = test_registry_integrity_adversarial(
        str(targets_py),
        str(registry_path),
        str(vst3_dump),
    )

    print(f"\nTest Results:")
    print(f"  Total: {test_result['total_fixtures']}")
    print(f"  Passed: {test_result['passed']}")
    print(f"  Failed: {test_result['failed']}")

    if test_result['details']:
        print(f"\nDetails:")
        for detail in test_result['details']:
            status = detail.get('result', 'UNKNOWN')
            fixture = detail.get('fixture', 'unknown')
            print(f"  {fixture}: {status}")

    # Write result
    output_path = repo_root / 'serum2' / 'qualification' / 'R5_REGISTRY_INTEGRITY_TEST_RESULT.json'
    with open(output_path, 'w') as f:
        json.dump(test_result, f, indent=2)

    print(f"\nResults written to {output_path}")

    gate_pass = (
        test_result['passed'] == test_result['total_fixtures'] and
        test_result['failed'] == 0
    )

    print(f"\n{'='*50}")
    print(f"R5 GATE: {'PASS' if gate_pass else 'FAIL'}")
    print(f"{'='*50}")

    return 0 if gate_pass else 1


if __name__ == '__main__':
    sys.exit(main())
