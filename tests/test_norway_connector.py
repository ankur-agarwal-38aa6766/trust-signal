import hashlib
import json

import httpx
import pytest

from trust_signal.connectors.norway import NorwayRegistryAdapter, NorwayRegistryProtocolError

ORGANIZATION_NUMBER = "974760673"


def organization_payload(organization_number=ORGANIZATION_NUMBER):
    return {
        "organisasjonsnummer": organization_number,
        "navn": "BRONNOYSUNDREGISTRENE",
        "organisasjonsform": {"kode": "ORGL"},
        "underAvvikling": False,
        "forretningsadresse": {
            "adresse": ["Havnegata 48"],
            "postnummer": "8900",
            "poststed": "BRONNOYSUND",
            "land": "Norge",
        },
    }


def test_fetch_organization_normalizes_record_and_hashes_response():
    payload = organization_payload()
    response_body = json.dumps(payload).encode("utf-8")

    def handler(request):
        assert request.url.path == f"/enhetsregisteret/api/enheter/{ORGANIZATION_NUMBER}"
        return httpx.Response(200, content=response_body, headers={"content-type": "application/json"})

    with NorwayRegistryAdapter(transport=httpx.MockTransport(handler)) as adapter:
        result = adapter.fetch_organization(ORGANIZATION_NUMBER)

    assert result is not None
    assert result.entity.legal_name == "BRONNOYSUNDREGISTRENE"
    assert result.entity.registration_id == ORGANIZATION_NUMBER
    assert result.entity.jurisdiction == "NO"
    assert result.entity.registration_status == "not_under_liquidation"
    assert result.entity.entity_status == "active"
    assert result.entity.legal_form == "ORGL"
    assert result.entity.registered_address == "Havnegata 48, 8900, BRONNOYSUND, Norge"
    assert result.observation.content_hash == f"sha256:{hashlib.sha256(response_body).hexdigest()}"


def test_fetch_organization_returns_none_for_not_found():
    transport = httpx.MockTransport(lambda _request: httpx.Response(404))
    with NorwayRegistryAdapter(transport=transport) as adapter:
        assert adapter.fetch_organization(ORGANIZATION_NUMBER) is None


def test_fetch_organization_rejects_invalid_identifier():
    transport = httpx.MockTransport(lambda _request: pytest.fail("unexpected HTTP request"))
    with NorwayRegistryAdapter(transport=transport) as adapter, pytest.raises(
        ValueError, match="9 digits"
    ):
        adapter.fetch_organization("123")


def test_fetch_organization_rejects_mismatched_identity():
    payload = organization_payload("974760674")
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    with NorwayRegistryAdapter(transport=transport) as adapter, pytest.raises(
        NorwayRegistryProtocolError, match="did not match"
    ):
        adapter.fetch_organization(ORGANIZATION_NUMBER)
