from unittest.mock import Mock

import httpx
import pytest

from trust_signal.connectors.feeds import FCANewsAdapter, GazetteInsolvencyAdapter, parse_feed
from trust_signal.connectors.gdelt import GDELTNewsAdapter
from trust_signal.connectors.http_source import SourceSchemaError
from trust_signal.connectors.registry import SourceRequest, default_registry
from trust_signal.connectors.worldbank import WorldBankDebarmentAdapter
from trust_signal.ingestion.pipeline import IngestionPipeline


def atom(code):
    return f'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:f="https://www.thegazette.co.uk/facets">
      <entry><id>notice-1</id><title>Example Ltd</title><link href="https://www.thegazette.co.uk/notice/1"/>
      <f:notice-code>{code}</f:notice-code><f:status>published</f:status></entry></feed>'''.encode()


@pytest.mark.parametrize("code,status,outcome", [
    ("2450", "proceeding", None), ("2452", "decision", "winding_up_order_published"),
    ("2461", "decision", "petition_dismissal_published"),
])
def test_gazette_petition_order_and_dismissal_are_distinct(code, status, outcome):
    records, _ = parse_feed(httpx.Response(200, content=atom(code)), "source", "insolvency_notice", "www.thegazette.co.uk")
    assert records[0]["procedural_status"] == status
    assert records[0]["outcome"] == outcome
    assert records[0]["finality"] == "unknown"
    assert records[0]["identity_status"] == "unmatched_candidate"


def test_personal_insolvency_is_rejected_by_corporate_connector():
    with pytest.raises(SourceSchemaError):
        parse_feed(httpx.Response(200, content=atom("2509")), "source", "insolvency_notice", "www.thegazette.co.uk")


def test_gazette_queries_name_and_marks_truncated_coverage():
    def respond(request):
        assert request.url.params["text"] == "Example Ltd"
        assert request.url.params["categorycode"] == "24"
        return httpx.Response(200, content=atom("2450").replace(b"<entry>", b'<link rel="next" href="https://www.thegazette.co.uk/ignored"/><entry>'))
    with GazetteInsolvencyAdapter(transport=httpx.MockTransport(respond)) as adapter:
        batches = list(adapter.search("Example Ltd", 1))
    assert not batches[0].complete


def test_newsroom_does_not_infer_finality_from_headline():
    raw = b'<rss><channel><item><guid>1</guid><title>Firm fined for fraud</title><link>https://www.fca.org.uk/news/example</link></item></channel></rss>'
    with FCANewsAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))) as adapter:
        batch = adapter.fetch_recent()
    assert batch.records[0]["procedural_status"] == "unknown"
    assert batch.records[0]["finality"] == "unknown"
    assert not batch.complete


def test_court_automated_use_is_blocked_without_permission(monkeypatch):
    fetch = Mock(side_effect=AssertionError("Must not fetch"))
    monkeypatch.setattr("trust_signal.connectors.feeds.FindCaseLawAdapter.search", fetch)
    result = IngestionPipeline(default_registry({}), Mock(), Mock()).ingest(
        SourceRequest(source_id="uk_find_case_law", operation="search", value="Example"))
    assert result.coverage == "blocked"
    fetch.assert_not_called()


def test_false_permission_flag_is_not_advertised_as_configured():
    registry = default_registry({"FIND_CASELAW_COMPUTATIONAL_LICENSE_APPROVED": "false"})
    source = next(row for row in registry.catalog() if row["source_id"] == "uk_find_case_law")
    assert not source["configured"]


def test_worldbank_retains_cross_debarment_and_dates_without_conviction_claim():
    page = b'<script>var propApiKey = "public-browser-key";</script>'
    payload = {"response": {"ZPROCSUPP": [{"SUPP_ID": 1, "SUPP_NAME": "Example",
        "ELIG_STAT": "X-DEBARRED", "INELIG_FLG": "X", "DEBAR_FROM_DATE": "2025-01-01"}]}}
    def respond(request):
        if request.url.host == "apigwext.worldbank.org":
            assert request.headers["apikey"] == "public-browser-key"
            return httpx.Response(200, json=payload)
        return httpx.Response(200, content=page)
    with WorldBankDebarmentAdapter(transport=httpx.MockTransport(respond)) as adapter:
        batch = adapter.fetch_snapshot()
    assert len(batch.observations) == 2
    assert batch.records[0]["outcome"] == "X-DEBARRED"
    assert batch.records[0]["metadata"]["INELIG_FLG"] == "X"
    assert batch.records[0]["finality"] == "unknown"


def test_gdelt_uses_exact_phrase_and_keeps_seen_time_separate():
    payload = {"articles": [{"url": "https://example.org/news/1", "title": "Example",
                              "seendate": "20261003T000000Z", "language": "French"}]}
    def respond(request):
        assert request.url.params["query"] == '"Example Ltd"'
        return httpx.Response(200, json=payload)
    with GDELTNewsAdapter(transport=httpx.MockTransport(respond)) as adapter:
        batch = adapter.search("Example Ltd")
    assert batch.records[0]["published_at"] is None
    assert batch.records[0]["metadata"]["publisher_trust"] == "not_assessed"
    assert batch.records[0]["metadata"]["content_rights"] == "metadata_and_links_only"


def test_gdelt_query_injection_is_rejected_before_fetch():
    with GDELTNewsAdapter(transport=httpx.MockTransport(lambda _: pytest.fail("Must not fetch"))) as adapter, pytest.raises(ValueError):
        adapter.search('Example" OR fraud')


def test_http_rate_limit_is_recorded_without_retry_storm():
    def fetch(_):
        response = httpx.Response(429, headers={"Retry-After": "60"}, request=httpx.Request("GET", "https://example.org"))
        response.raise_for_status()
    registry = default_registry({})
    from trust_signal.connectors.registry import SourceDefinition, SourceRegistry
    definition = registry.get(SourceRequest(source_id="gdelt_doc_news", operation="search", value="Example"))
    registry = SourceRegistry([SourceDefinition(definition.source_id, "0.1.0", (), ("search",), fetch)])
    result = IngestionPipeline(registry, Mock(), Mock()).ingest(
        SourceRequest(source_id=definition.source_id, operation="search", value="Example"))
    assert result.http_status == 429 and result.retry_after == "60"
    assert result.coverage == "failed" and result.records == []
