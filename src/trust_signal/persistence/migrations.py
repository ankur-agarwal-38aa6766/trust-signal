"""Reviewed SQL migrations shared by ingestion setup and full initialization."""

import hashlib
import re
from io import StringIO
from pathlib import Path

from trust_signal.persistence.sql_resources import render_sql


def migration_paths(directory: Path) -> list[Path]:
    paths = list(directory.glob("V*__*.sql"))
    versions = {}
    for path in paths:
        match = re.fullmatch(r"V([0-9]+)__[a-z0-9_]+\.sql", path.name)
        if not match or path.is_symlink():
            raise ValueError("Invalid migration filename or symbolic link.")
        version = int(match[1])
        if version in versions:
            raise ValueError("Duplicate migration version.")
        versions[version] = path
    if sorted(versions) != list(range(1, len(versions) + 1)) or not versions:
        raise ValueError("Migrations must have consecutive versions starting at V001.")
    if versions[1].name != "V001__foundation.sql":
        raise ValueError("Reviewed migrations must include the foundation migration.")
    return [versions[version] for version in sorted(versions)]


def sql_literal(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def tracked_migration(path: Path, resources: Path | None = None) -> tuple[str, str]:
    from snowflake.connector.util_text import split_statements

    content = path.read_text(encoding="utf-8")
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    version = int(path.name.split("__", 1)[0][1:])
    statements = [
        sql
        for sql, _ in split_statements(StringIO(content))
        if any(not line.strip().startswith("--") and line.strip() for line in sql.splitlines())
    ]
    if not statements:
        raise ValueError("Empty migration.")
    body = render_sql(
        "bootstrap/APPLY_MIGRATION.sql.template",
        resources=resources,
        version=version,
        checksum=checksum,
        filename=path.name,
        statements="\n".join(
            f"        EXECUTE IMMEDIATE {sql_literal(sql)};" for sql in statements
        ),
    )
    return f"-- Migration: {path.name}\nEXECUTE IMMEDIATE {sql_literal(body)};\n", checksum
