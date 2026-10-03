"""Single-writer CORE persistence for replayable identity/evidence snapshots."""

import base64
import hashlib
import json
import re
from typing import Protocol

from trust_signal.ingestion.observation import sql_literal
from trust_signal.persistence.snowflake_cli import (
    ObservationWriteError,
    SnowflakeCliObservationStore,
)
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.service import ResearchIdentity


class IdentityResearchStore(Protocol):
    def store(self, tenant_id: str, case_id: str, input_version: int,
              research: ResearchIdentity) -> str: ...


class SnowflakeCliIdentityResearchStore:
    def __init__(self, connection: str, database: str = "TRUST_SIGNAL_DEV"):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", database):
            raise ValueError("Invalid Snowflake database identifier.")
        self.client = SnowflakeCliObservationStore(connection, database)
        self.database = database

    def store(self, tenant_id: str, case_id: str, input_version: int,
              research: ResearchIdentity) -> str:
        if not tenant_id.strip() or not case_id.strip() or input_version < 1:
            raise ValueError("Tenant, case and positive input version are required.")
        payload = research.model_dump(mode="json")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(serialized.encode()).hexdigest()
        decision_id = stable_id("identity", tenant_id, case_id, str(input_version), digest)
        table = f"{self.database}.TRUST_SIGNAL_CORE.IDENTITY_DECISIONS"
        encoded = base64.b64encode(serialized.encode()).decode("ascii")
        identity = sql_literal(decision_id)
        sql = f"""INSERT INTO {table} (
    IDENTITY_DECISION_ID, TENANT_ID, CASE_ID, INPUT_VERSION,
    POLICY_VERSION, RESOLUTION_STATUS, RESEARCH, CREATED_AT
)
SELECT {identity}, {sql_literal(tenant_id)}, {sql_literal(case_id)}, {input_version},
    {sql_literal(research.resolution.policy_version)},
    {sql_literal(research.resolution.status.value)},
    PARSE_JSON(BASE64_DECODE_STRING('{encoded}')), CURRENT_TIMESTAMP()
WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE IDENTITY_DECISION_ID = {identity});
SELECT IDENTITY_DECISION_ID, TENANT_ID, CASE_ID, INPUT_VERSION, TO_JSON(RESEARCH) AS RESEARCH_JSON
FROM {table} WHERE IDENTITY_DECISION_ID = {identity};"""
        rows = [r for r in self.client.execute(sql) if "IDENTITY_DECISION_ID" in r]
        if len(rows) != 1:
            raise ObservationWriteError("Expected one stored identity decision.")
        row = rows[0]
        try:
            stored_payload = json.loads(row["RESEARCH_JSON"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ObservationWriteError("Stored identity payload could not be verified.") from exc
        if (row.get("IDENTITY_DECISION_ID") != decision_id or row.get("TENANT_ID") != tenant_id
                or row.get("CASE_ID") != case_id or row.get("INPUT_VERSION") != input_version
                or stored_payload != payload):
            raise ObservationWriteError("Stored identity decision does not match the research.")
        return decision_id
