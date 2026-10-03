"""Versioned, explainable identity decisions independent of source adapters."""

from enum import StrEnum

from pydantic import Field

from trust_signal.domain.base import Contract


class MatchStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANDIDATE = "candidate"
    CONFLICT = "conflict"
    NO_MATCH = "no_match"


class ResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    NEEDS_REVIEW = "needs_review"
    NO_MATCH = "no_match"


class IdentityCandidate(Contract):
    candidate_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_record_id: str = Field(min_length=1)
    legal_name: str = Field(min_length=1)
    lei: str | None = None
    registration_id: str | None = None
    registration_authority: str | None = None
    jurisdiction: str | None = None
    registered_address: str | None = None
    aliases: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)


class CandidateMatch(Contract):
    candidate: IdentityCandidate
    status: MatchStatus
    reason_codes: list[str]
    name_similarity: float = Field(ge=0, le=1)
    eligible_for_attribution: bool = False


class IdentityResolution(Contract):
    schema_version: str = "1"
    policy_version: str = "identity-0.1"
    status: ResolutionStatus
    selected_candidate_id: str | None = None
    matches: list[CandidateMatch] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
