from threading import Barrier

from trust_signal.models import (
    BranchResult,
    BranchStatus,
    CaseRequest,
    CaseStatus,
    Disposition,
    EvidenceMode,
    Finding,
    SourceMode,
)
from trust_signal.orchestration.case_graph import run_case


def test_incomplete_identity_routes_to_request_details_without_research():
    result = run_case(CaseRequest(party={"legal_name": "Example Organization"}))

    assert result.status == CaseStatus.NEEDS_MORE_INFORMATION
    assert result.assessment.disposition == Disposition.REQUEST_DETAILS
    assert result.assessment.risk_score is None
    assert result.branches == []


def test_live_gleif_mode_requires_an_exact_lei():
    result = run_case(
        CaseRequest(
            source_mode=SourceMode.GLEIF_LIVE,
            party={"legal_name": "Example Organization", "jurisdiction": "GB"},
        )
    )

    assert result.status == CaseStatus.NEEDS_MORE_INFORMATION
    assert result.assessment.reasons == ["lei"]
    assert result.branches == []


def test_live_identity_name_conflict_pauses_before_other_specialists():
    def registry(_request):
        return BranchResult(
            branch_id="registry",
            status=BranchStatus.COMPLETED,
            findings=[
                Finding(
                    branch_id="registry",
                    claim_type="legal_identity_record",
                    claim="GLEIF legal name: Other Legal Entity Ltd.",
                    subject="Other Legal Entity Ltd.",
                    source_id="gleif_lei_api",
                    source_name="GLEIF",
                    source_url="https://search.gleif.org/#/record/00000000000000000000",
                    source_record_id="00000000000000000000",
                    evidence_mode=EvidenceMode.LIVE_SOURCE,
                    verification_status="source_record_retrieved",
                )
            ],
        )

    request = CaseRequest(
        source_mode=SourceMode.GLEIF_LIVE,
        party={
            "legal_name": "Different Organization Ltd",
            "lei": "00000000000000000000",
        },
    )
    result = run_case(request, {"registry": registry})

    assert result.status == CaseStatus.NEEDS_MORE_INFORMATION
    assert result.identity_status == "identity_name_conflict"
    assert result.assessment.disposition == Disposition.REQUEST_DETAILS
    assert len(result.branches) == 1
    assert "Other Legal Entity Ltd." in result.assessment.reasons[0]


def test_live_exact_lei_and_name_match_still_requires_review_without_full_coverage():
    def registry(_request):
        return BranchResult(
            branch_id="registry",
            status=BranchStatus.COMPLETED,
            findings=[
                Finding(
                    branch_id="registry",
                    claim_type="legal_identity_record",
                    claim="GLEIF legal name: Example Organization Ltd.",
                    subject="EXAMPLE ORGANIZATION, LTD",
                    source_id="gleif_lei_api",
                    source_name="GLEIF",
                    source_url="https://search.gleif.org/#/record/00000000000000000000",
                    source_record_id="00000000000000000000",
                    evidence_mode=EvidenceMode.LIVE_SOURCE,
                    verification_status="source_record_retrieved",
                )
            ],
            limitations=["Only the LEI registry was queried."],
        )

    request = CaseRequest(
        source_mode=SourceMode.GLEIF_LIVE,
        party={"legal_name": "Example Organization Ltd.", "lei": "00000000000000000000"},
    )
    result = run_case(request, {"registry": registry})

    assert result.identity_status == "resolved_by_exact_lei_and_name"
    assert result.status == CaseStatus.COMPLETED_WITH_GAPS
    assert result.assessment.disposition == Disposition.ANALYST_REVIEW
    assert result.assessment.risk_score is None


def test_complete_input_runs_parallel_fixture_branches_and_does_not_score_fixtures():
    result = run_case(
        CaseRequest(
            party={
                "legal_name": "Example Organization Ltd",
                "jurisdiction": "GB",
                "registration_id": "00000000",
            }
        )
    )

    assert {branch.branch_id for branch in result.branches} == {"registry", "leadership", "events"}
    assert result.assessment.risk_score is None
    assert result.assessment.disposition == Disposition.ANALYST_REVIEW
    assert all(f.finding_id.startswith("finding_") for b in result.branches for f in b.findings)
    assert all(f.evidence_mode.value == "demo_fixture" for b in result.branches for f in b.findings)
    assert len(result.comparison_board) == 2
    assert any(item.relation == "same_claim_type_across_branches" for item in result.comparison_board)


def test_specialist_branches_run_concurrently():
    barrier = Barrier(3)

    def branch(branch_id):
        def run(_request):
            barrier.wait(timeout=2)
            return BranchResult(branch_id=branch_id, status=BranchStatus.COMPLETED)

        return run

    branches = {branch_id: branch(branch_id) for branch_id in ("registry", "events", "board")}
    result = run_case(
        CaseRequest(
            party={
                "legal_name": "Example Organization Ltd",
                "jurisdiction": "GB",
                "registration_id": "00000000",
            }
        ),
        branches,
    )

    assert len(result.branches) == 3


def test_branch_failure_is_recorded_without_aborting_other_branches():
    def failing(_request):
        raise RuntimeError("private service details")

    branches = {"registry": failing, "events": lambda request: BranchResult(
        branch_id="events", status=BranchStatus.COMPLETED
    )}
    result = run_case(
        CaseRequest(
            party={
                "legal_name": "Example Organization Ltd",
                "jurisdiction": "GB",
                "registration_id": "00000000",
            }
        ),
        branches,
    )

    assert result.status == CaseStatus.COMPLETED_WITH_GAPS
    assert {branch.branch_id: branch.status for branch in result.branches} == {
        "registry": BranchStatus.FAILED,
        "events": BranchStatus.COMPLETED,
    }
    failed = next(branch for branch in result.branches if branch.branch_id == "registry")
    assert "private service details" not in failed.error
