"""Application implementations: in-memory mock/fake and local adapter."""

from __future__ import annotations

import uuid

from trust_signal.application.contracts import (
    CaseReceipt,
    CaseStatus,
    CaseView,
    IdentityCandidateView,
    IdentitySearchCommand,
    IdentitySearchResult,
    SubmitCaseCommand,
    TrustSignalApplication,
)
from trust_signal.models import CaseRequest, CaseResult, SourceMode
from trust_signal.orchestration import case_graph


class InMemoryApplication(TrustSignalApplication):
    """In-memory implementation of TrustSignalApplication for contract testing and disconnected UI testing."""

    def __init__(
        self,
        candidates_by_name: dict[str, list[IdentityCandidateView]] | None = None,
        preloaded_cases: dict[str, CaseView] | None = None,
    ) -> None:
        self.candidates_by_name = candidates_by_name or {}
        self.cases: dict[str, CaseView] = preloaded_cases or {}

    def search_identity(self, command: IdentitySearchCommand) -> IdentitySearchResult:
        query = command.legal_name.strip()
        candidates = self.candidates_by_name.get(query, [])
        return IdentitySearchResult(
            candidates=candidates,
            source_run_id=f"run_{uuid.uuid4().hex[:8]}",
            coverage="nominal" if candidates else "no_match",
            limitations=["In-memory test simulation"] if not candidates else [],
        )

    def submit_case(self, command: SubmitCaseCommand) -> CaseReceipt:
        case_id = f"case_{uuid.uuid4().hex[:8]}"
        view = CaseView(
            case_id=case_id,
            status=CaseStatus.COMPLETED,
            legal_name=command.legal_name,
            lei=command.lei,
            reasons=[],
            branches=[{"branch_id": "registry", "status": "completed"}],
        )
        self.cases[case_id] = view
        return CaseReceipt(
            case_id=case_id,
            request_id=f"req_{uuid.uuid4().hex[:8]}",
            status=CaseStatus.COMPLETED,
            message="Case processed successfully",
        )

    def get_case(self, case_id: str) -> CaseView:
        if case_id not in self.cases:
            return CaseView(
                case_id=case_id,
                status=CaseStatus.FAILED,
                legal_name="",
                error=f"Case {case_id} not found",
            )
        return self.cases[case_id]


class LocalSynchronousApplication(TrustSignalApplication):
    """Local synchronous application that wraps run_case for local demo/development."""

    def __init__(self) -> None:
        self._cases: dict[str, CaseView] = {}

    def search_identity(self, command: IdentitySearchCommand) -> IdentitySearchResult:
        # Run synchronous name discovery without LEI
        source_mode = (
            SourceMode.GLEIF_LIVE
            if command.source_mode == SourceMode.GLEIF_LIVE.value or command.source_mode == SourceMode.GLEIF_LIVE
            else SourceMode.DEMO_FIXTURES
        )
        req = CaseRequest(
            party={
                "legal_name": command.legal_name,
                "jurisdiction": command.jurisdiction,
                "registration_id": command.registration_id,
                "website": command.website,
            },
            source_mode=source_mode,
        )
        res = case_graph.run_case(req)
        candidates: list[IdentityCandidateView] = []
        # Check registry branch or top-level identity resolution
        resolutions = []
        if res.identity_resolution:
            resolutions.append(res.identity_resolution)
        for b in res.branches:
            if b.branch_id == "registry" and b.identity_resolution:
                resolutions.append(b.identity_resolution)

        for resolution in resolutions:
            for match in resolution.matches:
                c = match.candidate
                if not any(existing.candidate_id == c.candidate_id for existing in candidates):
                    candidates.append(
                        IdentityCandidateView(
                            candidate_id=c.candidate_id,
                            legal_name=c.legal_name,
                            lei=c.lei or "",
                            jurisdiction=c.jurisdiction,
                            source_id=c.source_id,
                            source_record_id=c.source_record_id,
                            observation_ids=c.observation_ids,
                        )
                    )
        branch_limitations = [lim for b in res.branches for lim in b.limitations]
        return IdentitySearchResult(
            candidates=candidates,
            source_run_id=res.case_id,
            coverage="nominal" if candidates else "no_match",
            limitations=branch_limitations,
        )

    def submit_case(self, command: SubmitCaseCommand) -> CaseReceipt:
        source_mode = (
            SourceMode.GLEIF_LIVE
            if command.source_mode == SourceMode.GLEIF_LIVE.value or command.source_mode == SourceMode.GLEIF_LIVE
            else SourceMode.DEMO_FIXTURES
        )
        req = CaseRequest(
            party={
                "legal_name": command.legal_name.strip(),
                "jurisdiction": command.jurisdiction.strip() if command.jurisdiction else None,
                "registration_id": command.registration_id.strip() if command.registration_id else None,
                "lei": command.lei.strip() if command.lei else None,
                "website": command.website.strip() if command.website else None,
            },
            source_mode=source_mode,
        )
        res: CaseResult = case_graph.run_case(req)
        status_map = {
            "needs_more_information": CaseStatus.NEEDS_MORE_INFORMATION,
            "completed": CaseStatus.COMPLETED,
            "completed_with_gaps": CaseStatus.COMPLETED_WITH_GAPS,
            "failed": CaseStatus.FAILED,
        }
        case_status = status_map.get(res.status.value, CaseStatus.COMPLETED)

        view = CaseView(
            case_id=res.case_id,
            status=case_status,
            legal_name=command.legal_name,
            lei=command.lei,
            reasons=list(res.assessment.reasons),
            branches=[{"branch_id": b.branch_id, "status": b.status.value} for b in res.branches],
            comparison_board=[{"relation": item.relation, "summary": item.summary} for item in res.comparison_board],
            result=res,
        )
        self._cases[res.case_id] = view
        return CaseReceipt(
            case_id=res.case_id,
            request_id=res.case_id,
            status=case_status,
        )

    def get_case(self, case_id: str) -> CaseView:
        if case_id in self._cases:
            return self._cases[case_id]
        return CaseView(
            case_id=case_id,
            status=CaseStatus.FAILED,
            legal_name="",
            error=f"Case {case_id} not found",
        )
