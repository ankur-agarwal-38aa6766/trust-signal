"""Norway Bronnoysundregistrene organization-register connector."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Self

import httpx

from trust_signal.connectors.base import (
    EntityLookup,
    EntityRecord,
    OrganizationRole,
    SourceBatch,
    SourceHealth,
    SourceObservation,
)


class NorwayRegistryProtocolError(RuntimeError):
    """The Norwegian registry returned an unexpected payload."""


class NorwayRegistryAdapter:
    source_id = "no_bronnoysund_enhetsregisteret"
    connector_version = "0.1.0"
    base_url = "https://data.brreg.no/enhetsregisteret/api"
    record_url = "https://data.brreg.no/enhetsregisteret/oppslag/enheter/{orgnr}"
    _orgnr_pattern = re.compile(r"^[0-9]{9}$")

    def __init__(self, transport: httpx.BaseTransport | None = None, timeout: float = 8.0):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "TrustSignal/0.1"},
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
            response = self._client.get(f"{self.base_url}/enheter", params={"size": 1})
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

    def fetch_organization(self, organization_number: str) -> EntityLookup | None:
        normalized_number = organization_number.strip()
        if not self._orgnr_pattern.fullmatch(normalized_number):
            raise ValueError("Norwegian organization number must contain exactly 9 digits.")

        url = f"{self.base_url}/enheter/{normalized_number}"
        response = self._client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()

        try:
            response_body = response.content
            response_text = response_body.decode("utf-8")
            payload = json.loads(response_body)
            returned_number = str(payload["organisasjonsnummer"])
            legal_name = payload["navn"]
        except (ValueError, KeyError, TypeError) as exc:
            raise NorwayRegistryProtocolError("Norwegian registry record is missing required fields.") from exc

        if returned_number != normalized_number:
            raise NorwayRegistryProtocolError("Norwegian registry organization number did not match request.")
        if not isinstance(legal_name, str) or not legal_name.strip():
            raise NorwayRegistryProtocolError("Norwegian registry record did not include a legal name.")

        legal_form = payload.get("organisasjonsform")
        if isinstance(legal_form, dict):
            legal_form = legal_form.get("kode") or legal_form.get("beskrivelse")
        observed_at = datetime.now(UTC)
        observation = SourceObservation(
            source_id=self.source_id,
            source_record_id=normalized_number,
            canonical_url=self.record_url.format(orgnr=normalized_number),
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
            jurisdiction="NO",
            registration_status=_boolean_status(payload.get("underAvvikling")),
            entity_status="deleted" if payload.get("slettedato") else "active",
            legal_form=legal_form,
            registered_address=_format_address(payload.get("forretningsadresse")),
        )
        return EntityLookup(entity=record, observation=observation)

    def fetch_roles(self, organization_number: str) -> SourceBatch:
        number = organization_number.strip()
        if not self._orgnr_pattern.fullmatch(number):
            raise ValueError("Norwegian organization number must contain exactly 9 digits.")
        url = f"{self.base_url}/enheter/{number}/roller"
        response = self._client.get(url)
        response.raise_for_status()
        try:
            payload = response.json()
            groups = payload["rollegrupper"]
            if not isinstance(groups, list):
                raise TypeError("Role groups must be a list")
            own_url = payload.get("_links", {}).get("enhet", {}).get("href")
            if own_url and own_url != f"{self.base_url}/enheter/{number}":
                raise ValueError("Organization identity mismatch")
            records = []
            for group_index, group in enumerate(groups):
                group_code = group["type"]["kode"]
                for role_index, role in enumerate(group["roller"]):
                    holder = role.get("person") or role.get("enhet")
                    holder_type = "person" if role.get("person") else "organization"
                    name = holder["navn"]
                    if isinstance(name, dict):
                        name = " ".join(name.get(part, "") for part in ("fornavn", "mellomnavn", "etternavn") if name.get(part))
                    elif isinstance(name, list):
                        name = " ".join(name)
                    if not isinstance(name, str) or not name.strip():
                        raise ValueError("Missing role-holder name")
                    if type(role["avregistrert"]) is not bool:
                        raise TypeError("Invalid deregistration flag")
                    record = OrganizationRole(
                        source_id=self.source_id, source_record_id=f"{number}:roles:{group_index}:{role_index}",
                        organization_number=number, display_name=name.strip(), holder_type=holder_type,
                        holder_registration_id=holder.get("organisasjonsnummer"), role_code=role["type"]["kode"],
                        role_name=role["type"]["beskrivelse"], group_code=group_code,
                        group_last_changed=group.get("sistEndret"), deregistered=role["avregistrert"],
                        is_board_role=group_code == "STYR",
                    )
                    records.append(record.model_dump(mode="json"))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise NorwayRegistryProtocolError("Norwegian roles payload failed validation.") from exc
        observation = SourceObservation(
            source_id=self.source_id, source_record_id=f"{number}:roles", canonical_url=url,
            observed_at=datetime.now(UTC), connector_version=self.connector_version,
            content_hash=f"sha256:{hashlib.sha256(response.content).hexdigest()}",
            raw_payload=payload, payload_format="application/json", raw_response_text=response.content.decode("utf-8"),
        )
        return SourceBatch(observations=[observation], records=records,
                           limitations=["Roles reflect the registry snapshot; deregistered roles are explicitly flagged."])


def _boolean_status(under_liquidation: object) -> str | None:
    if under_liquidation is True:
        return "under_liquidation"
    if under_liquidation is False:
        return "not_under_liquidation"
    return None


def _format_address(address: object) -> str | None:
    if not isinstance(address, dict):
        return None
    parts = [
        *(address.get("adresse") or []),
        address.get("postnummer"),
        address.get("poststed"),
        address.get("land"),
    ]
    formatted = ", ".join(str(part).strip() for part in parts if str(part or "").strip())
    return formatted or None
