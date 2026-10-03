"""UK Companies House public-data connector."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Self

import httpx

from trust_signal.connectors.base import EntityLookup, EntityRecord, SourceHealth, SourceObservation


class CompaniesHouseProtocolError(RuntimeError):
    """Companies House returned an unexpected payload for the requested record."""


class CompaniesHouseAdapter:
    source_id = "uk_companies_house"
    connector_version = "0.1.0"
    base_url = "https://api.company-information.service.gov.uk"
    record_url = "https://find-and-update.company-information.service.gov.uk/company/{company_number}"
    _company_number_pattern = re.compile(r"^[A-Z0-9]{2,8}$")

    def __init__(
        self,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 8.0,
    ):
        if not api_key.strip():
            raise ValueError("Companies House API key is required.")
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "TrustSignal/0.1"},
            auth=(api_key, ""),
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
            response = self._client.get(f"{self.base_url}/search/companies", params={"q": "test", "items_per_page": 1})
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

    def fetch_company_profile(self, company_number: str) -> EntityLookup | None:
        normalized_number = company_number.strip().upper()
        if not self._company_number_pattern.fullmatch(normalized_number):
            raise ValueError("Company number must contain 2 to 8 letters or digits.")

        url = f"{self.base_url}/company/{normalized_number}"
        response = self._client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        try:
            response_body = response.content
            response_text = response_body.decode("utf-8")
            payload = json.loads(response_body)
            returned_number = payload["company_number"]
            legal_name = payload["company_name"]
        except (ValueError, KeyError, TypeError) as exc:
            raise CompaniesHouseProtocolError("Companies House profile is missing required fields.") from exc

        if returned_number.upper() != normalized_number:
            raise CompaniesHouseProtocolError("Companies House profile number did not match request.")
        if not isinstance(legal_name, str) or not legal_name.strip():
            raise CompaniesHouseProtocolError("Companies House profile did not include a legal name.")

        address = payload.get("registered_office_address")
        registered_address = _format_address(address) if isinstance(address, dict) else None
        observed_at = datetime.now(UTC)
        observation = SourceObservation(
            source_id=self.source_id,
            source_record_id=normalized_number,
            canonical_url=self.record_url.format(company_number=normalized_number),
            observed_at=observed_at,
            content_hash=f"sha256:{hashlib.sha256(response_body).hexdigest()}",
            connector_version=self.connector_version,
            raw_payload=payload,
            payload_format="application/json",
            raw_response_text=response_text,
        )
        record = EntityRecord(
            source_id=self.source_id,
            source_record_id=normalized_number,
            legal_name=legal_name.strip(),
            registration_id=normalized_number,
            jurisdiction=payload.get("jurisdiction"),
            registration_status=payload.get("company_status"),
            entity_status=payload.get("company_status"),
            legal_form=payload.get("type"),
            registered_address=registered_address,
        )
        return EntityLookup(entity=record, observation=observation)


def _format_address(address: dict) -> str | None:
    parts = [
        address.get("address_line_1"),
        address.get("address_line_2"),
        address.get("locality"),
        address.get("region"),
        address.get("postal_code"),
        address.get("country"),
    ]
    formatted = ", ".join(str(part).strip() for part in parts if str(part or "").strip())
    return formatted or None
