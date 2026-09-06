"""Four-state contradiction invariant. NOT_TESTED and INCONCLUSIVE are not
negative results and must never contradict anything."""
import sys
sys.path.insert(0, r"D:\ableton claude")
from serum2.evidence.claim import outcomes_contradict
from serum2.evidence.record import (
    OUTCOME_EFFECT as EFF, OUTCOME_NO_OBSERVED_EFFECT as NOE,
    OUTCOME_INCONCLUSIVE as INC, OUTCOME_NOT_TESTED as NT,
)

cases = [
    (EFF, NOE, True,  "effect <-> no_observed_effect = contradiction candidate"),
    (EFF, NT,  False, "effect <-> not_tested = no contradiction"),
    (EFF, INC, False, "effect <-> inconclusive = no contradiction"),
    (NOE, INC, False, "no_observed_effect <-> inconclusive = no contradiction"),
    (NOE, NT,  False, "no_observed_effect <-> not_tested = no contradiction"),
    (INC, NT,  False, "inconclusive <-> not_tested = no contradiction"),
    (EFF, EFF, False, "identical outcomes = no contradiction"),
    (NOE, NOE, False, "identical outcomes = no contradiction"),
]
ok = True
for a, b, expected, label in cases:
    got = outcomes_contradict(a, b)
    sym = outcomes_contradict(b, a)
    good = (got == expected) and (sym == expected)
    ok &= good
    print("%-4s %-58s %s" % ("PASS" if good else "FAIL", label, "symmetric" if got == sym else "ASYMMETRIC!"))
print()
print("OUTCOME INVARIANT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
