"""Portable aggregation output; original findings remain in branch results."""

from datetime import datetime

from pydantic import Field

from trust_signal.domain.base import Contract


class ComparisonItem(Contract):
    finding_ids: list[str]
    relation: str
    summary: str


class ClaimGroup(Contract):
    group_id: str
    subject_key: str
    claim_type: str
    claim_key: str | None = None
    event_id: str | None = None
    effective_at: datetime | None = None
    finding_ids: list[str]
    source_ids: list[str]
    observation_ids: list[str]
    duplicate_sets: list[list[str]] = Field(default_factory=list)
    distinct_evidence_count: int
    relation: str
    identity_confirmed: bool = False


class TimelineEntry(Contract):
    event_at: datetime
    finding_ids: list[str]
    group_id: str


class BranchCoverage(Contract):
    branch_id: str
    status: str
    sources_checked: list[str]
    limitations: list[str]
    finding_count: int
    error: str | None = None


class AggregationResult(Contract):
    schema_version: str = "1"
    policy_version: str = "aggregation-0.1"
    groups: list[ClaimGroup] = Field(default_factory=list)
    comparison_board: list[ComparisonItem] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    coverage: list[BranchCoverage] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
