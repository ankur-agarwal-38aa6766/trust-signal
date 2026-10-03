"""Shared contracts for source adapters and immutable source observations."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Protocol

from pydantic import Field

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
    payload_format: Literal["application/vnd.api+json", "application/json", "application/xml"] = "application/vnd.api+json"
    raw_response_text: str | None = Field(default=None, exclude=True, repr=False)


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
