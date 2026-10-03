import base64
import hashlib
import json
import re

import httpx
import pytest

from trust_signal.connectors.gleif import GleifAdapter
from trust_signal.ingestion.raw_export import export_observation


def lookup_for_test():
    # Network-independent contract test only; never used for the live export.
    lei = "5493001KJTIIGC8Y1R12"
    payload = {"data": {"id": lei, "attributes": {
        "lei": lei, "entity": {"legalName": {"name": "Test O'Neil \u00c9nergie"}},
    }}}
    response = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, content=response))
    with GleifAdapter(transport=transport) as adapter:
        lookup = adapter.fetch_by_lei(lei)
    return lookup, response


def test_export_preserves_exact_response_and_replay_identity(tmp_path):
    lookup, response = lookup_for_test()
    first = export_observation(lookup, tmp_path)
    second = export_observation(lookup, tmp_path)
    assert first["observation_id"] == second["observation_id"]
    assert (tmp_path / "raw_response.json").read_bytes() == response
    sql = (tmp_path / "load_observation.sql").read_text()
    encoded = re.search(r"BASE64_DECODE_STRING\('([^']+)'\)", sql)[1]
    assert base64.b64decode(encoded) == response
    assert "sha256:" + hashlib.sha256(response).hexdigest() in sql
    assert "NOT EXISTS" in sql
    assert "prepared_not_executed" == first["load_status"]
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["observation"]["raw_payload"] == json.loads(response)
    assert "raw_response_text" not in manifest["observation"]


def test_export_rejects_hash_mismatch_before_writing(tmp_path):
    lookup, _ = lookup_for_test()
    lookup.observation.raw_response_text += " "
    with pytest.raises(ValueError, match="hash does not match"):
        export_observation(lookup, tmp_path)
    assert not list(tmp_path.iterdir())


def test_export_rejects_unsafe_database_identifier(tmp_path):
    lookup, _ = lookup_for_test()
    with pytest.raises(ValueError, match="identifier"):
        export_observation(lookup, tmp_path, "DEV; DROP DATABASE DEV")
    assert not list(tmp_path.iterdir())


def test_export_rejects_missing_original_response(tmp_path):
    lookup, _ = lookup_for_test()
    lookup.observation.raw_response_text = None
    with pytest.raises(ValueError, match="exact raw response"):
        export_observation(lookup, tmp_path)
