import base64
import hashlib
import json
from unittest.mock import Mock

import pytest
from test_raw_export import lookup_for_test

from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.contracts import ObservationWriteError
from trust_signal.persistence.snowflake import SnowflakeObservationStore


@pytest.mark.parametrize("failure", [None, "missing", "hash", "order", "body", "manifest"])
def test_binary_chunk_readback_is_required_before_release(failure):
    lookup, _ = lookup_for_test()
    raw = b"PK binary workbook test"
    observation = lookup.observation.model_copy(update={
        "raw_response_text": None, "raw_response_bytes": raw,
        "payload_format": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "raw_payload": {"record_count": 1},
        "content_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
    })
    prepared = prepare_observation(observation)
    chunk = {"CHUNK_INDEX": 0, "RAW_BYTES_BASE64": base64.b64encode(raw).decode(),
             "CHUNK_HASH": hashlib.sha256(raw).hexdigest()}
    row = {"OBSERVATION_ID": prepared.observation_id,
           "SOURCE_ID": observation.source_id, "SOURCE_RECORD_ID": observation.source_record_id,
           "CANONICAL_URL": observation.canonical_url, "CONNECTOR_VERSION": observation.connector_version,
           "PAYLOAD_FORMAT": observation.payload_format, "CONTENT_HASH": observation.content_hash,
           "PAYLOAD_JSON": json.dumps(observation.raw_payload), "RAW_CHUNK_COUNT": 1}
    if failure == "hash":
        chunk["CHUNK_HASH"] = "wrong"
    if failure == "order":
        chunk["CHUNK_INDEX"] = 1
    if failure == "body":
        chunk["RAW_BYTES_BASE64"] = base64.b64encode(b"different").decode()
        chunk["CHUNK_HASH"] = hashlib.sha256(b"different").hexdigest()
    if failure == "manifest":
        row["RAW_CHUNK_COUNT"] = 0
    executor = Mock()
    executor.execute.side_effect = [[{"number of rows inserted": 1}], [],
                                    [] if failure == "missing" else [chunk], [row]]
    store = SnowflakeObservationStore(executor)
    if failure:
        with pytest.raises(ObservationWriteError):
            store.store_observation(observation)
    else:
        assert store.store_observation(observation).verified_rows == 1
        assert executor.execute.call_count == 4
