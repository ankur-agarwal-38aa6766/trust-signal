import hashlib
import json
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from trust_signal.connectors.base import SourceObservation
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.snowflake_cli import (
    ObservationWriteError,
    SnowflakeCliObservationStore,
)


def test_xml_is_stored_with_exact_body_and_metadata_and_verified_hash():
    raw = '<CONSOLIDATED_LIST dateGenerated="2026-10-03" />'
    observation = SourceObservation(
        source_id="un", source_record_id="snapshot", canonical_url="https://example.org/list.xml",
        observed_at=datetime.now(UTC), connector_version="0.1.0", payload_format="application/xml",
        raw_payload={"root_tag": "CONSOLIDATED_LIST"}, raw_response_text=raw,
        content_hash="sha256:" + hashlib.sha256(raw.encode()).hexdigest())
    prepared = prepare_observation(observation)
    assert prepared.raw_bytes == raw.encode()
    assert "RAW_RESPONSE_TEXT" in prepared.insert_sql and "application/xml" in prepared.insert_sql
    row = {"OBSERVATION_ID": prepared.observation_id, "SOURCE_ID": "un",
           "SOURCE_RECORD_ID": "snapshot", "CANONICAL_URL": observation.canonical_url,
           "CONNECTOR_VERSION": "0.1.0", "PAYLOAD_FORMAT": "application/xml",
           "CONTENT_HASH": observation.content_hash, "STORED_RESPONSE_HASH": observation.content_hash,
           "PAYLOAD_JSON": json.dumps(observation.raw_payload)}
    store = SnowflakeCliObservationStore("dev")
    store.executor.execute = Mock(return_value=[{"number of rows inserted": 1}, row])
    assert store.store_observation(observation).verified_rows == 1
    row["STORED_RESPONSE_HASH"] = "corrupt"
    with pytest.raises(ObservationWriteError):
        store.store_observation(observation)
