"""Generate administrator-reviewed Snowflake setup SQL; never execute on startup."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from trust_signal.persistence.keys import validate_keypair
from trust_signal.persistence.settings import SnowflakeSettings


def setup_sql(settings: SnowflakeSettings, public_key_file: Path, migrations: Path) -> str:
    from cryptography.hazmat.primitives import serialization

    settings.validate_context()
    if settings.role in {"ACCOUNTADMIN", "SECURITYADMIN", "USERADMIN", "SYSADMIN", "PUBLIC"}:
        raise ValueError("Setup requires a dedicated runtime role, not a built-in administrative role.")
    key = validate_keypair(settings, public_key_file)
    public_key = base64.b64encode(key.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo,
    )).decode("ascii")
    migration_paths = sorted(migrations.glob("V[0-9]*__*.sql"))
    if not migration_paths or migration_paths[0].name != "V001__foundation.sql":
        raise ValueError("Reviewed migrations must include the foundation migration.")
    database, warehouse, role, user = (
        settings.database, settings.warehouse, settings.role, settings.user,
    )
    header = f"""-- REVIEW BEFORE EXECUTION. Target account: {settings.account}
-- Use an authorized administrator connection to this account only.
-- Existing user keys are NOT overwritten. Verify their key and role before reuse.
-- Existing warehouse settings are NOT changed. DDL may partially commit on failure.
CREATE DATABASE IF NOT EXISTS {database};
CREATE WAREHOUSE IF NOT EXISTS {warehouse} WAREHOUSE_SIZE = XSMALL
    AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
CREATE ROLE IF NOT EXISTS {role};
USE DATABASE {database};
"""
    ddl = "\n".join(f"-- Migration: {path.name}\n{path.read_text(encoding='utf-8')}"
                    for path in migration_paths)
    grants = f"""
CREATE USER IF NOT EXISTS {user} TYPE = SERVICE RSA_PUBLIC_KEY = '{public_key}'
    DEFAULT_ROLE = {role} DEFAULT_WAREHOUSE = {warehouse};
GRANT USAGE ON DATABASE {database} TO ROLE {role};
GRANT USAGE ON WAREHOUSE {warehouse} TO ROLE {role};
GRANT USAGE ON SCHEMA {database}.TRUST_SIGNAL_RAW TO ROLE {role};
GRANT USAGE ON SCHEMA {database}.TRUST_SIGNAL_OPS TO ROLE {role};
GRANT SELECT, INSERT ON TABLE {database}.TRUST_SIGNAL_RAW.SOURCE_OBSERVATIONS TO ROLE {role};
GRANT SELECT, INSERT, UPDATE ON TABLE {database}.TRUST_SIGNAL_OPS.SOURCE_RUNS TO ROLE {role};
GRANT ROLE {role} TO USER {user};
-- No CORE, UI, Cortex or account-admin privileges are granted to the ingestion user.
"""
    return header + ddl + grants


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--public-key-file", type=Path, required=True)
    parser.add_argument("--migrations-dir", type=Path, default=Path("snowflake/migrations"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.resolve() in {args.env_file.resolve(), args.public_key_file.resolve()}:
            raise ValueError("Setup output must not overwrite configuration or keys.")
        settings = SnowflakeSettings.from_env(args.env_file)
        protected = {settings.private_key_file.resolve(), settings.private_key_passphrase_file.resolve()}
        protected.update(path.resolve() for path in args.migrations_dir.glob("*.sql"))
        if args.output.resolve() in protected:
            raise ValueError("Setup output must not overwrite private credentials.")
        sql = setup_sql(settings, args.public_key_file, args.migrations_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(sql, encoding="utf-8")
        print(json.dumps({"status": "plan_only", "account": settings.account,
                          "database": settings.database, "sql_file": str(args.output.resolve()),
                          "executed": False}, indent=2))
    except (ValueError, OSError, ImportError, TypeError):
        parser.exit(1, "Setup plan failed. Check configuration, public key and migrations.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
