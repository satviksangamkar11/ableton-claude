#!/usr/bin/env python3
"""16.5.69.1: Build SERUM_SEMANTIC_TARGET_INVENTORY.json

Audits existing semantic targets and maps to VST3 parameters.
Structure each inventory entry for mutation class classification.

This is PHASE 1 output: inventory of what targets we claim to control.
Does NOT yet run mutation tests; that's A3–A7.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add serum2 to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from serum2.compiler import targets
from serum2.qualification.vst3_resolver import VST3Resolver


def build_inventory(vst3_dump_path: str, output_path: str, mapping_path: str = None):
    """Build semantic target inventory from existing targets.py and VST3 dump.

    Args:
        vst3_dump_path: path to A1_1_vst3_parameter_surface.json
        output_path: where to write the inventory
        mapping_path: path to semantic_vst3_mapping.json (if None, uses __file__.parent)
    """

    # Load VST3 dump
    with open(vst3_dump_path, 'r') as f:
        vst3_dump = json.load(f)

    params = vst3_dump.get('parameters', [])

    # Build reverse lookup: parameter name -> VST3 record
    vst3_by_name = {p['name']: p for p in params}

    # Load semantic-to-VST3 mapping
    if mapping_path is None:
        mapping_path = Path(__file__).parent / 'semantic_vst3_mapping.json'
    with open(mapping_path, 'r') as f:
        mapping_data = json.load(f)
    semantic_to_vst3 = mapping_data.get('mappings', {})

    resolver = VST3Resolver(vst3_dump_path)

    # Audit existing semantic targets
    inventory = {
        'inventory_phase': '16.5.69.1',
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'total_semantic_targets': len(targets.SEMANTIC_TARGETS),
        'total_vst3_parameters': len(params),
        'mapping_file': str(mapping_path),
        'semantic_targets': [],
    }

    resolved_count = 0
    unresolved_count = 0

    for semantic_name, target_ref in sorted(targets.SEMANTIC_TARGETS.items()):
        # Lookup VST3 parameter name via semantic_vst3_mapping
        capability_key = target_ref.capability_key
        vst3_param_name = semantic_to_vst3.get(capability_key)

        # Try lookup in VST3 by mapped name
        vst3_record = vst3_by_name.get(vst3_param_name) if vst3_param_name else None

        entry = {
            'semantic_id': semantic_name,
            'capability_key': capability_key,
            'display_name': semantic_name,  # Placeholder
            'family': 'unknown',  # Will be classified during A3–A7
            'value_kind': 'unknown',
            'mutation_class': 'UNKNOWN',
            'vst3_parameter_ids': [],
            'vst3_parameter_name': None,
            'resolution_status': 'UNRESOLVED',
            'notes': [],
        }

        if vst3_record:
            # Found VST3 parameter
            entry['resolution_status'] = 'RESOLVED'
            entry['vst3_parameter_name'] = vst3_record['name']
            entry['vst3_parameter_ids'] = [vst3_record['index']]

            # Classify mutation class
            mutation_class = resolver.classify_mutation_class(vst3_record)
            entry['mutation_class'] = mutation_class

            # Set value kind based on type
            if vst3_record.get('isBoolean'):
                entry['value_kind'] = 'boolean'
            elif vst3_record.get('isDiscrete'):
                entry['value_kind'] = 'enum'
                entry['notes'].append(
                    f"numSteps={vst3_record.get('numSteps', 'unknown')}"
                )
            else:
                entry['value_kind'] = 'scalar'

            resolved_count += 1
        else:
            # No VST3 match found
            unresolved_count += 1
            if vst3_param_name:
                entry['notes'].append(
                    f'Mapped to VST3 name {vst3_param_name!r} but parameter not found in dump'
                )
            else:
                entry['notes'].append(
                    f'No VST3 mapping for capability_key {capability_key!r}'
                )

        inventory['semantic_targets'].append(entry)

    # Summary
    inventory['resolution_summary'] = {
        'total': len(targets.SEMANTIC_TARGETS),
        'resolved': resolved_count,
        'unresolved': unresolved_count,
        'resolution_rate': f"{100 * resolved_count / len(targets.SEMANTIC_TARGETS):.1f}%"
    }

    # Write inventory
    with open(output_path, 'w') as f:
        json.dump(inventory, f, indent=2)

    print(f"Inventory written to {output_path}")
    print(f"Resolution: {resolved_count}/{len(targets.SEMANTIC_TARGETS)} ({inventory['resolution_summary']['resolution_rate']})")
    return inventory


if __name__ == '__main__':
    repo_root = Path(__file__).parent.parent.parent
    vst3_dump = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'
    output = repo_root / 'serum2' / 'qualification' / 'SERUM_SEMANTIC_TARGET_INVENTORY.json'
    mapping = repo_root / 'serum2' / 'qualification' / 'semantic_vst3_mapping.json'

    if not vst3_dump.exists():
        print(f"Error: VST3 dump not found at {vst3_dump}", file=sys.stderr)
        sys.exit(1)

    if not mapping.exists():
        print(f"Error: semantic-VST3 mapping not found at {mapping}", file=sys.stderr)
        sys.exit(1)

    build_inventory(str(vst3_dump), str(output), str(mapping))
