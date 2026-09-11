#!/usr/bin/env python3
"""16.5.69.1a: VST3 Surface Audit

Pure data validation on A1_1_vst3_parameter_surface.json.
No semantic knowledge. Only answers:
- Is the dump structurally valid?
- Are indices unique?
- How many duplicate names exist?
- What metadata is present?
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict


def audit_vst3_surface(dump_path: str) -> Dict[str, Any]:
    """Audit the VST3 parameter surface from A1.1 dump.

    Returns a complete audit report without semantic interpretation.
    """

    with open(dump_path, 'r') as f:
        dump = json.load(f)

    params = dump.get('parameters', [])

    audit = {
        'audit_phase': '16.5.69.1a',
        'source': dump_path,
        'schema_status': 'PASS',
        'errors': [],
        'warnings': [],
    }

    # Basic counts
    audit['parameter_count'] = len(params)
    audit['metadata'] = {
        'experiment': dump.get('experiment'),
        'mechanism': dump.get('mechanism'),
        'plugin': dump.get('plugin'),
    }

    # Index audit
    indices: Dict[int, List[int]] = defaultdict(list)  # index -> param positions
    for i, p in enumerate(params):
        idx = p.get('index')
        if idx is None:
            audit['errors'].append(f"Parameter {i}: missing 'index' field")
        else:
            indices[idx].append(i)

    audit['unique_index_count'] = len(indices)
    duplicate_indices = {idx: positions for idx, positions in indices.items() if len(positions) > 1}
    audit['duplicate_indices'] = duplicate_indices
    if duplicate_indices:
        audit['warnings'].append(f"{len(duplicate_indices)} indices appear multiple times")

    # Name audit
    names: Dict[str, List[int]] = defaultdict(list)  # name -> param positions
    for i, p in enumerate(params):
        name = p.get('name')
        if name is None:
            audit['errors'].append(f"Parameter {i}: missing 'name' field")
        else:
            names[name].append(i)

    audit['unique_name_count'] = len(names)
    duplicate_names = {name: positions for name, positions in names.items() if len(positions) > 1}
    audit['duplicate_names'] = {
        name: {
            'count': len(positions),
            'indices': [params[pos]['index'] for pos in positions]
        }
        for name, positions in duplicate_names.items()
    }
    if duplicate_names:
        audit['warnings'].append(f"{len(duplicate_names)} names appear multiple times")

    # Schema completeness audit
    required_fields = ['index', 'name', 'isBoolean', 'isDiscrete']
    optional_fields = ['numSteps', 'defaultValue', 'min', 'max', 'category', 'label', 'currentValText']

    missing_required = set()
    for i, p in enumerate(params):
        for field in required_fields:
            if field not in p:
                missing_required.add((i, field))

    if missing_required:
        audit['errors'].append(f"{len(missing_required)} parameters missing required fields")
        audit['missing_fields'] = list(missing_required)

    # Transport metadata audit
    boolean_count = sum(1 for p in params if p.get('isBoolean', False))
    discrete_count = sum(1 for p in params if p.get('isDiscrete', False))
    continuous_count = audit['parameter_count'] - boolean_count - discrete_count

    audit['transport_metadata'] = {
        'boolean_parameters': boolean_count,
        'discrete_parameters': discrete_count,
        'continuous_scalar_parameters': continuous_count,
    }

    # Domain metadata audit
    with_min_max = sum(1 for p in params if 'min' in p and 'max' in p)
    with_numsteps = sum(1 for p in params if 'numSteps' in p)

    audit['domain_metadata'] = {
        'with_min_max': with_min_max,
        'with_numsteps': with_numsteps,
    }

    # Final schema status
    if audit['errors']:
        audit['schema_status'] = 'FAIL'

    return audit


def main():
    repo_root = Path(__file__).parent.parent.parent
    dump_path = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'
    output_path = repo_root / 'serum2' / 'qualification' / 'VST3_SURFACE_AUDIT.json'

    if not dump_path.exists():
        print(f"Error: VST3 dump not found at {dump_path}", file=sys.stderr)
        sys.exit(1)

    audit = audit_vst3_surface(str(dump_path))

    with open(output_path, 'w') as f:
        json.dump(audit, f, indent=2)

    print(f"VST3 Surface Audit written to {output_path}")
    print(f"Schema status: {audit['schema_status']}")
    print(f"Total parameters: {audit['parameter_count']}")
    print(f"Unique indices: {audit['unique_index_count']}")
    print(f"Unique names: {audit['unique_name_count']}")
    if audit['duplicate_indices']:
        print(f"Duplicate indices: {len(audit['duplicate_indices'])}")
    if audit['duplicate_names']:
        print(f"Duplicate names: {len(audit['duplicate_names'])}")

    return 0 if audit['schema_status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
