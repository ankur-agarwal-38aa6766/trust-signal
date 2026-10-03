"""UN Security Council consolidated sanctions-list connector."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Self
from xml.etree import ElementTree

import httpx

from trust_signal.connectors.base import (
    SanctionsListing,
    SanctionsSnapshot,
    SourceHealth,
    SourceObservation,
)


class UNSanctionsProtocolError(RuntimeError):
    """The UN sanctions XML did not match the expected list structure."""


class UNSanctionsAdapter:
    source_id = "un_security_council_consolidated_list"
    connector_version = "0.1.0"
    consolidated_xml_url = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

    def __init__(self, transport: httpx.BaseTransport | None = None, timeout: float = 20.0):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"Accept": "application/xml,text/xml", "User-Agent": "TrustSignal/0.1"},
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
            response = self._client.head(self.consolidated_xml_url)
            if response.status_code in {403, 405}:
                response = self._client.get(self.consolidated_xml_url)
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

    def fetch_snapshot(self) -> SanctionsSnapshot:
        response = self._client.get(self.consolidated_xml_url)
        response.raise_for_status()
        response_body = response.content
        observed_at = datetime.now(UTC)
        root = _parse_xml(response_body)
        listings = _parse_entity_listings(root)
        observation = SourceObservation(
            source_id=self.source_id,
            source_record_id="consolidated.xml",
            canonical_url=self.consolidated_xml_url,
            observed_at=observed_at,
            content_hash=f"sha256:{hashlib.sha256(response_body).hexdigest()}",
            connector_version=self.connector_version,
            raw_payload=_snapshot_metadata(root, listings),
            payload_format="application/xml",
            raw_response_text=response_body.decode("utf-8"),
        )
        return SanctionsSnapshot(observation=observation, listings=listings)


def _parse_xml(response_body: bytes) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(response_body)
    except ElementTree.ParseError as exc:
        raise UNSanctionsProtocolError("UN sanctions response was not valid XML.") from exc


def _parse_entity_listings(root: ElementTree.Element) -> list[SanctionsListing]:
    entity_nodes = root.findall(".//ENTITY")
    if not entity_nodes:
        raise UNSanctionsProtocolError("UN sanctions XML did not include entity listings.")

    listings: list[SanctionsListing] = []
    for node in entity_nodes:
        reference = _text(node, "REFERENCE_NUMBER") or _text(node, "DATAID")
        name = _text(node, "FIRST_NAME")
        if not reference or not name:
            continue
        listings.append(
            SanctionsListing(
                source_id=UNSanctionsAdapter.source_id,
                source_record_id=reference,
                legal_name=name,
                list_type="entity",
                listed_on=_text(node, "LISTED_ON"),
                sanctions_regime=_text(node, "UN_LIST_TYPE"),
                jurisdiction=_text(node.find("ENTITY_ADDRESS"), "COUNTRY"),
                aliases=_aliases(node),
                comments=_text(node, "COMMENTS1"),
            )
        )
    if not listings:
        raise UNSanctionsProtocolError("UN sanctions XML entity listings lacked required fields.")
    return listings


def _aliases(node: ElementTree.Element) -> list[str]:
    values: list[str] = []
    for alias in node.findall(".//ENTITY_ALIAS"):
        alias_name = _text(alias, "ALIAS_NAME")
        if alias_name:
            values.append(alias_name)
    return values


def _snapshot_metadata(root: ElementTree.Element, listings: list[SanctionsListing]) -> dict:
    return {
        "root_tag": root.tag,
        "generated_on": root.attrib.get("dateGenerated"),
        "entity_count": len(listings),
    }


def _text(node: ElementTree.Element | None, child_name: str) -> str | None:
    if node is None:
        return None
    child = node.find(child_name)
    if child is None or child.text is None:
        return None
    value = child.text.strip()
    return value or None
