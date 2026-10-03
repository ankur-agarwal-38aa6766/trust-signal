"""Shared contracts for source adapters and immutable source observations."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Protocol

from pydantic import Field, StringConstraints

from trust_signal.models import Contract


class SourceHealth(Contract):
    source_id: str
    available: bool
    checked_at: datetime
    error_category: str | None = None


class SourceObservation(Contract):
    source_id: str
    source_record_id: str
    canonical_url: str
    observed_at: datetime
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    connector_version: str
    raw_payload: dict
    payload_format: Literal["application/vnd.api+json", "application/json", "application/xml", "text/html", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"] = "application/vnd.api+json"
    raw_response_text: Annotated[str, StringConstraints(strip_whitespace=False)] | None = Field(default=None, exclude=True, repr=False)
    raw_response_bytes: bytes | None = Field(default=None, exclude=True, repr=False)


class EntityRecord(Contract):
    source_id: str
    legal_name: str
    source_record_id: str | None = None
    lei: str | None = None
    registration_id: str | None = None
    jurisdiction: str | None = None
    registration_status: str | None = None
    entity_status: str | None = None
    legal_form: str | None = None
    registered_address: str | None = None


class SanctionsListing(Contract):
    source_id: str
    source_record_id: str
    legal_name: str
    list_type: str
    listed_on: str | None = None
    sanctions_regime: str | None = None
    jurisdiction: str | None = None
    aliases: list[str] = Field(default_factory=list)
    comments: str | None = None
    measures: list[str] = Field(default_factory=list)
    programs: list[str] = Field(default_factory=list)


class EntityLookup(Contract):
    entity: EntityRecord
    observation: SourceObservation


class SanctionsSnapshot(Contract):
    observation: SourceObservation
    listings: list[SanctionsListing]


class SourceBatch(Contract):
    observations: list[SourceObservation] = Field(default_factory=list)
    records: list[dict] = Field(default_factory=list)
    complete: bool = True
    limitations: list[str] = Field(default_factory=list)


class SourceAdapter(Protocol):
    source_id: str

    def health(self) -> SourceHealth: ...

    def fetch_by_lei(self, lei: str) -> EntityLookup | None: ...


class OrganizationRole(Contract):
    source_id: str
    source_record_id: str
    organization_number: str
    display_name: str
    holder_type: Literal["person", "organization"]
    holder_registration_id: str | None = None
    role_code: str
    role_name: str
    group_code: str
    group_last_changed: str | None = None
    deregistered: bool
    is_board_role: bool


class SourceEvent(Contract):
    """Source metadata, not an attributed adverse finding or a risk score."""

    source_id: str
    source_record_id: str
    title: str
    canonical_url: str
    event_type: str
    procedural_status: Literal["unknown", "allegation", "proceeding", "decision", "final_decision", "judgment_published", "debarment_listing"] = "unknown"
    finality: Literal["unknown", "final", "appealable", "under_appeal"] = "unknown"
    published_at: str | None = None
    updated_at: str | None = None
    subject_name: str | None = None
    jurisdiction: str | None = None
    source_category: str | None = None
    outcome: str | None = None
    identity_status: Literal["unmatched_candidate"] = "unmatched_candidate"
    metadata: dict = Field(default_factory=dict)
