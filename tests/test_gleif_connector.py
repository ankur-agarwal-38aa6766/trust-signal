import hashlib
import json

import httpx
import pytest

from trust_signal.connectors.gleif import GleifAdapter, SourceProtocolError

LEI = "5493001KJTIIGC8Y1R12"


def gleif_payload(lei=LEI):
    return {
        "data": {
            "type": "lei-records",
            "id": lei,
            "attributes": {
                "lei": lei,
                "entity": {
                    "legalName": {"name": "Example Global PLC"},
                    "jurisdiction": "GB",
                    "legalAddress": {"country": "GB"},
                    "status": "ACTIVE",
                },
                "registration": {"status": "ISSUED"},
            },
        }
    }


def test_fetch_by_lei_normalizes_record_and_hashes_raw_response():
    payload = gleif_payload()
    response_body = json.dumps(payload).encode("utf-8")

    def handler(request):
        assert request.url.path == f"/api/v1/lei-records/{LEI}"
        assert request.headers["accept"] == "application/vnd.api+json"
        return httpx.Response(
            200,
            content=response_body,
            headers={"content-type": "application/vnd.api+json"},
        )

    with GleifAdapter(transport=httpx.MockTransport(handler)) as adapter:
        result = adapter.fetch_by_lei(LEI.lower())

    assert result is not None
    assert result.entity.legal_name == "Example Global PLC"
    assert result.entity.jurisdiction == "GB"
    assert result.entity.registration_status == "ISSUED"
    assert result.entity.entity_status == "ACTIVE"
    expected_hash = hashlib.sha256(response_body).hexdigest()
    assert result.observation.content_hash == f"sha256:{expected_hash}"
    assert result.observation.canonical_url.endswith(f"/record/{LEI}")


def test_fetch_by_lei_returns_none_for_not_found():
    transport = httpx.MockTransport(lambda _request: httpx.Response(404))
    with GleifAdapter(transport=transport) as adapter:
        assert adapter.fetch_by_lei(LEI) is None


def test_invalid_identifier_is_rejected_before_network_call():
    transport = httpx.MockTransport(lambda _request: pytest.fail("unexpected HTTP request"))
    with GleifAdapter(transport=transport) as adapter, pytest.raises(
        ValueError, match="20 uppercase letters or digits"
    ):
        adapter.fetch_by_lei("not-an-lei")


def test_mismatched_response_identity_is_rejected():
    payload = gleif_payload("5493001KJTIIGC8Y1R13")
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    with GleifAdapter(transport=transport) as adapter, pytest.raises(
        SourceProtocolError, match="did not match"
    ):
        adapter.fetch_by_lei(LEI)


def test_malformed_payload_is_rejected():
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": {}}))
    with GleifAdapter(transport=transport) as adapter, pytest.raises(
        SourceProtocolError, match="missing required"
    ):
        adapter.fetch_by_lei(LEI)
