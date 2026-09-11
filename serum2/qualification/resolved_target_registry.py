#!/usr/bin/env python3
"""16.5.69.1c: Resolved Target Registry

Builds the authoritative registry of ResolvedTarget objects.
Only RESOLVED mappings enter this registry.
Unresolved/ambiguous targets are explicitly classified but not included.

Output: RESOLVED_TARGET_REGISTRY.json
This becomes the ONLY input to A3 (mutation qualification).
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ResolvedTarget:
    """A semantic target that has been validated to map to exactly one VST3 parameter."""

    semantic_id: str
    capability_key: str

    # VST3 identity
    vst3_name: str
    vst3_index: int

    # VST3 transport classification (what the parameter looks like in VST3)
    vst3_transport_kind: str  # SCALAR, ENUM, BOOLEAN
    is_discrete: bool
    num_steps: int  # for ENUM

    # Semantic classification (what the parameter means semantically)
    semantic_mutation_class: str  # SCALAR, ENUM, BOOLEAN, TOPOLOGY, CONTEXTUAL, DEPENDENT, etc.

    # Resolution metadata
    resolution_status: str  # RESOLVED
    mapping_basis: str  # explicit_mapping, audited, inferred, etc.

    # Value domain
    min_val: float
    max_val: float
    default_val: float


def build_resolved_registry(
    mapping_audit_path: str,
    vst3_dump_path: str
) -> Dict[str, Any]:
    """Build the resolved target registry from validated mappings."""

    with open(mapping_audit_path, 'r') as f:
        mapping_audit = json.load(f)

    with open(vst3_dump_path, 'r') as f:
        vst3_dump = json.load(f)

    vst3_params = vst3_dump.get('parameters', [])

    # Build VST3 lookup by name (we know from audit that RESOLVED names are unique)
    vst3_by_name = {p['name']: p for p in vst3_params}

    registry = {
        'registry_phase': '16.5.69.1c',
        'resolved_count': 0,
        'unresolved_summary': {},
        'resolved_targets': [],
    }

    unresolved_by_status = {}

    # Process mapping audit results
    for mapping_entry in mapping_audit.get('mappings', []):
        semantic_id = mapping_entry['semantic_id']
        status = mapping_entry['resolution_status']

        if status == 'RESOLVED':
            # Fetch the VST3 parameter record
            vst3_name = mapping_entry['mapped_vst3_name']
            vst3_record = vst3_by_name.get(vst3_name)

            if not vst3_record:
                # Should not happen if audit passed, but be defensive
                continue

            # Classify VST3 transport kind
            if vst3_record.get('isBoolean'):
                transport_kind = 'BOOLEAN'
            elif vst3_record.get('isDiscrete'):
                transport_kind = 'ENUM'
            else:
                transport_kind = 'SCALAR'

            # Extract domain metadata
            min_val = parse_domain_value(vst3_record.get('min', 0.0))
            max_val = parse_domain_value(vst3_record.get('max', 1.0))
            default_val = vst3_record.get('defaultValue', 0.0)

            resolved = ResolvedTarget(
                semantic_id=semantic_id,
                capability_key=mapping_entry['capability_key'],
                vst3_name=vst3_name,
                vst3_index=mapping_entry['vst3_indices'][0],
                vst3_transport_kind=transport_kind,
                is_discrete=vst3_record.get('isDiscrete', False),
                num_steps=vst3_record.get('numSteps', 1),
                # Semantic classification: initially same as transport (will be refined)
                semantic_mutation_class=transport_kind,
                resolution_status='RESOLVED',
                mapping_basis=mapping_entry.get('mapping_basis', 'explicit_mapping'),
                min_val=min_val,
                max_val=max_val,
                default_val=default_val,
            )

            registry['resolved_targets'].append(asdict(resolved))
            registry['resolved_count'] += 1

        else:
            # Track unresolved entries
            if status not in unresolved_by_status:
                unresolved_by_status[status] = []
            unresolved_by_status[status].append({
                'semantic_id': semantic_id,
                'capability_key': mapping_entry['capability_key'],
                'issues': mapping_entry.get('issues', []),
            })

    registry['unresolved_summary'] = {
        status: len(entries) for status, entries in unresolved_by_status.items()
    }
    registry['unresolved_by_status'] = unresolved_by_status

    return registry


def parse_domain_value(val: Any) -> float:
    """Parse domain value which may be string or number."""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Try to extract numeric part from strings like "100% [3.0 dB]"
        import re
        match = re.search(r'[-+]?\d*\.?\d+', val)
        if match:
            return float(match.group())
    return 0.0


def main():
    repo_root = Path(__file__).parent.parent.parent

    mapping_audit_path = repo_root / 'serum2' / 'qualification' / 'SEMANTIC_MAPPING_AUDIT.json'
    vst3_dump_path = repo_root / 'experiments' / 'A1_1_vst3_parameter_surface.json'

    # Prerequisites
    if not mapping_audit_path.exists():
        print(f"Error: Semantic Mapping Audit not found. Run semantic_mapping_audit.py first.", file=sys.stderr)
        sys.exit(1)

    with open(mapping_audit_path, 'r') as f:
        mapping_audit = json.load(f)

    if mapping_audit.get('validation_status') != 'PASS':
        print(f"Error: Semantic Mapping Audit failed. Fix mappings before proceeding.", file=sys.stderr)
        sys.exit(1)

    if not vst3_dump_path.exists():
        print(f"Error: VST3 dump not found at {vst3_dump_path}", file=sys.stderr)
        sys.exit(1)

    registry = build_resolved_registry(str(mapping_audit_path), str(vst3_dump_path))

    output_path = repo_root / 'serum2' / 'qualification' / 'RESOLVED_TARGET_REGISTRY.json'
    with open(output_path, 'w') as f:
        json.dump(registry, f, indent=2)

    print(f"Resolved Target Registry written to {output_path}")
    print(f"Resolved targets: {registry['resolved_count']}")
    print(f"\nUnresolved Summary:")
    for status, count in sorted(registry['unresolved_summary'].items()):
        print(f"  {status:25s}: {count}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
