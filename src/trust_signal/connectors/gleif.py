"""Exact LEI retrieval from GLEIF's official public API."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Self

import httpx

from trust_signal.connectors.base import EntityLookup, EntityRecord, SourceHealth, SourceObservation


class SourceProtocolError(RuntimeError):
    """The source returned a payload that does not match its documented contract."""


class GleifAdapter:
    source_id = "gleif_lei_api"
    connector_version = "0.1.0"
    base_url = "https://api.gleif.org/api/v1"
    record_url = "https://search.gleif.org/#/record/{lei}"
    _lei_pattern = re.compile(r"^[0-9A-Z]{20}$")

    def __init__(self, transport: httpx.BaseTransport | None = None, timeout: float = 8.0):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"Accept": "application/vnd.api+json", "User-Agent": "TrustSignal/0.1"},
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def health(self) -> SourceHealth:
        checked_at = datetime.now(UTC)
        try:
            response = self._client.get(f"{self.base_url}/lei-records", params={"page[size]": 1})
            response.raise_for_status()
            available = True
            error_category = None
        except httpx.HTTPError as exc:
            available = False
            error_category = type(exc).__name__
        return SourceHealth(
            source_id=self.source_id,
            available=available,
            checked_at=checked_at,
            error_category=error_category,
        )

    def fetch_by_lei(self, lei: str) -> EntityLookup | None:
        normalized_lei = lei.strip().upper()
        if not self._lei_pattern.fullmatch(normalized_lei):
            raise ValueError("LEI must contain exactly 20 uppercase letters or digits.")

        url = f"{self.base_url}/lei-records/{normalized_lei}"
        response = self._client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        try:
            response_body = response.content
            payload = json.loads(response_body)
            data = payload["data"]
            attributes = data["attributes"]
            entity = attributes["entity"]
            registration = attributes.get("registration") or {}
            legal_name = entity["legalName"]["name"]
            returned_lei = attributes["lei"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SourceProtocolError("GLEIF response is missing required LEI record fields.") from exc

        if returned_lei != normalized_lei or data.get("id") != normalized_lei:
            raise SourceProtocolError("GLEIF response identifier did not match the requested LEI.")
        if not isinstance(legal_name, str) or not legal_name.strip():
            raise SourceProtocolError("GLEIF response did not include a legal name.")

        observed_at = datetime.now(UTC)
        jurisdiction = entity.get("jurisdiction")
        if not jurisdiction:
            jurisdiction = (entity.get("legalAddress") or {}).get("country")
        observation = SourceObservation(
            source_id=self.source_id,
            source_record_id=normalized_lei,
            canonical_url=self.record_url.format(lei=normalized_lei),
            observed_at=observed_at,
            content_hash=f"sha256:{hashlib.sha256(response_body).hexdigest()}",
            connector_version=self.connector_version,
            raw_payload=payload,
        )
        record = EntityRecord(
            source_id=self.source_id,
            lei=normalized_lei,
            legal_name=legal_name.strip(),
            jurisdiction=jurisdiction,
            registration_status=registration.get("status"),
            entity_status=entity.get("status"),
        )
        return EntityLookup(entity=record, observation=observation)
