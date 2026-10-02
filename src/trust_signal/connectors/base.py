"""Shared contracts for source adapters and immutable source observations."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

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


class EntityRecord(Contract):
    source_id: str
    lei: str
    legal_name: str
    jurisdiction: str | None = None
    registration_status: str | None = None
    entity_status: str | None = None


class EntityLookup(Contract):
    entity: EntityRecord
    observation: SourceObservation


class SourceAdapter(Protocol):
    source_id: str

    def health(self) -> SourceHealth: ...

    def fetch_by_lei(self, lei: str) -> EntityLookup | None: ...
