"""Shared bounded HTTP transport and provenance capture for new source adapters."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Self

import httpx

from trust_signal.connectors.base import SourceObservation


class SourceSchemaError(RuntimeError):
    """A source response failed the expected schema; no partial list is accepted."""


class HttpSource:
    connector_version = "0.1.0"
    source_id: str

    def __init__(self, transport: httpx.BaseTransport | None = None, timeout: float = 60):
        self._client = httpx.Client(transport=transport, timeout=timeout, follow_redirects=True,
                                   headers={"User-Agent": "TrustSignal/0.1", "Accept": "*/*"})

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args) -> None:
        self._client.close()

    def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> httpx.Response:
        with self._client.stream("GET", url, params=params, headers=headers) as response:
            response.raise_for_status()
            pieces = []
            length = 0
            for piece in response.iter_bytes():
                length += len(piece)
                if length > 64 * 1024 * 1024:
                    raise SourceSchemaError("Response exceeded the 64 MiB source limit.")
                pieces.append(piece)
            # iter_bytes has already decompressed the response; avoid a second decode.
            decoded_headers = {key: value for key, value in response.headers.items()
                               if key.lower() not in {"content-encoding", "content-length"}}
            return httpx.Response(response.status_code, headers=decoded_headers,
                                  content=b"".join(pieces), request=response.request)

    def observation(self, response: httpx.Response, record_id: str, payload: dict,
                    payload_format: str = "application/xml", binary: bool = False,
                    canonical_url: str | None = None) -> SourceObservation:
        return SourceObservation(
            source_id=self.source_id, source_record_id=record_id, canonical_url=canonical_url or str(response.url),
            observed_at=datetime.now(UTC), connector_version=self.connector_version,
            content_hash="sha256:" + hashlib.sha256(response.content).hexdigest(),
            raw_payload=payload, payload_format=payload_format,
            raw_response_text=None if binary else response.content.decode("utf-8"),
            raw_response_bytes=response.content if binary else None,
        )


def xml_text(node, path: str) -> str | None:
    value = node.findtext(path)
    return value.strip() if value and value.strip() else None
