"""Durable workflow state shared by local and Snowflake execution adapters."""

from enum import StrEnum
from typing import Literal

from pydantic import Field

from trust_signal.domain.base import Contract


class WorkflowStage(StrEnum):
    IDENTITY = "identity"
    SANCTIONS = "sanctions"
    OWNERSHIP = "ownership"
    NEWS = "news"
    LEGAL = "legal"
    AGGREGATE = "aggregate"
    VALIDATE = "validate"
    ASSESS = "assess"


SPECIALIST_STAGES = (
    WorkflowStage.SANCTIONS, WorkflowStage.OWNERSHIP, WorkflowStage.NEWS, WorkflowStage.LEGAL,
)


class WorkflowRun(Contract):
    run_id: str
    graph_run_id: str
    request_id: str
    case_id: str
    tenant_id: str
    status: str = "running"
    request_payload: dict


class StageAttempt(Contract):
    attempt_id: str
    run_id: str
    stage: WorkflowStage
    attempt: int = Field(ge=1)
    status: str
    output: dict | None = None
    error_category: str | None = None


class WorkflowInputFailure(Contract):
    schema_version: str = "1"
    case_id: str
    status: Literal["needs_more_information"] = "needs_more_information"
    error_category: str = "InvalidCaseRequest"
    reason_codes: list[str] = Field(default_factory=lambda: ["invalid_case_request"])
