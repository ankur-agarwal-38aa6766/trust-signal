"""Reviewable legal-source candidates, separate from adverse conclusions."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from trust_signal.domain.base import Contract
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.domain.sanctions import ScreeningEvidence


class LegalCandidate(Contract):
    candidate_id: str
    source_id: str
    source_record_id: str
    status: Literal["confirmed", "potential", "excluded"]
    relevance: Literal["named_subject", "title_mention"]
    reason_codes: list[str]
    event: dict
    source_run_id: str
    evidence: list[ScreeningEvidence] = Field(min_length=1)


class LegalResearchResult(Contract):
    policy_version: str = "legal-0.1"
    case_id: str
    subject_id: str
    identity_observation_ids: list[str] = Field(min_length=1)
    checked_at: datetime
    coverage: list[ResearchCoverage]
    candidates: list[LegalCandidate] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
