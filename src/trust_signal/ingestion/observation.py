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


def sql_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def prepare_observation(
    observation: SourceObservation, database: str = "TRUST_SIGNAL_DEV"
) -> PreparedObservation:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", database):
        raise ValueError("Database must be an uppercase unquoted Snowflake identifier.")
    if observation.raw_response_text is None:
        raise ValueError("The exact raw response is required; reserialized JSON is not accepted.")
    raw_bytes = observation.raw_response_text.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()
    if digest != observation.content_hash:
        raise ValueError("Raw response hash does not match the observation.")
    if observation.payload_format == "application/xml":
        ElementTree.fromstring(raw_bytes)
    elif json.loads(raw_bytes) != observation.raw_payload:
        raise ValueError("Raw response does not match the parsed observation.")

    # A fetched response has its own observation; replay retains that same ID.
    identity = json.dumps(
        [observation.source_id, observation.source_record_id,
         observation.observed_at.isoformat(), digest],
        separators=(",", ":"),
    )
    observation_id = f"observation_{uuid5(NAMESPACE_URL, identity).hex}"
    encoded = base64.b64encode(raw_bytes).decode("ascii")
    payload_encoded = base64.b64encode(json.dumps(observation.raw_payload).encode()).decode("ascii")
    payload_sql = (f"PARSE_JSON(BASE64_DECODE_STRING('{payload_encoded}'))"
                   if observation.payload_format == "application/xml" else "PARSE_JSON(payload_text)")
    table = f"{database}.TRUST_SIGNAL_RAW.SOURCE_OBSERVATIONS"
    entity_columns = ""
    if isinstance(observation.raw_payload.get("data"), dict):
        entity_columns = """RAW_PAYLOAD:data:attributes:entity:legalName:name::VARCHAR AS LEGAL_NAME,
    RAW_PAYLOAD:data:attributes:entity:status::VARCHAR AS ENTITY_STATUS,
    RAW_PAYLOAD:data:attributes:registration:status::VARCHAR AS REGISTRATION_STATUS,"""
    insert_sql = f"""INSERT INTO {table} (
    OBSERVATION_ID, SOURCE_ID, SOURCE_RECORD_ID, CANONICAL_URL,
    OBSERVED_AT, INGESTED_AT, CONTENT_HASH, CONNECTOR_VERSION,
    PAYLOAD_FORMAT, RAW_PAYLOAD, RAW_RESPONSE_TEXT
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
    payload_text
FROM (
    SELECT BASE64_DECODE_STRING('{encoded}') AS payload_text
)
WHERE 'sha256:' || SHA2(payload_text, 256) = {sql_literal(digest)}
  AND NOT EXISTS (
    SELECT 1 FROM {table}
    WHERE OBSERVATION_ID = {sql_literal(observation_id)}
);"""
    verify_sql = f"""SELECT
    OBSERVATION_ID, SOURCE_ID, SOURCE_RECORD_ID, CANONICAL_URL,
    CONNECTOR_VERSION, PAYLOAD_FORMAT, CONTENT_HASH,
    TO_JSON(RAW_PAYLOAD) AS PAYLOAD_JSON,
    'sha256:' || SHA2(RAW_RESPONSE_TEXT, 256) AS STORED_RESPONSE_HASH,
    {entity_columns}
    OBSERVED_AT, INGESTED_AT
FROM {table}
WHERE OBSERVATION_ID = {sql_literal(observation_id)};"""
    return PreparedObservation(observation_id, table, raw_bytes, insert_sql, verify_sql)
