"""Portable screening decisions, separate from risk scoring and legal conclusions."""

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from trust_signal.domain.base import Contract


class ScreeningEvidence(Contract):
    observation_id: str = Field(min_length=1)
    canonical_url: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    connector_version: str = Field(min_length=1)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Evidence retrieval time requires a timezone.")
        return value


class SanctionsMatch(Contract):
    match_id: str
    source_id: str
    listing_id: str
    listing_name: str
    list_type: str
    status: Literal["confirmed", "potential", "excluded"]
    reason_codes: list[str]
    name_similarity: float = Field(ge=0, le=1)
    aliases: list[str] = Field(default_factory=list)
    measures: list[str] = Field(default_factory=list)
    programs: list[str] = Field(default_factory=list)
    sanctions_regime: str | None = None
    listed_on: str | None = None
    source_run_id: str
    evidence: list[ScreeningEvidence] = Field(min_length=1)


class SanctionsSourceCoverage(Contract):
    source_id: str
    coverage: Literal["available", "partial", "failed", "blocked", "stale"]
    source_run_id: str | None = None
    records_checked: int = Field(default=0, ge=0)
    limitations: list[str] = Field(default_factory=list)
    error_category: str | None = None


class SanctionsScreeningResult(Contract):
    policy_version: str = "sanctions-0.1"
    case_id: str
    subject_id: str
    identity_observation_ids: list[str] = Field(min_length=1)
    outcome: Literal["confirmed_match", "potential_match", "no_candidates", "incomplete"]
    complete: bool
    checked_at: datetime
    sources: list[SanctionsSourceCoverage]
    matches: list[SanctionsMatch] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
