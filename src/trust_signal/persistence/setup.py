"""Generate administrator-reviewed Snowflake setup SQL; never execute on startup."""

from __future__ import annotations

import argparse
import base64
import json
from functools import partial
from pathlib import Path

from trust_signal.persistence.keys import validate_keypair
from trust_signal.persistence.migrations import migration_paths
from trust_signal.persistence.settings import SnowflakeSettings
from trust_signal.persistence.sql_resources import render_sql as render_template


def ingestion_identity_sql(
    settings: SnowflakeSettings, public_key_file: Path, resources: Path | None = None
) -> str:
    render_sql = partial(render_template, resources=resources)
    from cryptography.hazmat.primitives import serialization

    settings.validate_context()
    if settings.role in {"ACCOUNTADMIN", "SECURITYADMIN", "USERADMIN", "SYSADMIN", "PUBLIC"}:
        raise ValueError(
            "Setup requires a dedicated runtime role, not a built-in administrative role."
        )
    key = validate_keypair(settings, public_key_file)
    public_key = base64.b64encode(
        key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    ).decode("ascii")
    database, warehouse, role, user = (
        settings.database,
        settings.warehouse,
        settings.role,
        settings.user,
    )
    return render_sql(
        "security/INGESTION_IDENTITY.sql.template",
        role=role,
        user=user,
        public_key=public_key,
        warehouse=warehouse,
        database=database,
    )


def setup_sql(settings: SnowflakeSettings, public_key_file: Path, migrations: Path) -> str:
    render_sql = render_template
    grants = ingestion_identity_sql(settings, public_key_file)
    paths = migration_paths(migrations)
    database, warehouse = settings.database, settings.warehouse
    header = render_sql(
        "bootstrap/INGESTION_PLATFORM.sql.template",
        parameter_0=settings.account,
        database=database,
        warehouse=warehouse,
    )
    ddl = "\n".join(
        f"-- Migration: {path.name}\n{path.read_text(encoding='utf-8')}" for path in paths
    )
    return header + ddl + grants


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--public-key-file", type=Path, required=True)
    parser.add_argument("--migrations-dir", type=Path, default=Path("snowflake/migrations"))
    parser.add_argument("--output", type=Path, default=Path("snowflake/build/setup.sql"))
    args = parser.parse_args()
    try:
        if args.output.resolve() in {args.env_file.resolve(), args.public_key_file.resolve()}:
            raise ValueError("Setup output must not overwrite configuration or keys.")
        settings = SnowflakeSettings.from_env(args.env_file)
        protected = {
            settings.private_key_file.resolve(),
            settings.private_key_passphrase_file.resolve(),
        }
        protected.update(path.resolve() for path in args.migrations_dir.glob("*.sql"))
        if args.output.resolve() in protected:
            raise ValueError("Setup output must not overwrite private credentials.")
        sql = setup_sql(settings, args.public_key_file, args.migrations_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(sql, encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "plan_only",
                    "account": settings.account,
                    "database": settings.database,
                    "sql_file": str(args.output.resolve()),
                    "executed": False,
                },
                indent=2,
            )
        )
    except (ValueError, OSError, ImportError, TypeError):
        parser.exit(1, "Setup plan failed. Check configuration, public key and migrations.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
