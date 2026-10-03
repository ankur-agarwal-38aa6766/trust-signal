"""Prepare immutable source observations for export or Snowflake loading."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree

from trust_signal.connectors.base import SourceObservation


@dataclass(frozen=True)
class PreparedObservation:
    observation_id: str
    table: str
    raw_bytes: bytes
    insert_sql: str
    verify_sql: str
    chunk_sql: tuple[str, ...] = ()
    verify_chunks_sql: str | None = None


def sql_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def prepare_observation(
    observation: SourceObservation, database: str = "TRUST_SIGNAL_DEV"
) -> PreparedObservation:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", database):
        raise ValueError("Database must be an uppercase unquoted Snowflake identifier.")
    if observation.raw_response_text is None and observation.raw_response_bytes is None:
        raise ValueError("The exact raw response is required; reserialized JSON is not accepted.")
    raw_bytes = (observation.raw_response_bytes if observation.raw_response_bytes is not None
                 else observation.raw_response_text.encode("utf-8"))
    if not raw_bytes:
        raise ValueError("An empty raw response cannot be persisted as evidence.")
    if observation.raw_response_text is not None and observation.raw_response_text.encode("utf-8") != raw_bytes:
        raise ValueError("Text and byte representations do not match.")
    digest = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
    if digest != observation.content_hash:
        raise ValueError("Raw response hash does not match the observation.")
    if observation.payload_format == "application/xml":
        ElementTree.fromstring(raw_bytes)
    elif observation.payload_format in {"application/json", "application/vnd.api+json"} and json.loads(raw_bytes) != observation.raw_payload:
        raise ValueError("Raw response does not match the parsed observation.")

    # A fetched response has its own observation; replay retains that same ID.
    identity = json.dumps(
        [observation.source_id, observation.source_record_id,
         observation.observed_at.isoformat(), digest],
        separators=(",", ":"),
    )
    observation_id = f"observation_{uuid5(NAMESPACE_URL, identity).hex}"
    chunked = len(raw_bytes) > 4 * 1024 * 1024 or observation.raw_response_text is None
    encoded = base64.b64encode(raw_bytes if not chunked else b"").decode("ascii")
    payload_encoded = base64.b64encode(json.dumps(observation.raw_payload).encode()).decode("ascii")
    payload_sql = (f"PARSE_JSON(BASE64_DECODE_STRING('{payload_encoded}'))"
                   if observation.payload_format not in {"application/json", "application/vnd.api+json"} or chunked else "PARSE_JSON(payload_text)")
    table = f"{database}.TRUST_SIGNAL_RAW.SOURCE_OBSERVATIONS"
    chunks = []
    chunk_table = f"{database}.TRUST_SIGNAL_RAW.SOURCE_RESPONSE_CHUNKS"
    if chunked:
        for index, offset in enumerate(range(0, len(raw_bytes), 512 * 1024)):
            piece = raw_bytes[offset:offset + 512 * 1024]
            encoded_piece = base64.b64encode(piece).decode("ascii")
            piece_hash = hashlib.sha256(piece).hexdigest()
            chunks.append(f"""INSERT INTO {chunk_table}
(OBSERVATION_ID, CHUNK_INDEX, RAW_BYTES_BASE64, CHUNK_HASH)
SELECT {sql_literal(observation_id)}, {index}, '{encoded_piece}', '{piece_hash}'
WHERE NOT EXISTS (SELECT 1 FROM {chunk_table}
WHERE OBSERVATION_ID = {sql_literal(observation_id)} AND CHUNK_INDEX = {index});""")
    hash_condition = "TRUE" if chunked else f"'sha256:' || SHA2(payload_text, 256) = {sql_literal(digest)}"
    raw_sql = "NULL" if chunked else "payload_text"
    entity_columns = ""
    if isinstance(observation.raw_payload.get("data"), dict):
        entity_columns = """RAW_PAYLOAD:data:attributes:entity:legalName:name::VARCHAR AS LEGAL_NAME,
    RAW_PAYLOAD:data:attributes:entity:status::VARCHAR AS ENTITY_STATUS,
    RAW_PAYLOAD:data:attributes:registration:status::VARCHAR AS REGISTRATION_STATUS,"""
    insert_sql = f"""INSERT INTO {table} (
    OBSERVATION_ID, SOURCE_ID, SOURCE_RECORD_ID, CANONICAL_URL,
    OBSERVED_AT, INGESTED_AT, CONTENT_HASH, CONNECTOR_VERSION,
    PAYLOAD_FORMAT, RAW_PAYLOAD, RAW_RESPONSE_TEXT, RAW_CHUNK_COUNT
)
SELECT
    {sql_literal(observation_id)},
    {sql_literal(observation.source_id)},
    {sql_literal(observation.source_record_id)},
    {sql_literal(observation.canonical_url)},
    TO_TIMESTAMP_TZ({sql_literal(observation.observed_at.isoformat())}),
    CURRENT_TIMESTAMP(),
    {sql_literal(digest)},
    {sql_literal(observation.connector_version)},
    {sql_literal(observation.payload_format)},
    {payload_sql},
    {raw_sql},
    {len(chunks)}
FROM (
    SELECT BASE64_DECODE_STRING('{encoded}') AS payload_text
)
WHERE {hash_condition}
  AND NOT EXISTS (
    SELECT 1 FROM {table}
    WHERE OBSERVATION_ID = {sql_literal(observation_id)}
);"""
    verify_sql = f"""SELECT
    OBSERVATION_ID, SOURCE_ID, SOURCE_RECORD_ID, CANONICAL_URL,
    CONNECTOR_VERSION, PAYLOAD_FORMAT, CONTENT_HASH,
    RAW_CHUNK_COUNT,
    TO_JSON(RAW_PAYLOAD) AS PAYLOAD_JSON,
    'sha256:' || SHA2(RAW_RESPONSE_TEXT, 256) AS STORED_RESPONSE_HASH,
    {entity_columns}
    OBSERVED_AT, INGESTED_AT
FROM {table}
WHERE OBSERVATION_ID = {sql_literal(observation_id)};"""
    chunk_verify = (f"SELECT CHUNK_INDEX, RAW_BYTES_BASE64, CHUNK_HASH FROM {chunk_table} "
                    f"WHERE OBSERVATION_ID = {sql_literal(observation_id)} ORDER BY CHUNK_INDEX;") if chunked else None
    return PreparedObservation(observation_id, table, raw_bytes, insert_sql, verify_sql, tuple(chunks), chunk_verify)
