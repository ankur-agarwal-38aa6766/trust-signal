"""Reusable, serialized application session with key-pair authentication."""

from __future__ import annotations

import argparse
import json
import logging
import re
import stat
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from trust_signal.config import environment_config
from trust_signal.persistence.snowflake_cli import ObservationWriteError


@dataclass(frozen=True)
class SnowflakeSettings:
    account: str
    user: str
    role: str
    warehouse: str
    database: str
    schema: str
    private_key_file: Path = field(repr=False)
    private_key_passphrase_file: Path = field(repr=False)

    @classmethod
    def from_env(cls, path: Path | None = None) -> SnowflakeSettings:
        config = environment_config(path)
        names = ("ACCOUNT", "USER", "ROLE", "WAREHOUSE", "DATABASE", "SCHEMA",
                 "PRIVATE_KEY_FILE", "PRIVATE_KEY_PASSPHRASE_FILE")
        values = [config.get(f"TRUST_SIGNAL_SNOWFLAKE_{name}", "").strip() for name in names]
        if not all(values):
            raise ValueError("Set all TRUST_SIGNAL_SNOWFLAKE_* application connection variables.")
        base = path.resolve().parent if path else Path.cwd()
        paths = [Path(value).expanduser() for value in values[6:]]
        return cls(*values[:6], *(item if item.is_absolute() else base / item for item in paths))

    @classmethod
    def from_config(cls, path: Path) -> SnowflakeSettings:
        return cls.from_file(path) if path.suffix == ".toml" else cls.from_env(path)

    @classmethod
    def from_file(cls, path: Path) -> SnowflakeSettings:
        values = tomllib.loads(path.read_text(encoding="utf-8"))
        for key in ("private_key_file", "private_key_passphrase_file"):
            location = Path(values[key]).expanduser()
            values[key] = location if location.is_absolute() else path.resolve().parent / location
        return cls(**values)

    def validate_context(self) -> None:
        for value in (self.user, self.role, self.warehouse, self.database, self.schema):
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
                raise ValueError("Application context must use uppercase Snowflake identifiers.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.account):
            raise ValueError("Use an organization-account identifier, not a URL.")

    def connection_options(self) -> dict:
        self.validate_context()
        for path in (self.private_key_file, self.private_key_passphrase_file):
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise ValueError("Key and passphrase files must be private regular files (0600).")
        passphrase = self.private_key_passphrase_file.read_text(encoding="utf-8").strip()
        if not passphrase:
            raise ValueError("Private-key passphrase file is empty.")
        return {"account": self.account, "user": self.user, "role": self.role,
                "warehouse": self.warehouse, "database": self.database, "schema": self.schema,
                "authenticator": "SNOWFLAKE_JWT", "private_key_file": str(self.private_key_file),
                "private_key_file_pwd": passphrase, "autocommit": True, "login_timeout": 30,
                "network_timeout": 60, "client_session_keep_alive": False,
                "session_parameters": {"QUERY_TAG": "trust_signal_application",
                                       "STATEMENT_TIMEOUT_IN_SECONDS": 120}}


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
    from trust_signal.persistence.snowflake_cli import SnowflakeCliObservationStore
    from trust_signal.persistence.source_runs import SnowflakeCliSourceRunStore

    settings = SnowflakeSettings.from_config(config)
    if database is not None and settings.database != database:
        raise ValueError("Requested database differs from the application connection database.")
    database = settings.database
    with SnowflakeSession(settings) as session:
        yield (SnowflakeCliObservationStore("application", database, executor=session),
               SnowflakeCliSourceRunStore("application", database, executor=session))


if __name__ == "__main__":
    raise SystemExit(main())
