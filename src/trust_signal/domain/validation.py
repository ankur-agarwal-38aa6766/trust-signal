"""Validation audit; structural checks never grant scoring eligibility."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from trust_signal.domain.base import Contract


class FindingValidation(Contract):
    finding_id: str
    status: Literal["review_required", "rejected"]
    reason_codes: list[str]
    structural_checks_passed: bool


class ValidationResult(Contract):
    policy_version: str = "validation-0.1"
    status: str = "review_required"
    checked_at: datetime
    findings: list[FindingValidation] = Field(default_factory=list)
    eligible_finding_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=lambda: [
        "Structural checks do not reverify RAW persistence or source claim truth.",
        "Claim/event validation and scoring policy are not configured; no finding is scoring-eligible.",
    ])
