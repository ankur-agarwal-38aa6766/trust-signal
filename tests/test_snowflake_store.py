import json
import subprocess

import pytest
from test_raw_export import lookup_for_test

from trust_signal.ingestion.load import load_bundle
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.ingestion.raw_export import export_observation
from trust_signal.persistence.snowflake_cli import (
    ObservationWriteError,
    SnowflakeCliObservationStore,
)


def stored_row(observation):
    return {
        "OBSERVATION_ID": prepare_observation(observation).observation_id,
        "SOURCE_ID": observation.source_id,
        "SOURCE_RECORD_ID": observation.source_record_id,
        "CANONICAL_URL": observation.canonical_url,
        "CONNECTOR_VERSION": observation.connector_version,
        "PAYLOAD_FORMAT": "application/vnd.api+json",
        "CONTENT_HASH": observation.content_hash,
        "STORED_RESPONSE_HASH": observation.content_hash,
        "PAYLOAD_JSON": json.dumps(observation.raw_payload),
    }


@pytest.mark.parametrize("inserted", [0, 1])
def test_store_checks_payload_and_reports_insert_or_replay(monkeypatch, inserted):
    lookup, _ = lookup_for_test()
    observation = lookup.observation

    def run(command, **kwargs):
        assert command == [
            "snow", "sql", "--connection", "trust_signal_dev", "--database", "TRUST_SIGNAL_DEV",
            "--format", "JSON", "--silent", "--stdin",
        ]
        assert "INSERT INTO" in kwargs["input"]
        assert "TO_JSON(RAW_PAYLOAD)" in kwargs["input"]
        assert "shell" not in kwargs
        results = [[{"number of rows inserted": inserted}], [stored_row(observation)]]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(results))

    monkeypatch.setattr(subprocess, "run", run)
    receipt = SnowflakeCliObservationStore("trust_signal_dev").store_observation(observation)
    assert receipt.inserted_rows == inserted
    assert receipt.verified_rows == 1
    assert receipt.content_hash == observation.content_hash


@pytest.mark.parametrize("failure", ["payload", "hash", "duplicate", "missing", "count"])
def test_store_rejects_unverifiable_result(monkeypatch, failure):
    lookup, _ = lookup_for_test()
    row = stored_row(lookup.observation)
    rows = [row]
    if failure == "payload":
        row["PAYLOAD_JSON"] = '{"changed": true}'
    elif failure == "hash":
        row["CONTENT_HASH"] = "wrong"
    elif failure == "duplicate":
        rows.append(row.copy())
    elif failure == "missing":
        rows = []
    counts = [] if failure == "count" else [{"number of rows inserted": 1}]
    monkeypatch.setattr(subprocess, "run", lambda command, **_kwargs:
                        subprocess.CompletedProcess(command, 0, stdout=json.dumps([counts, rows])))
    with pytest.raises(ObservationWriteError):
        SnowflakeCliObservationStore("trust_signal_dev").store_observation(lookup.observation)


def test_failed_command_does_not_expose_authentication_output(monkeypatch):
    lookup, _ = lookup_for_test()
    monkeypatch.setattr(subprocess, "run", lambda command, **_kwargs:
                        subprocess.CompletedProcess(command, 1, stdout="", stderr="secret-token"))
    with pytest.raises(ObservationWriteError) as error:
        SnowflakeCliObservationStore("trust_signal_dev").store_observation(lookup.observation)
    assert "secret-token" not in str(error.value)


def test_timeout_reports_unknown_write_outcome(monkeypatch):
    lookup, _ = lookup_for_test()

    def timeout(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 180)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(ObservationWriteError, match="outcome is unknown"):
        SnowflakeCliObservationStore("trust_signal_dev").store_observation(lookup.observation)


def test_corrupt_response_is_rejected_before_sql_execution(monkeypatch):
    lookup, _ = lookup_for_test()
    lookup.observation.raw_response_text += " "
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs:
                        pytest.fail("Unexpected SQL execution"))
    with pytest.raises(ValueError, match="hash does not match"):
        SnowflakeCliObservationStore("trust_signal_dev").store_observation(lookup.observation)


def test_saved_bundle_load_updates_status_only_after_verified_write(tmp_path, monkeypatch):
    lookup, _ = lookup_for_test()
    export_observation(lookup, tmp_path)
    rows = [[{"number of rows inserted": 0}], [stored_row(lookup.observation)]]
    monkeypatch.setattr(subprocess, "run", lambda command, **_kwargs:
                        subprocess.CompletedProcess(command, 0, stdout=json.dumps(rows)))
    receipt = load_bundle(tmp_path, SnowflakeCliObservationStore("trust_signal_dev"))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["load_status"] == "verified_in_snowflake"
    assert manifest["last_load_receipt"]["observation_id"] == receipt.observation_id


def test_bundle_load_failure_leaves_manifest_unverified(tmp_path, monkeypatch):
    lookup, _ = lookup_for_test()
    export_observation(lookup, tmp_path)
    original = (tmp_path / "manifest.json").read_bytes()
    monkeypatch.setattr(subprocess, "run", lambda command, **_kwargs:
                        subprocess.CompletedProcess(command, 1, stdout="", stderr="error"))
    with pytest.raises(ObservationWriteError):
        load_bundle(tmp_path, SnowflakeCliObservationStore("trust_signal_dev"))
    assert (tmp_path / "manifest.json").read_bytes() == original
