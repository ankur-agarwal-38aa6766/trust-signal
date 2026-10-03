import json
from unittest.mock import Mock

import pytest
from test_raw_export import lookup_for_test

from trust_signal.ingestion.observation import prepare_observation
from trust_signal.ingestion.raw_export import ingest_tracked
from trust_signal.persistence.contracts import ObservationReceipt
from trust_signal.persistence.source_runs import (
    SnowflakeCliSourceRunStore,
    SourceRun,
    SourceRunWriteError,
)


def setup_flow():
    lookup, _ = lookup_for_test()
    adapter = Mock(source_id="gleif_lei_api", connector_version="0.1.0")
    adapter.fetch_by_lei.return_value = lookup
    store = Mock()
    observation = lookup.observation
    store.store_observation.return_value = ObservationReceipt(
        prepare_observation(observation).observation_id, observation.source_id,
        observation.source_record_id, observation.content_hash, 1, 1,
    )
    return lookup, adapter, store, Mock()


def test_success_records_counts_and_manifest_link(tmp_path):
    lookup, adapter, store, runs = setup_flow()
    result = ingest_tracked(adapter, lookup.entity.lei, lookup.entity.legal_name, tmp_path,
                            "TRUST_SIGNAL_DEV", store, runs)
    run, status, seen, accepted, error, details = runs.finish.call_args.args
    assert (status, seen, accepted, error) == ("succeeded", 1, 1, None)
    assert details["observation_id"] == result["observation_id"]
    assert details["inserted_rows"] == 1
    assert json.loads((tmp_path / "manifest.json").read_text())["source_run_id"] == run.run_id


@pytest.mark.parametrize("failure,stage,seen", [
    ("fetch", "fetch", 0), ("missing", "not_found", 0),
    ("identity", "identity_check", 1), ("storage", "storage", 1),
])
def test_failure_is_sanitized_and_recorded(tmp_path, failure, stage, seen):
    lookup, adapter, store, runs = setup_flow()
    if failure == "fetch":
        adapter.fetch_by_lei.side_effect = RuntimeError("secret-token")
    if failure == "missing":
        adapter.fetch_by_lei.return_value = None
    if failure == "storage":
        store.store_observation.side_effect = RuntimeError("secret-token")
    name = "wrong" if failure == "identity" else lookup.entity.legal_name
    with pytest.raises(RuntimeError, match=stage) as error:
        ingest_tracked(adapter, lookup.entity.lei, name, tmp_path, "TRUST_SIGNAL_DEV", store, runs)
    assert "secret-token" not in str(error.value)
    args = runs.finish.call_args.args
    assert args[1:5] == ("failed", seen, 0, stage)
    assert "secret-token" not in json.dumps(args[5])
    if failure != "storage":
        store.store_observation.assert_not_called()
    else:
        assert args[5]["storage_outcome"] == "unknown"


def test_start_failure_prevents_fetch(tmp_path):
    lookup, adapter, store, runs = setup_flow()
    runs.start.side_effect = SourceRunWriteError("start failed")
    with pytest.raises(SourceRunWriteError):
        ingest_tracked(adapter, lookup.entity.lei, lookup.entity.legal_name, tmp_path,
                       "TRUST_SIGNAL_DEV", store, runs)
    adapter.fetch_by_lei.assert_not_called()


def test_terminal_log_failure_retains_verified_bundle(tmp_path):
    lookup, adapter, store, runs = setup_flow()
    runs.finish.side_effect = SourceRunWriteError("finish failed")
    with pytest.raises(SourceRunWriteError):
        ingest_tracked(adapter, lookup.entity.lei, lookup.entity.legal_name, tmp_path,
                       "TRUST_SIGNAL_DEV", store, runs)
    assert runs.finish.call_count == 1
    assert json.loads((tmp_path / "manifest.json").read_text())["load_status"] == "verified_in_snowflake"


@pytest.mark.parametrize("corrupt", [False, True])
def test_snowflake_run_write_requires_readback(corrupt):
    run = SourceRun.create("gleif_lei_api", "0.1.0")
    store = SnowflakeCliSourceRunStore("trust_signal_dev")
    details = {"stage": "fetch", "requested_record_id": "O'Neil"}
    row = {"SOURCE_RUN_ID": run.run_id, "SOURCE_ID": run.source_id,
           "CONNECTOR_VERSION": run.connector_version, "RUN_STATUS": "running",
           "RECORDS_SEEN": 0, "RECORDS_ACCEPTED": 0, "ERROR_CATEGORY": None,
           "IS_COMPLETE": False, "DETAILS_JSON": json.dumps(details)}
    store.cli.execute = Mock(return_value=[row, row] if corrupt else [row])
    if corrupt:
        with pytest.raises(SourceRunWriteError):
            store.start(run, details)
    else:
        store.start(run, details)
        assert "O'Neil" not in store.cli.execute.call_args.args[0]


def test_run_store_rejects_unsafe_database():
    with pytest.raises(ValueError):
        SnowflakeCliSourceRunStore("trust_signal_dev", "DEV; DROP DATABASE DEV")


@pytest.mark.parametrize("seen,accepted", [(0, 1), (-1, 0), (True, 1), (1, 0.5)])
def test_run_store_rejects_invalid_counts(seen, accepted):
    store = SnowflakeCliSourceRunStore("trust_signal_dev")
    with pytest.raises(ValueError):
        store.finish(SourceRun.create("gleif_lei_api", "0.1.0"), "succeeded",
                     seen, accepted, None, {})


def test_terminal_write_is_guarded_and_verified():
    store = SnowflakeCliSourceRunStore("trust_signal_dev")
    run = SourceRun.create("gleif_lei_api", "0.1.0")
    details = {"stage": "complete"}
    row = {"SOURCE_RUN_ID": run.run_id, "SOURCE_ID": run.source_id,
           "CONNECTOR_VERSION": run.connector_version, "RUN_STATUS": "succeeded",
           "RECORDS_SEEN": 1, "RECORDS_ACCEPTED": 1, "ERROR_CATEGORY": None,
           "IS_COMPLETE": True, "DETAILS_JSON": json.dumps(details)}
    store.cli.execute = Mock(return_value=[row])
    store.finish(run, "succeeded", 1, 1, None, details)
    assert "AND RUN_STATUS = 'running'" in store.cli.execute.call_args.args[0]
    row["DETAILS_JSON"] = '{}'
    with pytest.raises(SourceRunWriteError):
        store.finish(run, "succeeded", 1, 1, None, details)


def test_export_failure_does_not_store_evidence(tmp_path, monkeypatch):
    lookup, adapter, store, runs = setup_flow()
    monkeypatch.setattr("trust_signal.ingestion.raw_export.export_observation",
                        Mock(side_effect=OSError("private-path")))
    with pytest.raises(RuntimeError, match="export"):
        ingest_tracked(adapter, lookup.entity.lei, lookup.entity.legal_name, tmp_path,
                       "TRUST_SIGNAL_DEV", store, runs)
    assert runs.finish.call_args.args[1:5] == ("failed", 1, 0, "export")
    store.store_observation.assert_not_called()
