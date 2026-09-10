#!/usr/bin/env python3
"""16.5.69.1-R, R3 — Hardened Resolved Target Registry Builder

Builds conservative registry from qualified R2 mapping + R1 VST3 audit.
Refuses lossy data structures.
Preserves raw domain values.
No semantic classification.
No fabricated transport-kind inference.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from r3_resolved_target_record import ResolvedTarget


class RegistryBuilderError(Exception):
    """Raised when registry construction violates safety constraints."""
    pass


def get_unique_vst3_record(
    vst3_by_name: Dict[str, List[Dict[str, Any]]],
    name: str,
) -> Dict[str, Any]:
    """Retrieve a unique VST3 record by name.

    Enforces uniqueness even though R2 already guarantees it.
    This is a defensive check; registry builder should not depend
    on R2's work being correct.

    Args:
        vst3_by_name: dict mapping name → list of records
        name: VST3 parameter name to look up

    Returns:
        The unique VST3 record

    Raises:
        RegistryBuilderError: if not found or ambiguous
    """
    matches = vst3_by_name.get(name, [])

    if len(matches) == 0:
        raise RegistryBuilderError(
            f"VST3 parameter '{name}' not found in dump"
        )

    if len(matches) > 1:
        indices = [p["index"] for p in matches]
        raise RegistryBuilderError(
            f"VST3 parameter '{name}' is ambiguous: "
            f"appears at indices {indices}"
        )

    return matches[0]


def build_registry_hardened(
    targets_module_path: str,
    mapping_file_path: str,
    vst3_dump_path: str,
    vst3_audit_path: str,
    strict: bool = False,
) -> Dict[str, Any]:
    """Build conservative registry from R2 mapping + VST3 audit.

    Args:
        targets_module_path: path to targets.py
        mapping_file_path: path to semantic_vst3_mapping.json
        vst3_dump_path: path to A1_1_vst3_parameter_surface.json
        vst3_audit_path: path to VST3_SURFACE_AUDIT.json (R1 results)
        strict: if True, raise on any violation; else collect errors

    Returns:
        Registry result dict with entries and validation status
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

    # Load VST3 dump and build name→records lookup
    with open(vst3_dump_path, 'r') as f:
        vst3_dump = json.load(f)
    vst3_params = vst3_dump.get('parameters', [])

    vst3_by_name: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for p in vst3_params:
        name = p.get('name')
        if name:
            vst3_by_name[name].append(p)

    # Load R1 audit (for reference, not required for R3)
    with open(vst3_audit_path, 'r') as f:
        vst3_audit = json.load(f)

    result = {
        'registry_phase': '16.5.69.1-R / R3',
        'strict_mode': strict,
        'validation_status': 'PASS',
        'errors': [],
        'warnings': [],
        'entries': [],
        'summary': {},
    }

    # ===== BUILD REGISTRY FROM QUALIFIED MAPPINGS =====

    for semantic_id, target_ref in sorted(targets.SEMANTIC_TARGETS.items()):
        capability_key = target_ref.capability_key
        vst3_name = mappings.get(capability_key)

        # Skip unmapped targets (allowed)
        if vst3_name is None:
            result['warnings'].append(
                f"Target {semantic_id} ({capability_key}) is unmapped"
            )
            continue

        try:
            # Retrieve unique VST3 record
            vst3_record = get_unique_vst3_record(vst3_by_name, vst3_name)

            # Extract transport metadata
            vst3_index = vst3_record.get('index')
            is_boolean = vst3_record.get('isBoolean', False)
            is_discrete = vst3_record.get('isDiscrete', False)
            num_steps = vst3_record.get('numSteps') if is_discrete else None

            # Preserve raw domain values exactly
            min_raw = vst3_record.get('min')
            max_raw = vst3_record.get('max')
            default_raw = vst3_record.get('defaultValue')

            # Determine transport kind for reference (not semantic classification)
            if is_boolean:
                transport_kind = 'BOOLEAN'
            elif is_discrete:
                transport_kind = 'ENUM'
            else:
                transport_kind = 'SCALAR'

            # Create conservative record
            entry = ResolvedTarget(
                semantic_id=semantic_id,
                capability_key=capability_key,
                vst3_name=vst3_name,
                vst3_index=vst3_index,
                vst3_transport_kind=transport_kind,
                is_boolean=is_boolean,
                is_discrete=is_discrete,
                num_steps=num_steps,
                min_raw=min_raw,
                max_raw=max_raw,
                default_raw=default_raw,
                semantic_mutation_class=None,  # NEVER inferred
                semantic_classification_status='UNCLASSIFIED',
                resolution_status='RESOLVED_FROM_MAPPING',
                mapping_basis='R2 semantic_vst3_mapping.json + A1.1 VST3 dump',
            )

            # Validate invariants
            entry.validate_invariants()

            result['entries'].append({
                'semantic_id': entry.semantic_id,
                'capability_key': entry.capability_key,
                'vst3_name': entry.vst3_name,
                'vst3_index': entry.vst3_index,
                'vst3_transport_kind': entry.vst3_transport_kind,
                'is_boolean': entry.is_boolean,
                'is_discrete': entry.is_discrete,
                'num_steps': entry.num_steps,
                'min_raw': entry.min_raw,
                'max_raw': entry.max_raw,
                'default_raw': entry.default_raw,
                'semantic_mutation_class': entry.semantic_mutation_class,
                'semantic_classification_status': entry.semantic_classification_status,
                'resolution_status': entry.resolution_status,
                'mapping_basis': entry.mapping_basis,
            })

        except RegistryBuilderError as e:
            error = f"Failed to create entry for {semantic_id}: {str(e)}"
            result['errors'].append(error)
            if strict:
                raise RegistryBuilderError(error)

    # ===== REGISTRY INTEGRITY CHECKS =====

    # Check for duplicate VST3 targets (semantic collision would have been caught in R2)
    vst3_indices_used = {}
    for entry in result['entries']:
        idx = entry['vst3_index']
        if idx in vst3_indices_used:
            error = (
                f"Registry collision: two entries map to same VST3 index {idx}: "
                f"{vst3_indices_used[idx]} and {entry['semantic_id']}"
            )
            result['errors'].append(error)
            if strict:
                raise RegistryBuilderError(error)
        vst3_indices_used[idx] = entry['semantic_id']

    # Final status
    if result['errors']:
        result['validation_status'] = 'FAIL'
    else:
        result['validation_status'] = 'PASS'

    result['summary'] = {
        'total_entries': len(result['entries']),
        'unmapped_targets': len(result['warnings']),
        'errors': len(result['errors']),
    }

    return result


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

    print("=== R3 Hardened Resolved Target Registry Builder ===\n")

    # Build registry
    print("Building registry from R2 mapping + VST3 audit...")
    result = build_registry_hardened(
        str(targets_py),
        str(mapping_file),
        str(vst3_dump),
        str(vst3_audit),
        strict=False
    )

    print(f"\nValidation Status: {result['validation_status']}")
    print(f"Registry Entries: {result['summary']['total_entries']}")
    print(f"Unmapped Targets: {result['summary']['unmapped_targets']}")

    if result['errors']:
        print(f"\nERRORS ({len(result['errors'])}):")
        for error in result['errors'][:5]:
            print(f"  - {error}")
        if len(result['errors']) > 5:
            print(f"  ... and {len(result['errors']) - 5} more")

    if result['warnings']:
        print(f"\nWARNINGS ({len(result['warnings'])}):")
        for warning in result['warnings'][:5]:
            print(f"  - {warning}")
        if len(result['warnings']) > 5:
            print(f"  ... and {len(result['warnings']) - 5} more")

    # Write result
    output_path = repo_root / 'serum2' / 'qualification' / 'R3_HARDENED_REGISTRY_RESULT.json'
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\nRegistry written to {output_path}")

    print(f"\n{'='*50}")
    print(f"R3 GATE: {'PASS' if result['validation_status'] == 'PASS' else 'FAIL'}")
    print(f"{'='*50}")

    return 0 if result['validation_status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
