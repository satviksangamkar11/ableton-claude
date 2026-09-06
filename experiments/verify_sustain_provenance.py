"""Quick verification that sustain contract provenance is correctly exposed."""

import pickle
import sys

sys.path.insert(0, r"D:\ableton claude")

# Load the rebuilt contracts
contracts = pickle.load(open(r"D:\ableton claude\experiments\_capability_contracts.pkl", "rb"))

# Find sustain contracts
sustain_contracts = [c for c in contracts.values() if "sustain" in c.target.lower()]

print(f"Total contracts: {len(contracts)}")
print(f"Sustain contracts: {len(sustain_contracts)}")
print()

for c in sustain_contracts:
    print(f"Target: {c.target}")
    print(f"  Status: {c.status}")
    print(f"  Mutation target: {c.scope.get('mutation_target_path')}")
    print(f"  Measurement ID: {c.measurement.get('measurement_definition_id') if c.measurement else None}")

    prov = c.provenance
    print(f"  Supporting evidence: {prov.get('supporting_evidence')}")

    if "shared_context" in prov:
        sc = prov["shared_context"]
        print(f"  ✓ Shared context exposed: YES")
        print(f"    Status: {sc.get('status')}")
        print(f"    Context fields: {sc.get('context_fields')}")
        if sc.get("baseline_overrides"):
            print(f"    Baseline overrides: {sc.get('baseline_overrides')}")
    else:
        print(f"  ✓ Shared context: NOT exposed")

    if "measurement_definition_ids" in prov:
        print(f"  ✓ Measurement definition IDs exposed: {prov['measurement_definition_ids']}")

    print()

# Summary
print("=" * 80)
print("PROVENANCE REPAIR VERIFICATION")
print("=" * 80)

all_have_shared_context = all("shared_context" in c.provenance for c in sustain_contracts)
all_expose_measurement = all("measurement_definition_ids" in c.provenance for c in sustain_contracts)
all_expose_mutation = all(c.scope.get("mutation_target_path") for c in sustain_contracts)
all_preserve_evidence = all(len(c.provenance.get("supporting_evidence", [])) > 0 for c in sustain_contracts)

print(f"✓ All sustain contracts expose shared context: {all_have_shared_context}")
print(f"✓ All sustain contracts expose measurement IDs: {all_expose_measurement}")
print(f"✓ All sustain contracts expose mutation targets: {all_expose_mutation}")
print(f"✓ All sustain contracts preserve evidence IDs: {all_preserve_evidence}")

if all([all_have_shared_context, all_expose_measurement, all_expose_mutation, all_preserve_evidence]):
    print("\n✓✓✓ PROVENANCE REPAIR COMPLETE ✓✓✓")
else:
    print("\n✗ PROVENANCE REPAIR INCOMPLETE")
