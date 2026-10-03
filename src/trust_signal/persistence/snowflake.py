"""Snowflake observation repository, independent of its connection transport."""

import base64
import hashlib
import json

from trust_signal.connectors.base import SourceObservation
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.contracts import (
    ObservationReceipt,
    ObservationWriteError,
    SqlExecutor,
)


class SnowflakeObservationStore:
    """Single-writer repository with full metadata and payload readback checks."""

    def __init__(self, executor: SqlExecutor, database: str = "TRUST_SIGNAL_DEV"):
        self.executor = executor
        self.database = database

    def store_observation(self, observation: SourceObservation) -> ObservationReceipt:
        prepared = prepare_observation(observation, self.database)
        if prepared.chunk_sql:
            inserts = self.execute(prepared.insert_sql)
            for statement in prepared.chunk_sql:
                self.execute(statement)
            chunks = self.execute(prepared.verify_chunks_sql)
            if len(chunks) != len(prepared.chunk_sql):
                raise ObservationWriteError("Raw response chunk count does not match.")
            content = bytearray()
            try:
                for index, chunk in enumerate(chunks):
                    piece = base64.b64decode(chunk["RAW_BYTES_BASE64"], validate=True)
                    if chunk["CHUNK_INDEX"] != index or hashlib.sha256(piece).hexdigest() != chunk["CHUNK_HASH"]:
                        raise ValueError("Chunk sequence or hash mismatch")
                    content.extend(piece)
            except (KeyError, TypeError, ValueError) as exc:
                raise ObservationWriteError("Raw response chunks failed verification.") from exc
            if bytes(content) != prepared.raw_bytes:
                raise ObservationWriteError("Stored raw response bytes do not match.")
            rows = inserts + self.execute(prepared.verify_sql)
            for row in rows:
                if "OBSERVATION_ID" in row:
                    if row.get("RAW_CHUNK_COUNT") != len(chunks):
                        raise ObservationWriteError("Stored chunk manifest does not match.")
                    row["STORED_RESPONSE_HASH"] = "sha256:" + hashlib.sha256(content).hexdigest()
        else:
            rows = self.execute(prepared.insert_sql + "\n" + prepared.verify_sql)
        return self._receipt(observation, prepared, rows)

    def execute(self, sql: str) -> list[dict]:
        return self.executor.execute(sql)

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
