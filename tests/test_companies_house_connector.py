import base64
import hashlib
import json

import httpx
import pytest

from trust_signal.connectors.companies_house import (
    CompaniesHouseAdapter,
    CompaniesHouseProtocolError,
)

COMPANY_NUMBER = "00000006"


def company_profile(company_number=COMPANY_NUMBER):
    return {
        "company_number": company_number,
        "company_name": "ROYAL MAIL PLC",
        "company_status": "active",
        "jurisdiction": "england-wales",
        "type": "plc",
        "registered_office_address": {
            "address_line_1": "185 Farringdon Road",
            "locality": "London",
            "postal_code": "EC1A 1AA",
            "country": "England",
        },
    }


def test_fetch_company_profile_normalizes_record_and_hashes_response():
    payload = company_profile()
    response_body = json.dumps(payload).encode("utf-8")
    expected_auth = "Basic " + base64.b64encode(b"test-key:").decode("ascii")

    def handler(request):
        assert request.url.path == f"/company/{COMPANY_NUMBER}"
        assert request.headers["authorization"] == expected_auth
        return httpx.Response(200, content=response_body, headers={"content-type": "application/json"})

    with CompaniesHouseAdapter(api_key="test-key", transport=httpx.MockTransport(handler)) as adapter:
        result = adapter.fetch_company_profile(COMPANY_NUMBER.lower())

    assert result is not None
    assert result.entity.legal_name == "ROYAL MAIL PLC"
    assert result.entity.registration_id == COMPANY_NUMBER
    assert result.entity.jurisdiction == "england-wales"
    assert result.entity.registration_status == "active"
    assert result.entity.legal_form == "plc"
    assert result.entity.registered_address == "185 Farringdon Road, London, EC1A 1AA, England"
    assert result.observation.content_hash == f"sha256:{hashlib.sha256(response_body).hexdigest()}"
    assert result.observation.canonical_url.endswith(f"/company/{COMPANY_NUMBER}")


def test_fetch_company_profile_returns_none_for_not_found():
    transport = httpx.MockTransport(lambda _request: httpx.Response(404))
    with CompaniesHouseAdapter(api_key="test-key", transport=transport) as adapter:
        assert adapter.fetch_company_profile(COMPANY_NUMBER) is None


def test_fetch_company_profile_rejects_invalid_company_number():
    transport = httpx.MockTransport(lambda _request: pytest.fail("unexpected HTTP request"))
    with CompaniesHouseAdapter(api_key="test-key", transport=transport) as adapter, pytest.raises(
        ValueError, match="2 to 8"
    ):
        adapter.fetch_company_profile("not-a-company-number")


def test_fetch_company_profile_rejects_mismatched_identity():
    payload = company_profile("00000007")
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, json=payload))
    with CompaniesHouseAdapter(api_key="test-key", transport=transport) as adapter, pytest.raises(
        CompaniesHouseProtocolError, match="did not match"
    ):
        adapter.fetch_company_profile(COMPANY_NUMBER)


def test_fetch_company_profile_requires_api_key():
    with pytest.raises(ValueError, match="API key"):
        CompaniesHouseAdapter(api_key=" ")
