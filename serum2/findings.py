"""Open Findings Ledger -- a system-wide epistemic-debt registry, deliberately
separate from Evidence -> Claim -> Capability -> Admission.

WHAT QUALIFIES AS A FINDING (the boundary, load-bearing -- not every UNKNOWN
or every stable negative result belongs here):

    A finding exists ONLY when evidence has exposed a specific unresolved
    MECHANISTIC, CAUSAL, or INTERPRETIVE question that the current contract/
    evidence cannot resolve.

A stable NEGATIVE_EVIDENCE, STRUCTURAL_ONLY, or CAUSAL_VERIFIED conclusion is
NOT, by itself, a finding -- it is a complete, correctly-frozen result. Example:
Macro.name's persistence FAIL is fully resolved evidence (see
capability_contract.py); WHY Serum drops it is an open question, but it does
not become ledger-worthy merely because it's unexplained -- only if it turns
out to matter to a producer-relevant operation. "Unexplained internals are not
automatically epistemic debt."

A finding NEVER writes capability status. It may motivate a brand new
ExperimentSpec, whose resulting EvidenceRecord/ClaimGroup -- through the
NORMAL pipeline -- can change capability status. The finding itself has no
write path into admission.py or capability_contract.py, by construction: this
module imports nothing from either, and nothing in either imports this module.
"""
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0.0"

STATUS_OPEN = "OPEN"
STATUS_CLOSED = "CLOSED"
ALLOWED_STATUSES = (STATUS_OPEN, STATUS_CLOSED)  # deliberately no NEEDS_DETAIL, no STALE

# Closed vocabulary. Extending this is a source-code change under normal
# review -- the same enforcement CAPABILITY_ORDER already relies on. No
# separate changelog microformat; the validator below is the actual gate.
ALLOWED_CATEGORIES = (
    "MEASUREMENT_LIMITATION",
    "MEASUREMENT_CONFOUND",
    "CAPABILITY_IDENTITY_UNRESOLVED",
    "PERSISTENCE_MECHANISM_UNKNOWN",
    "FORMAT_RESEARCH",
)
ALLOWED_OWNERS = ("compiler", "evidence", "producer")

REQUIRED_FIELDS = ("id", "status", "category", "owner", "discovered_at",
                  "trigger", "observed", "hypothesized_cause", "explicitly_not",
                  "closure_condition", "evidence_refs")


class LedgerValidationError(ValueError):
    pass


def compute_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_ledger(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_ledger(ledger: Dict[str, Any], *, base_dir: Optional[str] = None,
                    check_hashes: bool = True) -> List[str]:
    """Returns a list of problems (empty = valid). Never raises on data
    issues -- callers decide whether to treat problems as fatal, same
    convention as ExperimentSpec.validate()'s problem-list style."""
    problems = []
    if ledger.get("schema_version") != SCHEMA_VERSION:
        problems.append("schema_version %r does not match expected %r"
                        % (ledger.get("schema_version"), SCHEMA_VERSION))

    seen_ids = set()
    for entry in ledger.get("findings", []):
        eid = entry.get("id", "<missing id>")
        for field in REQUIRED_FIELDS:
            if field not in entry:
                problems.append("%s: missing required field %r" % (eid, field))
        if eid in seen_ids:
            problems.append("%s: duplicate finding id" % eid)
        seen_ids.add(eid)

        if entry.get("status") not in ALLOWED_STATUSES:
            problems.append("%s: status %r not in %r" % (eid, entry.get("status"), ALLOWED_STATUSES))
        if entry.get("category") not in ALLOWED_CATEGORIES:
            problems.append("%s: category %r not in closed vocabulary %r"
                            % (eid, entry.get("category"), ALLOWED_CATEGORIES))
        if entry.get("owner") not in ALLOWED_OWNERS:
            problems.append("%s: owner %r not in closed vocabulary %r"
                            % (eid, entry.get("owner"), ALLOWED_OWNERS))

        refs = entry.get("evidence_refs", [])
        if entry.get("status") == STATUS_OPEN and not refs:
            problems.append("%s: OPEN finding has no evidence_refs -- a finding may never "
                            "exist from recollection or prose alone" % eid)

        for ref in refs:
            fp = ref.get("file_path")
            if not fp:
                problems.append("%s: evidence_ref missing file_path" % eid)
                continue
            full_path = os.path.join(base_dir, fp) if base_dir else fp
            if not os.path.exists(full_path):
                problems.append("%s: evidence_ref file does not exist: %s" % (eid, full_path))
                continue
            if check_hashes:
                actual = compute_hash(full_path)
                expected = ref.get("content_hash")
                if actual != expected:
                    problems.append("%s: evidence_ref %s hash mismatch -- expected %s, got %s "
                                    "(the underlying file has changed since this finding was "
                                    "logged; re-verify and update content_hash)"
                                    % (eid, fp, expected, actual))

        cc = entry.get("closure_condition", {})
        if "description" not in cc:
            problems.append("%s: closure_condition missing 'description'" % eid)

    return problems
