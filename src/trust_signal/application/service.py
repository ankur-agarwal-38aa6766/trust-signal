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
    IdentityVerificationCommand,
    IdentityVerificationResult,
    SubmitCaseCommand,
    TrustSignalApplication,
)
from trust_signal.application.identity import LiveIdentityService
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

    def verify_identity(self, command: IdentityVerificationCommand) -> IdentityVerificationResult:
        return IdentityVerificationResult(status="demo", legal_name=command.legal_name,
                                          lei=command.lei, jurisdiction=command.jurisdiction)

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

    def __init__(self, ingestion_pipeline=None) -> None:
        self._cases: dict[str, CaseView] = {}
        self._identity = LiveIdentityService(ingestion_pipeline)
        self._verified_identity: IdentityVerificationResult | None = None

    def verify_identity(self, command: IdentityVerificationCommand) -> IdentityVerificationResult:
        self._verified_identity = self._identity.verify(command)
        return self._verified_identity

    def search_identity(self, command: IdentitySearchCommand) -> IdentitySearchResult:
        self._verified_identity = None
        if command.source_mode == SourceMode.GLEIF_LIVE.value:
            return self._identity.search(command)
        # Fixtures have no registry candidates. Discovery must never execute research.
        return IdentitySearchResult(coverage="no_match",
                                    limitations=["Fixture mode does not query a registry."])

    def submit_case(self, command: SubmitCaseCommand) -> CaseReceipt:
        if command.source_mode == SourceMode.GLEIF_LIVE:
            verified = self._verified_identity
            if (verified is None or verified.status != "verified"
                    or verified.lei != command.lei.strip().upper()
                    or verified.legal_name.strip().casefold() != command.legal_name.strip().casefold()
                    or (verified.jurisdiction or "").casefold() != (command.jurisdiction or "").strip().casefold()):
                raise ValueError("Confirm the selected GLEIF identity before launching research.")
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
                "registration_authority": command.registration_authority,
                "registered_address": command.registered_address,
                "aliases": command.aliases,
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
