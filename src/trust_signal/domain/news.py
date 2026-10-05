"""News metadata candidates, not verified claims or licensed article bodies."""

from datetime import datetime

from pydantic import Field

from trust_signal.domain.base import Contract
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.domain.sanctions import ScreeningEvidence


class NewsCandidate(Contract):
    candidate_id: str
    source_id: str
    source_record_id: str
    event: dict
    reason_codes: list[str]
    publisher_trust: str
    possible_duplicate_group: str
    source_run_id: str
    evidence: list[ScreeningEvidence] = Field(min_length=1)


class NewsResearchResult(Contract):
    policy_version: str = "news-0.1"
    case_id: str
    subject_id: str
    checked_at: datetime
    identity_observation_ids: list[str] = Field(min_length=1)
    coverage: list[ResearchCoverage]
    candidates: list[NewsCandidate] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
