from unittest.mock import Mock

import pytest
from test_raw_export import lookup_for_test

from trust_signal.connectors.base import SourceBatch
from trust_signal.connectors.registry import (
    SourceDefinition,
    SourceRegistry,
    SourceRequest,
    default_registry,
)
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.persistence.contracts import ObservationReceipt


def setup_pipeline(fetch=None):
    lookup, _ = lookup_for_test()
    batch = SourceBatch(observations=[lookup.observation], records=[{"legal_name": "Example"}])
    definition = SourceDefinition(lookup.observation.source_id, "0.1.0", ("global",),
                                  ("lookup",), fetch or (lambda _: iter([batch])))
    store = Mock()
    store.store_observation.return_value = ObservationReceipt(
        "obs_1", lookup.observation.source_id, lookup.observation.source_record_id,
        lookup.observation.content_hash, 1, 1)
    runs = Mock()
    pipeline = IngestionPipeline(SourceRegistry([definition]), store, runs)
    request = SourceRequest(source_id=definition.source_id, operation="lookup", value="identifier")
    return pipeline, request, store, runs, batch


def test_releases_records_only_after_evidence_and_terminal_log_are_verified():
    pipeline, request, store, runs, _ = setup_pipeline()
    calls = Mock()
    calls.attach_mock(store.store_observation, "store")
    calls.attach_mock(runs.finish, "finish")
    result = pipeline.ingest(request)
    assert result.coverage == "available"
    assert result.records[0]["observation_ids"] == ["obs_1"]
    assert [call[0] for call in calls.mock_calls] == ["store", "finish"]


def test_parallel_specialists_share_one_serialized_ingestion_session():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    pipeline, request, _, _, batch = setup_pipeline()
    first_entered, release_first, second_attempted, second_entered = (Event() for _ in range(4))
    calls = []

    def fetch(_):
        calls.append("fetch")
        if len(calls) == 1:
            first_entered.set()
            assert release_first.wait(timeout=3)
        else:
            second_entered.set()
        yield batch

    pipeline.registry = SourceRegistry([
        SourceDefinition(request.source_id, "0.1.0", (), ("lookup",), fetch)])

    def second():
        second_attempted.set()
        return pipeline.ingest(request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(pipeline.ingest, request)
        try:
            assert first_entered.wait(timeout=3)
            other = executor.submit(second)
            assert second_attempted.wait(timeout=3)
            assert not second_entered.wait(timeout=0.05)
        finally:
            release_first.set()
        assert first.result(timeout=3).coverage == "available"
        assert other.result(timeout=3).coverage == "available"
    assert second_entered.is_set()


def test_write_failure_records_gap_and_does_not_release_records():
    pipeline, request, store, runs, _ = setup_pipeline()
    store.store_observation.side_effect = RuntimeError("secret-token")
    result = pipeline.ingest(request)
    assert result.coverage == "failed" and not result.records
    details = runs.finish.call_args.args[-1]
    assert details["storage_outcome"] == "unknown"
    assert "secret-token" not in str(result)


def test_later_fetch_failure_keeps_receipts_but_withholds_all_records():
    pipeline, request, _store, runs, batch = setup_pipeline()

    def fetch(_):
        yield batch
        raise RuntimeError("provider failure")

    pipeline.registry = SourceRegistry([SourceDefinition(request.source_id, "0.1.0", (), ("lookup",), fetch)])
    result = pipeline.ingest(request)
    assert result.coverage == "failed" and result.receipts and not result.records
    assert runs.finish.call_args.args[2:4] == (1, 1)


def test_partial_and_empty_coverage_are_distinct():
    pipeline, request, _, _, batch = setup_pipeline()
    batch.complete = False
    assert pipeline.ingest(request).coverage == "partial"
    batch.records = []
    batch.complete = True
    assert pipeline.ingest(request).coverage == "no_matches"


def test_log_failure_prevents_records_from_reaching_caller():
    pipeline, request, store, runs, _ = setup_pipeline()
    runs.finish.side_effect = RuntimeError("log failed")
    with pytest.raises(RuntimeError, match="log failed"):
        pipeline.ingest(request)
    store.store_observation.assert_called_once()


def test_missing_credential_is_tracked_without_fetching(monkeypatch):
    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    observations, runs = Mock(), Mock()
    result = IngestionPipeline(default_registry(), observations, runs).ingest(
        SourceRequest(source_id="uk_companies_house", operation="lookup", value="00445790"))
    assert result.coverage == "blocked"
    observations.store_observation.assert_not_called()
    assert runs.finish.call_args.args[1] == "failed"


def test_invalid_request_and_registry_are_rejected():
    with pytest.raises(ValueError):
        SourceRequest(source_id="gleif_lei_api", operation="search")
    with pytest.raises(ValueError):
        default_registry().get(SourceRequest(source_id="uk_companies_house", operation="search", value="Tesco"))


def test_unverified_receipt_withholds_records():
    pipeline, request, store, _, _ = setup_pipeline()
    store.store_observation.return_value = ObservationReceipt("obs", request.source_id, "wrong", "wrong", 1, 0)
    assert not pipeline.ingest(request).records
