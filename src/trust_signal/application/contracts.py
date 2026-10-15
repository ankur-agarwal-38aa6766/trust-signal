"""Provider-neutral application contracts and data models.

Defines the boundary between UI/clients and trust_signal backend execution engines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class CaseStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    NEEDS_MORE_INFORMATION = "needs_more_information"
    COMPLETED_WITH_GAPS = "completed_with_gaps"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class IdentitySearchCommand:
    legal_name: str
    jurisdiction: str | None = None
    registration_id: str | None = None
    website: str | None = None
    source_mode: str = "demo_fixtures"


@dataclass(frozen=True)
class IdentityCandidateView:
    candidate_id: str
    legal_name: str
    lei: str
    jurisdiction: str | None = None
    source_id: str = "gleif_lei_api"
    source_record_id: str = ""
    observation_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IdentitySearchResult:
    candidates: list[IdentityCandidateView] = field(default_factory=list)
    source_run_id: str | None = None
    coverage: str = "nominal"
    limitations: list[str] = field(default_factory=list)
    raw_observation_ids: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass(frozen=True)
class SubmitCaseCommand:
    legal_name: str
    lei: str
    jurisdiction: str | None = None
    registration_id: str | None = None
    website: str | None = None
    source_mode: str = "demo_fixtures"


@dataclass(frozen=True)
class CaseReceipt:
    case_id: str
    request_id: str
    status: CaseStatus
    message: str = ""


@dataclass(frozen=True)
class CaseView:
    case_id: str
    status: CaseStatus
    legal_name: str
    lei: str | None = None
    reasons: list[str] = field(default_factory=list)
    branches: list[dict[str, Any]] = field(default_factory=list)
    comparison_board: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    result: Any | None = None  # Underlying CaseResult for legacy/rich inspection if present


class TrustSignalApplication(Protocol):
    """Platform-independent application boundary contract."""

    def search_identity(self, command: IdentitySearchCommand) -> IdentitySearchResult:
        """Search entity identity by legal name; discovers candidates without running specialists."""
        ...

    def submit_case(self, command: SubmitCaseCommand) -> CaseReceipt:
        """Submit a case for durable execution with confirmed legal name and LEI."""
        ...

    def get_case(self, case_id: str) -> CaseView:
        """Retrieve durable case status and evaluation projections."""
        ...
