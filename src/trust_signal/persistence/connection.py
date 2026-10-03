"""Reusable, serialized application session with key-pair authentication."""

from __future__ import annotations

import argparse
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

from trust_signal.persistence.contracts import ObservationWriteError
from trust_signal.persistence.settings import SnowflakeSettings


class SnowflakeSession:
    """Share within one worker; serialize use and never blindly replay failed SQL."""

    def __init__(self, settings: SnowflakeSettings, *, connect=None):
        self.settings = settings
        self._connect = connect
        self._connection = None
        self._lock = RLock()
        self._closed = False

    def _get_connection(self):
        if self._closed:
            raise ObservationWriteError("Application session is closed.")
        if self._connection is None or self._connection.is_closed():
            options = self.settings.connection_options()
            if self._connect is None:
                from snowflake.connector import connect
                self._connect = connect
            self._connection = self._connect(**options)
        return self._connection

    def _discard(self):
        connection, self._connection = self._connection, None
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001 - preserve query error without leaking credentials
                logging.getLogger(__name__).warning("Snowflake session cleanup failed.")

    def execute(self, sql: str) -> list[dict]:
        from io import StringIO

        from snowflake.connector.util_text import split_statements

        with self._lock:
            try:
                connection = self._get_connection()
                rows = []
                # Snowflake's parser handles literals/comments; never split on semicolons.
                for statement, _ in split_statements(StringIO(sql)):
                    with connection.cursor() as cursor:
                        cursor.execute(statement)
                        if cursor.description:
                            names = [column[0] for column in cursor.description]
                            rows.extend(dict(zip(names, row, strict=True)) for row in cursor.fetchall())
                return rows
            except Exception:  # noqa: BLE001 - discard failures without exposing driver credentials
                self._discard()
                raise ObservationWriteError(
                    "Application query failed; the write outcome may be unknown. "
                    "Reconcile or replay the saved observation before retrying."
                ) from None

    def close(self):
        with self._lock:
            self._discard()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify key-pair connection and session reuse.")
    config_args = parser.add_mutually_exclusive_group()
    config_args.add_argument("--config", type=Path, help="Legacy connection TOML")
    config_args.add_argument("--env-file", type=Path, default=None, help="Private dotenv file")
    args = parser.parse_args()
    try:
        path = args.config or args.env_file or (Path(".env") if Path(".env").is_file() else None)
        settings = SnowflakeSettings.from_config(path) if path else SnowflakeSettings.from_env()
        with SnowflakeSession(settings) as session:
            sql = """SELECT CURRENT_SESSION() AS SESSION_ID, CURRENT_USER() AS USER_NAME,
CURRENT_ROLE() AS ACTIVE_ROLE, CURRENT_DATABASE() AS ACTIVE_DATABASE,
CURRENT_WAREHOUSE() AS ACTIVE_WAREHOUSE;"""
            first, second = session.execute(sql), session.execute(sql)
            if len(first) != 1 or len(second) != 1 or first != second:
                raise RuntimeError("Application session reuse verification failed.")
            expected = {"USER_NAME": settings.user, "ACTIVE_ROLE": settings.role,
                        "ACTIVE_DATABASE": settings.database,
                        "ACTIVE_WAREHOUSE": settings.warehouse}
            if any(first[0].get(key) != value for key, value in expected.items()):
                raise RuntimeError("Application context verification failed.")
            print(json.dumps({"status": "OK", "session_reused": True, **first[0]}, indent=2))
    except (ValueError, OSError, RuntimeError, ImportError, KeyError, TypeError):
        parser.exit(1, "Application connection failed. Check configuration, key permissions, "
                    "registered public key and service-role grants. No credentials were printed.\n")
    return 0


@contextmanager
def application_stores(config: Path, database: str | None = None):
    from trust_signal.persistence.snowflake import SnowflakeObservationStore
    from trust_signal.persistence.source_runs import SnowflakeSourceRunStore

    settings = SnowflakeSettings.from_config(config)
    if database is not None and settings.database != database:
        raise ValueError("Requested database differs from the application connection database.")
    database = settings.database
    with SnowflakeSession(settings) as session:
        yield (SnowflakeObservationStore(session, database),
               SnowflakeSourceRunStore(session, database))


if __name__ == "__main__":
    raise SystemExit(main())
