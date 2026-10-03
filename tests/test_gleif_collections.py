import httpx
import pytest
from test_gleif_connector import LEI, gleif_payload

from trust_signal.connectors.gleif import GleifAdapter, SourceProtocolError


def test_search_paginates_and_marks_candidates():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"data": [gleif_payload()["data"]], "links": {
            "next": "https://api.gleif.org/api/v1/lei-records?page[number]=2" if len(calls) == 1 else None}})

    with GleifAdapter(transport=httpx.MockTransport(handler)) as adapter:
        batches = list(adapter.search_by_name("Example"))
    assert calls[0].url.params["filter[entity.legalName]"] == "Example"
    assert len(batches) == 2 and all(b.complete for b in batches)
    assert batches[0].records[0]["identity_status"] == "candidate_requires_resolution"


def test_search_cap_is_partial_and_external_next_link_is_rejected():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
        "data": [], "links": {"next": "https://untrusted.example/next"}}))
    with GleifAdapter(transport=transport) as adapter:
        assert next(adapter.search_by_name("Example", max_pages=1)).complete is False
        with pytest.raises(SourceProtocolError, match="untrusted"):
            list(adapter.search_by_name("Example", max_pages=2))


def test_parent_reporting_exceptions_are_retained():
    payload = gleif_payload()
    payload["data"]["relationships"] = {direction: {"links": {
        "reporting-exception": f"https://api.gleif.org/api/v1/lei-records/{LEI}/{direction}-reporting-exception"}}
        for direction in ("direct-parent", "ultimate-parent")}

    def handler(request):
        if request.url.path.endswith(LEI):
            return httpx.Response(200, json=payload)
        return httpx.Response(200, json={"data": {"id": "exception_1", "type": "reporting-exceptions",
                                                 "attributes": {"exceptionReasons": ["NO_KNOWN_PERSON"]}}})

    with GleifAdapter(transport=httpx.MockTransport(handler)) as adapter:
        batches = list(adapter.fetch_relationships(LEI))
    assert [b.records[0]["record_type"] for b in batches[1:3]] == ["reporting-exceptions"] * 2
    assert batches[-1].complete is False


def test_candidate_identity_mismatch_is_rejected():
    node = gleif_payload()["data"]
    node["id"] = "wrong"
    with GleifAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": [node]}))) as adapter, pytest.raises(SourceProtocolError):
        list(adapter.search_by_name("Example"))
