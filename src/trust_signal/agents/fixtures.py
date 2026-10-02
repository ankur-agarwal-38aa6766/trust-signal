"""Transparent local fixtures; these are never represented as live source results."""

from __future__ import annotations

from collections.abc import Callable

from trust_signal.models import BranchResult, BranchStatus, CaseRequest, EvidenceMode, Finding

Branch = Callable[[CaseRequest], BranchResult]


def _fixture_finding(request: CaseRequest, branch: str, claim_type: str, claim: str) -> Finding:
    return Finding(
        branch_id=branch,
        claim_type=claim_type,
        claim=claim,
        subject=request.party.legal_name,
        source_id="demo_fixture",
        source_name="Local demonstration fixture",
        source_url=None,
        source_record_id="fixture-not-a-source-record",
        evidence_mode=EvidenceMode.DEMO_FIXTURE,
        verification_status="illustrative_only",
        risk_weight=0,
    )


def registry_branch(request: CaseRequest) -> BranchResult:
    return BranchResult(
        branch_id="registry",
        status=BranchStatus.COMPLETED,
        findings=[
            _fixture_finding(
                request,
                "registry",
                "identity_input",
                "The submitted party details were accepted as workflow input; no registry was queried.",
            )
        ],
        sources_checked=["none: local fixture mode"],
        limitations=["No live registry connector is configured."],
    )


def leadership_branch(request: CaseRequest) -> BranchResult:
    return BranchResult(
        branch_id="leadership",
        status=BranchStatus.COMPLETED,
        findings=[
            _fixture_finding(
                request,
                "leadership",
                "coverage_note",
                "Leadership research is a fixture placeholder; no people or roles were inferred.",
            )
        ],
        sources_checked=["none: local fixture mode"],
        limitations=["No leadership source connector is configured."],
    )


def events_branch(request: CaseRequest) -> BranchResult:
    return BranchResult(
        branch_id="events",
        status=BranchStatus.COMPLETED,
        findings=[
            _fixture_finding(
                request,
                "events",
                "coverage_note",
                "News, sanctions, and legal-event research is a fixture placeholder; no event was asserted.",
            )
        ],
        sources_checked=["none: local fixture mode"],
        limitations=["No event or news source connector is configured."],
    )


def fixture_branches() -> dict[str, Branch]:
    return {
        "registry": registry_branch,
        "leadership": leadership_branch,
        "events": events_branch,
    }
