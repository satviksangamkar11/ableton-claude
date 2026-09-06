# GATES — Historical Gate Documentation

**⚠️ This is a historical scoped gate/evidence document for 16.5.14 only.**

- Not the authoritative roadmap. See [ROADMAP.md](ROADMAP.md) for the authoritative step register.
- 16.5.14 content and findings remain valid for their scoped gate and historical context.
- Do not treat this as the source of truth for current project direction.

---

## 16.5.14: HYPOTHESIS policy + "make darker" refusal/discovery

## Decision locked
```
GROUNDED           → NORMAL_EXECUTION
PARTIALLY_GROUNDED → EXPLORATORY_EXECUTION
HYPOTHESIS         → CAPABILITY_DISCOVERY_NEEDED
UNGROUNDED         → EXECUTION_REFUSED
```

HYPOTHESIS means "general synthesis knowledge, not Serum-verified."
Executing it inside the producer loop would make the producer a hidden research instrument.
Instead it produces a structured DiscoveryRequest naming exactly what evidence is missing.

"Make darker" is the test vehicle:
- Control candidate: FXEQ.Freq1 (IS in SEMANTIC_TARGETS, IS CAUSAL_VERIFIED)
- But no verified Serum evidence links FXEQ.Freq1 → spectral_centroid_hz
- form_prediction() → HYPOTHESIS (metric not established by evidence system)
- execute_producer_goal() → CAPABILITY_DISCOVERY_NEEDED

Do NOT add "darker" to SEMANTIC_TARGETS or add spectral_centroid to any contract.
The refusal must emerge from a genuine evidence gap, not a designed-to-fail test.

---

## Gate 1: EXECUTION_POLICY has CAPABILITY_DISCOVERY_NEEDED for HYPOTHESIS

CHECK:
```
python -c "
from serum2.compiler.producer import EXECUTION_POLICY, HYPOTHESIS, CAPABILITY_DISCOVERY_NEEDED
assert EXECUTION_POLICY[HYPOTHESIS] == CAPABILITY_DISCOVERY_NEEDED, EXECUTION_POLICY
print('PASS')
"
```
EXPECT: `PASS`

---

## Gate 2: DiscoveryRequest dataclass exists with required fields

CHECK:
```
python -c "
import dataclasses
from serum2.compiler.producer import DiscoveryRequest
fields = {f.name for f in dataclasses.fields(DiscoveryRequest)}
required = {'goal', 'candidate_control', 'required_effect', 'required_measurement', 'missing_capability_reason'}
missing = required - fields
assert not missing, 'missing fields: %s' % missing
print('PASS')
"
```
EXPECT: `PASS`

---

## Gate 3: GoalVerdict has discovery_request field

CHECK:
```
python -c "
import dataclasses
from serum2.compiler.producer import GoalVerdict
fields = {f.name for f in dataclasses.fields(GoalVerdict)}
assert 'discovery_request' in fields, fields
print('PASS')
"
```
EXPECT: `PASS`

---

## Gate 4: 16.5.14 experiment — "darker" → HYPOTHESIS → CAPABILITY_DISCOVERY_NEEDED

CHECK:
```
python experiments/step16_5_14_darker_refusal.py
```
EXPECT (all criteria PASS):
- prediction_basis.epistemic_status == HYPOTHESIS
- verdict.goal_status == CAPABILITY_DISCOVERY_NEEDED
- verdict.is_admissible_as_evidence == False
- verdict.discovery_request is not None
- discovery_request names the missing evidence

---

## Gate 5: No CapabilityContract modified by 16.5.14

CHECK (run BEFORE and AFTER the experiment, hashes must match):
```
python -c "
import pickle, hashlib
contracts = pickle.load(open(r'experiments\_capability_contracts.pkl', 'rb'))
sig = hashlib.md5(repr(sorted(c.target for c in contracts.values())).encode()).hexdigest()
print('contract_sig:', sig)
"
```
EXPECT: identical hash before and after

---

## Gate 6: Existing tests still pass

CHECK:
```
python experiments/step16_5_13_producer_quieter.py
```
EXPECT: `16.5.13 CRITERIA: 8/8 PASS`

---

## Final audit
- [ ] verdict.detail names the SPECIFIC experiment needed to ground the prediction
- [ ] DiscoveryRequest can be passed directly to ExperimentSpec construction (future step)
- [ ] producer.py has no default goal thresholds
- [ ] prediction_status and goal_status remain separate fields
