"""Optional CLI SQL transport and backwards-compatible observation adapter."""

from __future__ import annotations

import json
import subprocess

from trust_signal.persistence.contracts import ObservationWriteError, SqlExecutor
from trust_signal.persistence.snowflake import SnowflakeObservationStore


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


class SnowflakeCliExecutor:
    """Execute SQL with a named CLI connection; no repository-specific behavior."""

    def __init__(self, connection: str, database: str = "TRUST_SIGNAL_DEV", timeout: float = 180):
        if not connection or connection.startswith("-"):
            raise ValueError("A named Snowflake connection is required.")
        self.connection = connection
        self.database = database
        self.timeout = timeout

    def execute(self, sql: str) -> list[dict]:
        """Execute SQL without exposing CLI authentication output in errors."""
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


class SnowflakeCliObservationStore(SnowflakeObservationStore):
    """Compatibility adapter; new application code uses SnowflakeObservationStore."""

    def __init__(self, connection: str, database: str = "TRUST_SIGNAL_DEV", timeout: float = 180,
                 *, executor: SqlExecutor | None = None):
        super().__init__(executor if executor is not None else
                         SnowflakeCliExecutor(connection, database, timeout), database)
