"""Evidence provenance and claim attribution are separate from event verification."""

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from trust_signal.domain.base import Contract


class EvidenceType(StrEnum):
    REGISTRY_RECORD = "registry_record"
    SANCTIONS_LISTING = "sanctions_listing"
    NEWS_REPORT = "news_report"
    REGULATORY_NOTICE = "regulatory_notice"
    COURT_RECORD = "court_record"


class AttributionStatus(StrEnum):
    CONFIRMED = "confirmed"
    PENDING_IDENTITY = "pending_identity"
    EXCLUDED = "excluded"


class EvidenceDocument(Contract):
    schema_version: str = "1"
    evidence_id: str
    observation_id: str
    source_id: str
    source_record_id: str
    observation_record_id: str
    canonical_url: str
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    connector_version: str
    observed_at: datetime
    published_at: datetime | None = None
    event_at: datetime | None = None
    evidence_type: EvidenceType
    language: str | None = None
    source_locator: str
    subject_candidate_id: str


class FindingEvidence(Contract):
    finding_id: str = Field(min_length=1)
    evidence_id: str
    subject_candidate_id: str
    attribution_status: AttributionStatus
    identity_policy_version: str
    reason_codes: list[str]
    eligible_for_scoring: bool = False
    # Event-state/claim verification is performed by a separate validator.
    claim_verification_status: str = "not_validated"
