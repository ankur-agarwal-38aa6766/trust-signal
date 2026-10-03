"""Snowflake storage adapter using a named, locally authenticated CLI connection."""

from __future__ import annotations

import json
import subprocess

from trust_signal.connectors.base import SourceObservation
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.contracts import ObservationReceipt


class ObservationWriteError(RuntimeError):
    """A write failed or its stored result could not be verified."""


def _rows(value: object) -> list[dict]:
    if not isinstance(value, list):
        raise ObservationWriteError("Snowflake returned an unexpected result format.")
    rows = []
    for item in value:
        if isinstance(item, list):
            rows.extend(_rows(item))
        elif isinstance(item, dict):
            rows.append(item)
        else:
            raise ObservationWriteError("Snowflake returned an unexpected result row.")
    return rows


class SnowflakeCliObservationStore:
    """Single-writer MVP adapter; callers retain the observation for safe replay."""

    def __init__(
        self, connection: str, database: str = "TRUST_SIGNAL_DEV", timeout: float = 180,
        *, executor=None,
    ):
        if not connection or connection.startswith("-"):
            raise ValueError("A named Snowflake connection is required.")
        self.connection = connection
        self.database = database
        self.timeout = timeout
        self.executor = executor

    def store_observation(self, observation: SourceObservation) -> ObservationReceipt:
        prepared = prepare_observation(observation, self.database)
        rows = self.execute(prepared.insert_sql + "\n" + prepared.verify_sql)
        return self._receipt(observation, prepared, rows)

    def execute(self, sql: str) -> list[dict]:
        """Execute SQL without exposing CLI authentication output in errors."""
        if self.executor is not None:
            return self.executor.execute(sql)
        command = [
            "snow", "sql", "--connection", self.connection,
            "--database", self.database, "--format", "JSON", "--silent", "--stdin",
        ]
        try:
            result = subprocess.run(
                command,
                input=sql,
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ObservationWriteError("Snowflake CLI is not installed or not on PATH.") from exc
        except subprocess.TimeoutExpired as exc:
            raise ObservationWriteError(
                "Snowflake timed out; the write outcome is unknown. Replay the same observation."
            ) from exc
        if result.returncode:
            # CLI output can contain authentication details. Do not echo it in errors.
            raise ObservationWriteError(
                "Snowflake command failed. Test the named connection and table access; "
                "the write outcome may be unknown."
            )
        try:
            rows = _rows(json.loads(result.stdout))
        except json.JSONDecodeError as exc:
            raise ObservationWriteError(
                "Snowflake returned invalid JSON; the write outcome is unknown."
            ) from exc
        return rows

    def _receipt(self, observation, prepared, rows) -> ObservationReceipt:
        stored = [row for row in rows if "OBSERVATION_ID" in row]
        if len(stored) != 1:
            raise ObservationWriteError("Expected exactly one stored observation; verification failed.")
        row = stored[0]
        expected = {
            "OBSERVATION_ID": prepared.observation_id,
            "SOURCE_ID": observation.source_id,
            "SOURCE_RECORD_ID": observation.source_record_id,
            "CANONICAL_URL": observation.canonical_url,
            "CONNECTOR_VERSION": observation.connector_version,
            "PAYLOAD_FORMAT": observation.payload_format,
            "CONTENT_HASH": observation.content_hash,
            "STORED_RESPONSE_HASH": observation.content_hash,
        }
        if any(row.get(key) != value for key, value in expected.items()):
            raise ObservationWriteError("Stored observation metadata does not match the source.")
        try:
            payload = json.loads(row["PAYLOAD_JSON"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ObservationWriteError("Stored payload could not be verified.") from exc
        if payload != observation.raw_payload:
            raise ObservationWriteError("Stored payload does not match the source response.")
        inserted = [row.get("number of rows inserted") for row in rows
                    if "number of rows inserted" in row]
        if len(inserted) != 1 or type(inserted[0]) is not int or inserted[0] not in (0, 1):
            raise ObservationWriteError("Snowflake insert count could not be verified.")
        return ObservationReceipt(
            prepared.observation_id, observation.source_id, observation.source_record_id,
            observation.content_hash, inserted[0], len(stored),
        )
