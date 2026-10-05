"""Explicit human decisions linked to an immutable research snapshot."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from trust_signal.domain.base import Contract


class ReviewerContext(Contract):
    """Must be supplied by a trusted authentication/authorization boundary."""

    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    role: Literal["reviewer", "supervisor", "viewer"]


class ReviewCommand(Contract):
    request_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    snapshot_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_version: int = Field(ge=0)
    action: Literal["review", "request_details", "reject", "reopen"]
    rationale: str = Field(min_length=10, max_length=4000)
    finding_ids: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    acknowledge_limitations: bool = False


class ReviewReceipt(Contract):
    event_id: str
    request_id: str
    case_id: str
    snapshot_hash: str
    version: int
    state: Literal["awaiting_review", "details_requested", "rejected"]
    reviewer_id: str
    reviewer_role: str
    recorded_at: datetime
    command: ReviewCommand
