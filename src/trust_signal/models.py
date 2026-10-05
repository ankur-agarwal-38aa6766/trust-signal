"""Versioned domain contracts for a TrustSignal investigation case."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import Field, field_validator

from trust_signal.domain.aggregation import AggregationResult, ComparisonItem
from trust_signal.domain.base import Contract
from trust_signal.domain.identity import IdentityResolution
from trust_signal.domain.legal import LegalResearchResult
from trust_signal.domain.news import NewsResearchResult
from trust_signal.domain.ownership import OwnershipResearchResult
from trust_signal.domain.sanctions import SanctionsScreeningResult
from trust_signal.domain.validation import ValidationResult


def utc_now() -> datetime:
    return datetime.now(UTC)


class CaseStatus(StrEnum):
    NEEDS_MORE_INFORMATION = "needs_more_information"
    COMPLETED = "completed"
    COMPLETED_WITH_GAPS = "completed_with_gaps"


class BranchStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvidenceMode(StrEnum):
    LIVE_SOURCE = "live_source"
    DEMO_FIXTURE = "demo_fixture"


class SourceMode(StrEnum):
    DEMO_FIXTURES = "demo_fixtures"
    GLEIF_LIVE = "gleif_live"


class Disposition(StrEnum):
    REQUEST_DETAILS = "request_details"
    ANALYST_REVIEW = "analyst_review"
    MONITOR_RECOMMENDATION = "monitor_recommendation"
    REJECT_RECOMMENDATION = "reject_recommendation"


class PartyInput(Contract):
    legal_name: str = Field(min_length=2, max_length=240)
    jurisdiction: str | None = Field(default=None, min_length=2, max_length=8)
    registration_id: str | None = Field(default=None, max_length=120)
    registration_authority: str | None = Field(default=None, max_length=120)
    lei: str | None = Field(default=None, min_length=20, max_length=20)
    website: str | None = Field(default=None, max_length=500)
    registered_address: str | None = Field(default=None, max_length=1000)
    aliases: list[str] = Field(default_factory=list)


class CaseRequest(Contract):
    schema_version: str = "1"
    case_id: str = Field(default_factory=lambda: f"case_{uuid4().hex}")
    party: PartyInput
    source_mode: SourceMode = SourceMode.DEMO_FIXTURES
    requested_at: datetime = Field(default_factory=utc_now)


class Finding(Contract):
    finding_id: str = Field(default_factory=lambda: f"finding_{uuid4().hex}")
    branch_id: str
    claim_type: str
    claim: str = Field(min_length=1, max_length=2000)
    subject: str
    subject_id: str | None = None
    claim_key: str | None = None
    claim_value: str | None = None
    claim_cardinality: Literal["single", "multiple", "unknown"] = "unknown"
    event_id: str | None = None
    event_at: datetime | None = None
    effective_at: datetime | None = None
    source_id: str
    source_name: str
    source_url: str | None = None
    source_record_id: str | None = None
    observation_ids: list[str] = Field(default_factory=list)
    source_run_id: str | None = None
    content_hash: str | None = None
    connector_version: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)
    evidence_mode: EvidenceMode
    verification_status: str = "unverified"
    procedural_status: str | None = None
    risk_weight: int = Field(default=0, ge=0, le=100)

    @field_validator("event_at", "effective_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Event and effective timestamps require a timezone.")
        return value


class BranchResult(Contract):
    branch_id: str
    status: BranchStatus
    findings: list[Finding] = Field(default_factory=list)
    sources_checked: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    error: str | None = None
    identity_resolution: IdentityResolution | None = None
    sanctions_screening: SanctionsScreeningResult | None = None
    ownership_research: OwnershipResearchResult | None = None
    legal_research: LegalResearchResult | None = None
    news_research: NewsResearchResult | None = None
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime = Field(default_factory=utc_now)


class Assessment(Contract):
    policy_version: str = "starter-0.1"
    risk_score: int | None = Field(default=None, ge=0, le=100)
    score_status: str
    reasons: list[str] = Field(default_factory=list)
    disposition: Disposition


class CaseResult(Contract):
    schema_version: str = "1"
    case_id: str
    status: CaseStatus
    party: PartyInput
    identity_status: str
    identity_resolution: IdentityResolution | None = None
    branches: list[BranchResult] = Field(default_factory=list)
    comparison_board: list[ComparisonItem] = Field(default_factory=list)
    aggregation: AggregationResult | None = None
    validation: ValidationResult | None = None
    assessment: Assessment
    created_at: datetime = Field(default_factory=utc_now)
