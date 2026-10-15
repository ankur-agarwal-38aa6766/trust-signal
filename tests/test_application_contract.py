"""Contract tests for TrustSignalApplication."""

from trust_signal.application.contracts import (
    CaseStatus,
    IdentityCandidateView,
    IdentitySearchCommand,
    SubmitCaseCommand,
    TrustSignalApplication,
)
from trust_signal.application.service import InMemoryApplication, LocalSynchronousApplication


def test_in_memory_application_search_and_submit():
    candidate = IdentityCandidateView(
        candidate_id="cand_1",
        legal_name="Microsoft Corporation",
        lei="INR2EJN1ERAN0W5ZP974",
        jurisdiction="US-WA",
    )
    app: TrustSignalApplication = InMemoryApplication(
        candidates_by_name={"Microsoft Corporation": [candidate]}
    )

    search_res = app.search_identity(IdentitySearchCommand(legal_name="Microsoft Corporation"))
    assert len(search_res.candidates) == 1
    assert search_res.candidates[0].lei == "INR2EJN1ERAN0W5ZP974"

    receipt = app.submit_case(
        SubmitCaseCommand(
            legal_name="Microsoft Corporation",
            lei="INR2EJN1ERAN0W5ZP974",
        )
    )
    assert receipt.status == CaseStatus.COMPLETED
    assert receipt.case_id

    view = app.get_case(receipt.case_id)
    assert view.case_id == receipt.case_id
    assert view.legal_name == "Microsoft Corporation"
    assert view.status == CaseStatus.COMPLETED


def test_local_synchronous_application_demo():
    app: TrustSignalApplication = LocalSynchronousApplication()
    receipt = app.submit_case(
        SubmitCaseCommand(
            legal_name="Example Organization Ltd",
            lei="5493001KJTIIGC8Y1R12",
            jurisdiction="GB",
            registration_id="00000000",
            source_mode="demo_fixtures",
        )
    )
    assert receipt.case_id
    view = app.get_case(receipt.case_id)
    assert view.status in [CaseStatus.COMPLETED, CaseStatus.COMPLETED_WITH_GAPS]
    assert view.result is not None
