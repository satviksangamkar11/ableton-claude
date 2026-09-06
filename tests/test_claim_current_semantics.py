from types import SimpleNamespace

from serum2.evidence.capability_contract import (
    CAUSAL_VERIFIED,
    NEGATIVE_EVIDENCE,
)
from serum2.evidence.disposition import (
    CONTEXT_INCOMPLETE,
    HISTORICAL_VALID,
    INVALIDATED_ACTUATOR,
    VALID,
)
from serum2.evidence.semantics import (
    CURRENT_RUNTIME_CANDIDATE,
    CURRENT_RUNTIME_REQUALIFICATION_REQUIRED,
    evaluate_contract_semantics,
)


def make_contract(
    status=CAUSAL_VERIFIED,
    evidence=("E1",),
):
    return SimpleNamespace(
        target="test_target",
        status=status,
        provenance={
            "supporting_evidence": list(evidence),
        },
    )


def test_valid_evidence_creates_current_runtime_candidate():
    contract = make_contract()

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {"E1": VALID},
    )

    assert view.historical_admissible is True
    assert view.current_runtime_candidate is True
    assert (
        view.current_runtime_status
        == CURRENT_RUNTIME_CANDIDATE
    )


def test_historical_valid_does_not_mean_current_verified():
    contract = make_contract()

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {"E1": HISTORICAL_VALID},
    )

    assert view.historical_admissible is True
    assert view.current_runtime_candidate is False
    assert (
        view.current_runtime_status
        == CURRENT_RUNTIME_REQUALIFICATION_REQUIRED
    )


def test_context_incomplete_blocks_current_candidate():
    contract = make_contract()

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {"E1": CONTEXT_INCOMPLETE},
    )

    assert view.historical_admissible is False
    assert view.current_runtime_candidate is False


def test_invalidated_actuator_blocks_everything():
    contract = make_contract()

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {"E1": INVALIDATED_ACTUATOR},
    )

    assert view.historical_admissible is False
    assert view.current_runtime_candidate is False
    assert view.blocked_evidence == ("E1",)


def test_capability_status_is_not_overwritten_by_disposition():
    contract = make_contract(
        status=NEGATIVE_EVIDENCE,
        evidence=("E1",),
    )

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {"E1": VALID},
    )

    # VALID evidence cannot launder a negative capability status.
    assert view.capability_status == NEGATIVE_EVIDENCE
    assert view.current_runtime_candidate is False


def test_mixed_blocked_and_valid_evidence_is_not_current_candidate():
    contract = make_contract(
        status=CAUSAL_VERIFIED,
        evidence=("E1", "E2"),
    )

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {
            "E1": VALID,
            "E2": CONTEXT_INCOMPLETE,
        },
    )

    assert view.historical_admissible is False
    assert view.current_runtime_candidate is False
    assert view.blocked_evidence == ("E2",)


def test_undispositioned_evidence_is_not_admissible():
    contract = make_contract()

    view = evaluate_contract_semantics(
        "contract-1",
        contract,
        {},
    )

    assert view.historical_admissible is False
    assert view.current_runtime_candidate is False