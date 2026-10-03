"""Generate a complete, reviewable Snowflake onboarding bundle; no cloud calls."""

import argparse
import hashlib
import json
import shlex
from functools import partial
from pathlib import Path

from trust_signal.orchestration.deployment import build, identifier
from trust_signal.persistence.migrations import migration_paths, tracked_migration
from trust_signal.persistence.sql_resources import read_resource
from trust_signal.persistence.sql_resources import render_sql as render_template


def initialize(
    output: Path,
    source: Path,
    snowflake: Path,
    database: str,
    warehouse: str,
    role: str,
    admin_role: str,
    operator_user: str | None = None,
    external_access: bool = True,
    ingestion_env_file: Path | None = None,
    public_key_file: Path | None = None,
) -> dict:
    render_sql = partial(render_template, resources=snowflake)
    for value in (database, warehouse, role, admin_role):
        identifier(value)
    if role in {"ACCOUNTADMIN", "SECURITYADMIN", "USERADMIN", "SYSADMIN", "PUBLIC"}:
        raise ValueError("Use a dedicated workflow role.")
    if operator_user:
        identifier(operator_user)
    if bool(ingestion_env_file) != bool(public_key_file):
        raise ValueError("Ingestion configuration and public key must be supplied together.")
    ingestion_sql = None
    if ingestion_env_file:
        from trust_signal.persistence.settings import SnowflakeSettings
        from trust_signal.persistence.setup import ingestion_identity_sql

        settings = SnowflakeSettings.from_env(ingestion_env_file)
        if (settings.database, settings.warehouse) != (
            database,
            warehouse,
        ) or settings.role == role:
            raise ValueError(
                "Ingestion target must match; ingestion and workflow roles must differ."
            )
        ingestion_sql = ingestion_identity_sql(settings, public_key_file, resources=snowflake)
    # A fresh directory prevents mixed artifacts and accidental release overwrites.
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("Use a fresh initialization directory.")
    paths = migration_paths(snowflake / "migrations")
    history = (snowflake / "bootstrap" / "MIGRATION_HISTORY.sql").read_text()
    context = render_sql(
        "bootstrap/ADMIN_CONTEXT.sql.template", admin_role=admin_role, database=database
    )
    files = {
        "00_platform.sql": render_sql(
            "bootstrap/PLATFORM.sql.template",
            admin_role=admin_role,
            database=database,
            warehouse=warehouse,
            history=history,
        )
    }
    migrations = []
    for path in paths:
        sql, checksum = tracked_migration(path, resources=snowflake)
        filename = f"migrations/{path.name}"
        files[filename] = (
            context
            + render_sql("bootstrap/WAREHOUSE_CONTEXT.sql.template", warehouse=warehouse)
            + sql
        )
        migrations.append(
            {
                "version": int(path.name.split("__")[0][1:]),
                "filename": path.name,
                "sha256": checksum,
            }
        )
    eai = f"{role}_GLEIF_EAI"
    identifier(eai)
    if external_access:
        files["10_external_access.sql"] = context + render_sql(
            "integrations/GLEIF.sql.template", eai=eai, database=database
        )
    workflow = build(
        source,
        output / "workflow",
        database,
        warehouse,
        role,
        eai,
        external_access=external_access,
        resources=snowflake,
    )
    grants = (output / "workflow" / "grants.sql").read_text()
    if operator_user:
        grants += render_sql(
            "security/OPERATOR_GRANT.sql.template", role=role, operator_user=operator_user
        )
    files["20_permissions.sql"] = context + grants
    files["21_quiesce.sql"] = render_sql(
        "tasks/QUIESCE.sql.template", admin_role=admin_role, database=database, warehouse=warehouse
    )
    files["30_verify.sql"] = context + render_sql(
        "verification/INVENTORY.sql.template", warehouse=warehouse, database=database
    )
    order = ["00_platform.sql", "21_quiesce.sql", *[f"migrations/{path.name}" for path in paths]]
    if ingestion_sql:
        files["09_ingestion_identity.sql"] = context + ingestion_sql
        order.append("09_ingestion_identity.sql")
    if external_access:
        order.append("10_external_access.sql")
    order += [
        "20_permissions.sql",
        "21_quiesce.sql",
        "workflow/preflight.sql",
        "workflow/upload.sql",
        "workflow/procedures.sql",
        "workflow/tasks.sql",
        "30_verify.sql",
    ]
    # The script applies one file at a time, stopping on the first error; activation is excluded.
    script = read_resource("setup/APPLY.sh.template", snowflake)
    for filename in order:
        script += (
            f'snow sql --connection "$connection" --role {admin_role} '
            f"--filename {shlex.quote(filename)}\n"
        )
    files["apply.sh"] = script
    for filename, content in files.items():
        target = output / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    manifest = {
        "status": "plan_only",
        "executed": False,
        "database": database,
        "warehouse": warehouse,
        "workflow_role": role,
        "admin_role": admin_role,
        "operator_user": operator_user,
        "external_access": external_access,
        "ingestion_identity_included": bool(ingestion_sql),
        "tasks_enabled": False,
        "migration_history": migrations,
        "execution_order": order,
        "workflow": workflow,
    }
    manifest["artifact_checksums"] = {
        path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("snowflake/build/installation"))
    parser.add_argument("--database", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--workflow-role", default="TRUST_SIGNAL_ORCHESTRATOR")
    parser.add_argument("--admin-role", default="ACCOUNTADMIN")
    parser.add_argument("--operator-user")
    parser.add_argument("--ingestion-env-file", type=Path)
    parser.add_argument("--public-key-file", type=Path)
    parser.add_argument("--source-dir", type=Path, default=Path("src"))
    parser.add_argument("--snowflake-dir", type=Path, default=Path("snowflake"))
    parser.add_argument("--without-external-access", action="store_true")
    args = parser.parse_args()
    try:
        manifest = initialize(
            args.output_dir,
            args.source_dir,
            args.snowflake_dir,
            args.database,
            args.warehouse,
            args.workflow_role,
            args.admin_role,
            args.operator_user,
            not args.without_external_access,
            args.ingestion_env_file,
            args.public_key_file,
        )
        print(
            json.dumps(
                {
                    "status": manifest["status"],
                    "executed": False,
                    "output_dir": str(args.output_dir.resolve()),
                    "migration_count": len(manifest["migration_history"]),
                    "external_access": manifest["external_access"],
                },
                indent=2,
            )
        )
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f"Initialization plan failed: {type(exc).__name__}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
