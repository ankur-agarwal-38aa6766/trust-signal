"""Source-reported relationships and roles, not inferred beneficial ownership."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from trust_signal.domain.base import Contract
from trust_signal.domain.sanctions import ScreeningEvidence


class ResearchCoverage(Contract):
    source_id: str
    operation: str
    coverage: Literal["available", "no_matches", "partial", "failed", "blocked", "stale", "not_applicable"]
    source_run_id: str | None = None
    records_checked: int = 0
    limitations: list[str] = Field(default_factory=list)
    error_category: str | None = None


class OwnershipRecord(Contract):
    record_id: str
    source_id: str
    source_record_id: str
    kind: Literal["consolidation_relationship", "reporting_exception", "organizational_role"]
    attribution: Literal["confirmed", "pending"]
    details: dict
    source_run_id: str
    evidence: list[ScreeningEvidence] = Field(min_length=1)


class OwnershipResearchResult(Contract):
    policy_version: str = "ownership-0.1"
    case_id: str
    subject_id: str
    identity_observation_ids: list[str] = Field(min_length=1)
    checked_at: datetime
    coverage: list[ResearchCoverage]
    records: list[OwnershipRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
