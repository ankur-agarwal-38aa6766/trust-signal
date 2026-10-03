"""Validated Snowflake account configuration; no network or session side effects."""

from __future__ import annotations

import re
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from trust_signal.config import environment_config


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
        passphrase = self.key_passphrase()
        return {"account": self.account, "user": self.user, "role": self.role,
                "warehouse": self.warehouse, "database": self.database, "schema": self.schema,
                "authenticator": "SNOWFLAKE_JWT", "private_key_file": str(self.private_key_file),
                "private_key_file_pwd": passphrase, "autocommit": True, "login_timeout": 30,
                "network_timeout": 60, "client_session_keep_alive": False,
                "session_parameters": {"QUERY_TAG": "trust_signal_application",
                                       "STATEMENT_TIMEOUT_IN_SECONDS": 120}}

    def key_passphrase(self) -> str:
        for path in (self.private_key_file, self.private_key_passphrase_file):
            info = path.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise ValueError("Key and passphrase files must be private regular files (0600).")
        passphrase = self.private_key_passphrase_file.read_text(encoding="utf-8").strip()
        if not passphrase:
            raise ValueError("Private-key passphrase file is empty.")
        return passphrase
