"""Portable run lifecycle contract and Snowflake CLI implementation."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from trust_signal.ingestion.observation import sql_literal
from trust_signal.persistence.snowflake_cli import SnowflakeCliObservationStore


@dataclass(frozen=True)
class SourceRun:
    run_id: str
    source_id: str
    connector_version: str
    started_at: datetime

    @classmethod
    def create(cls, source_id: str, connector_version: str) -> SourceRun:
        return cls(f"run_{uuid4().hex}", source_id, connector_version, datetime.now(UTC))


class SourceRunStore(Protocol):
    def start(self, run: SourceRun, details: dict) -> None: ...

    def finish(
        self, run: SourceRun, status: str, seen: int, accepted: int,
        error_category: str | None, details: dict,
    ) -> None: ...


class SourceRunWriteError(RuntimeError):
    """Run history could not be verified; evidence may already be stored."""


def _details_sql(details: dict) -> str:
    encoded = base64.b64encode(json.dumps(details).encode()).decode("ascii")
    return f"PARSE_JSON(BASE64_DECODE_STRING('{encoded}'))"


class SnowflakeCliSourceRunStore:
    def __init__(self, connection: str, database: str = "TRUST_SIGNAL_DEV", *, executor=None):
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", database):
            raise ValueError("Database must be an uppercase unquoted Snowflake identifier.")
        self.table = f"{database}.TRUST_SIGNAL_OPS.SOURCE_RUNS"
        self.cli = SnowflakeCliObservationStore(connection, database, executor=executor)

    def _write(self, sql: str, run: SourceRun, expected: dict) -> None:
        verification = f"""SELECT SOURCE_RUN_ID, SOURCE_ID, CONNECTOR_VERSION,
RUN_STATUS, RECORDS_SEEN, RECORDS_ACCEPTED, ERROR_CATEGORY,
COMPLETED_AT IS NOT NULL AS IS_COMPLETE, TO_JSON(DETAILS) AS DETAILS_JSON
FROM {self.table} WHERE SOURCE_RUN_ID = {sql_literal(run.run_id)};"""
        try:
            rows = self.cli.execute(sql + "\n" + verification)
            stored = [row for row in rows if "SOURCE_RUN_ID" in row]
            expected = {**expected, "SOURCE_RUN_ID": run.run_id, "SOURCE_ID": run.source_id,
                        "CONNECTOR_VERSION": run.connector_version}
            details = expected.pop("DETAILS")
            if len(stored) != 1 or any(stored[0].get(k) != v for k, v in expected.items()):
                raise ValueError("Run metadata mismatch")
            if json.loads(stored[0]["DETAILS_JSON"]) != details:
                raise ValueError("Run details mismatch")
        except Exception as exc:
            raise SourceRunWriteError(
                f"Source run {run.run_id} could not be verified; reconcile its history in Snowflake."
            ) from exc

    def start(self, run: SourceRun, details: dict) -> None:
        sql = f"""INSERT INTO {self.table}
(SOURCE_RUN_ID, SOURCE_ID, STARTED_AT, RUN_STATUS, RECORDS_SEEN,
 RECORDS_ACCEPTED, CONNECTOR_VERSION, DETAILS)
SELECT {sql_literal(run.run_id)}, {sql_literal(run.source_id)},
TO_TIMESTAMP_TZ({sql_literal(run.started_at.isoformat())}), 'running', 0, 0,
{sql_literal(run.connector_version)}, {_details_sql(details)}
WHERE NOT EXISTS (SELECT 1 FROM {self.table}
                  WHERE SOURCE_RUN_ID = {sql_literal(run.run_id)});"""
        self._write(sql, run, {"RUN_STATUS": "running", "RECORDS_SEEN": 0,
                              "RECORDS_ACCEPTED": 0, "ERROR_CATEGORY": None,
                              "IS_COMPLETE": False, "DETAILS": details})

    def finish(self, run, status, seen, accepted, error_category, details) -> None:
        if (status not in {"succeeded", "failed"} or type(seen) is not int
                or type(accepted) is not int or not 0 <= accepted <= seen):
            raise ValueError("Invalid terminal run status or record counts.")
        error = "NULL" if error_category is None else sql_literal(error_category)
        sql = f"""UPDATE {self.table} SET COMPLETED_AT = CURRENT_TIMESTAMP(),
RUN_STATUS = {sql_literal(status)}, RECORDS_SEEN = {seen}, RECORDS_ACCEPTED = {accepted},
ERROR_CATEGORY = {error}, DETAILS = {_details_sql(details)}
WHERE SOURCE_RUN_ID = {sql_literal(run.run_id)} AND RUN_STATUS = 'running';"""
        self._write(sql, run, {"RUN_STATUS": status, "RECORDS_SEEN": seen,
                              "RECORDS_ACCEPTED": accepted, "ERROR_CATEGORY": error_category,
                              "IS_COMPLETE": True, "DETAILS": details})
