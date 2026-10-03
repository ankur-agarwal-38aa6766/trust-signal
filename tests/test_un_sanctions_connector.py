import hashlib

import httpx
import pytest

from trust_signal.connectors.un_sanctions import UNSanctionsAdapter, UNSanctionsProtocolError

XML_BODY = b"""<?xml version="1.0" encoding="UTF-8"?>
<CONSOLIDATED_LIST dateGenerated="2026-09-28">
  <ENTITIES>
    <ENTITY>
      <DATAID>6908555</DATAID>
      <VERSIONNUM>1</VERSIONNUM>
      <FIRST_NAME>EXAMPLE ENTITY LIMITED</FIRST_NAME>
      <UN_LIST_TYPE>Al-Qaida</UN_LIST_TYPE>
      <REFERENCE_NUMBER>QDe.001</REFERENCE_NUMBER>
      <LISTED_ON>2001-10-06</LISTED_ON>
      <COMMENTS1>Example comment.</COMMENTS1>
      <ENTITY_ALIAS>
        <ALIAS_NAME>EXAMPLE ENTITY</ALIAS_NAME>
      </ENTITY_ALIAS>
      <ENTITY_ADDRESS>
        <COUNTRY>GB</COUNTRY>
      </ENTITY_ADDRESS>
    </ENTITY>
  </ENTITIES>
</CONSOLIDATED_LIST>
"""


def test_fetch_snapshot_parses_entity_listings_and_hashes_xml():
    def handler(request):
        assert request.url.path == "/resources/xml/en/consolidated.xml"
        return httpx.Response(200, content=XML_BODY, headers={"content-type": "application/xml"})

    with UNSanctionsAdapter(transport=httpx.MockTransport(handler)) as adapter:
        snapshot = adapter.fetch_snapshot()

    assert snapshot.observation.source_record_id == "consolidated.xml"
    assert snapshot.observation.content_hash == f"sha256:{hashlib.sha256(XML_BODY).hexdigest()}"
    assert snapshot.observation.raw_payload["entity_count"] == 1
    assert len(snapshot.listings) == 1
    listing = snapshot.listings[0]
    assert listing.source_record_id == "QDe.001"
    assert listing.legal_name == "EXAMPLE ENTITY LIMITED"
    assert listing.list_type == "entity"
    assert listing.sanctions_regime == "Al-Qaida"
    assert listing.listed_on == "2001-10-06"
    assert listing.aliases == ["EXAMPLE ENTITY"]
    assert listing.jurisdiction == "GB"


def test_fetch_snapshot_rejects_invalid_xml():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=b"<not-valid"))
    with UNSanctionsAdapter(transport=transport) as adapter, pytest.raises(
        UNSanctionsProtocolError, match="valid XML"
    ):
        adapter.fetch_snapshot()


def test_fetch_snapshot_rejects_missing_entity_listings():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=b"<ROOT />"))
    with UNSanctionsAdapter(transport=transport) as adapter, pytest.raises(
        UNSanctionsProtocolError, match="entity listings"
    ):
        adapter.fetch_snapshot()
