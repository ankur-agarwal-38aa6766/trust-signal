"""Exact LEI retrieval from GLEIF's official public API."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Self

import httpx

from trust_signal.connectors.base import (
    EntityLookup,
    EntityRecord,
    SourceBatch,
    SourceHealth,
    SourceObservation,
)


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
            response_text = response_body.decode("utf-8")
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
            raw_response_text=response_text,
        )
        record = EntityRecord(
            source_id=self.source_id,
            lei=normalized_lei,
            source_record_id=normalized_lei,
            legal_name=legal_name.strip(),
            jurisdiction=jurisdiction,
            registration_status=registration.get("status"),
            entity_status=entity.get("status"),
        )
        return EntityLookup(entity=record, observation=observation)

    def search_by_name(self, name: str, page_size: int = 20, max_pages: int = 5) -> Iterator[SourceBatch]:
        if not name.strip() or not 1 <= page_size <= 100 or not 1 <= max_pages <= 100:
            raise ValueError("Name and bounded pagination are required.")
        url = str(httpx.URL(f"{self.base_url}/lei-records", params={
            "filter[entity.legalName]": name.strip(), "page[size]": page_size,
        }))
        yield from self._pages(url, "name_search", max_pages)

    def fetch_relationships(self, lei: str, max_pages: int = 5) -> Iterator[SourceBatch]:
        if not 1 <= max_pages <= 100:
            raise ValueError("max_pages must be between 1 and 100.")
        lookup = self.fetch_by_lei(lei)
        if lookup is None:
            yield SourceBatch(limitations=["LEI record not found; relationships unavailable."])
            return
        yield SourceBatch(observations=[lookup.observation], records=[lookup.entity.model_dump(mode="json")])
        relationships = lookup.observation.raw_payload["data"].get("relationships", {})
        for direction in ("direct-parent", "ultimate-parent", "direct-children"):
            links = relationships.get(direction, {}).get("links", {})
            url = links.get("relationship-records") or links.get("reporting-exception")
            if not url:
                yield SourceBatch(complete=False, limitations=[f"{direction}: no relationship or exception link."])
                continue
            yield from self._pages(url, direction, max_pages)

    def _pages(self, url: str, operation: str, max_pages: int) -> Iterator[SourceBatch]:
        visited: set[str] = set()
        for page in range(max_pages):
            parsed_url = httpx.URL(url)
            if (parsed_url.scheme != "https" or parsed_url.host != "api.gleif.org"
                    or parsed_url.port not in (None, 443) or parsed_url.username
                    or not parsed_url.path.startswith("/api/v1/")):
                raise SourceProtocolError("GLEIF returned an untrusted pagination or relationship URL.")
            if url in visited:
                raise SourceProtocolError("GLEIF pagination loop detected.")
            visited.add(url)
            response = self._client.get(url)
            response.raise_for_status()
            try:
                payload = response.json()
                nodes = payload["data"]
                nodes = [nodes] if isinstance(nodes, dict) else nodes
                if not isinstance(nodes, list):
                    raise TypeError("Invalid data collection")
                records = []
                for node in nodes:
                    if operation == "name_search":
                        attributes = node["attributes"]
                        identifier = attributes["lei"]
                        name = attributes["entity"]["legalName"]["name"]
                        if node["id"] != identifier or not self._lei_pattern.fullmatch(identifier) or not name.strip():
                            raise ValueError("Invalid candidate identity")
                        records.append({"lei": identifier, "legal_name": name,
                                        "jurisdiction": attributes["entity"].get("jurisdiction"),
                                        "identity_status": "candidate_requires_resolution"})
                    else:
                        if not node["id"] or not isinstance(node["attributes"], dict):
                            raise ValueError("Invalid relationship record")
                        records.append({"direction": operation, "record_type": node["type"],
                                        "source_record_id": node["id"], "attributes": node["attributes"]})
                next_url = payload.get("links", {}).get("next")
                if next_url is not None and not isinstance(next_url, str):
                    raise ValueError("Invalid next page URL")
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise SourceProtocolError("GLEIF collection did not match the expected contract.") from exc
            capped = bool(next_url) and page + 1 == max_pages
            observation = SourceObservation(
                source_id=self.source_id, source_record_id=f"{operation}:{url}", canonical_url=url,
                observed_at=datetime.now(UTC), connector_version=self.connector_version,
                content_hash=f"sha256:{hashlib.sha256(response.content).hexdigest()}",
                raw_payload=payload, raw_response_text=response.content.decode("utf-8"),
            )
            yield SourceBatch(observations=[observation], records=records, complete=not capped,
                              limitations=["Page limit reached; coverage is partial."] if capped else [])
            if not next_url:
                return
            url = next_url
