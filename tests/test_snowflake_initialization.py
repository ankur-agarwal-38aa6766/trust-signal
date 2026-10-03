import hashlib
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest
from snowflake.connector.util_text import split_statements

from trust_signal.persistence.initialize import initialize
from trust_signal.persistence.migrations import migration_paths, tracked_migration


def build_plan(tmp_path, **kwargs):
    return initialize(tmp_path / "init", Path("src"), Path("snowflake"),
                      "NEW_DB", "NEW_WH", "NEW_WORKFLOW", "ACCOUNTADMIN", **kwargs)


def test_complete_plan_targets_new_account_and_never_activates_tasks(tmp_path):
    manifest = build_plan(tmp_path, operator_user="NEW_ADMIN", external_access=False)
    output = tmp_path / "init"
    assert manifest["executed"] is False
    assert not manifest["tasks_enabled"]
    assert len(manifest["migration_history"]) == 7
    order = manifest["execution_order"]
    assert order.index("21_quiesce.sql") < order.index("migrations/V001__foundation.sql")
    assert order.index("20_permissions.sql") < order.index("workflow/upload.sql")
    assert order.index("workflow/upload.sql") < order.index("workflow/procedures.sql")
    assert order.index("workflow/procedures.sql") < order.index("workflow/tasks.sql")
    assert "workflow/enable_children.sql" not in order
    assert "workflow/start_schedule.sql" not in order
    assert not (output / "10_external_access.sql").exists()
    assert "GRANT ROLE NEW_WORKFLOW TO USER NEW_ADMIN" in (output / "20_permissions.sql").read_text()
    assert "no live" not in (output / "workflow/procedures.sql").read_text()
    assert "identity_unavailable" in (output / "workflow/procedures.sql").read_text()
    for filename in order:
        assert (output / filename).exists()
        sql = (output / filename).read_text()
        assert "TRUST_SIGNAL_DEV" not in sql
        assert " RESUME;" not in sql
        assert list(split_statements(StringIO(sql)))
    for filename, checksum in manifest["artifact_checksums"].items():
        assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == checksum
    script = (output / "apply.sh").read_text()
    assert "set -eu" in script
    assert 'connection=${1:?' in script
    assert "QUEUE_SMOKE" not in script
    assert script.count("--filename") == len(order)
    assert "CURRENT_TASK_GRAPHS" in (output / "21_quiesce.sql").read_text()


def test_live_mode_has_scoped_integration_and_correct_procedure_attachment(tmp_path):
    manifest = build_plan(tmp_path)
    assert "10_external_access.sql" in manifest["execution_order"]
    sql = (tmp_path / "init" / "10_external_access.sql").read_text()
    assert "api.gleif.org:443" in sql
    assert "NEW_WORKFLOW_GLEIF_EAI" in sql
    assert "CREATE OR REPLACE" not in sql
    procedures = (tmp_path / "init" / "workflow/procedures.sql").read_text()
    assert procedures.count("EXTERNAL_ACCESS_INTEGRATIONS") == 1
    assert "identity_unavailable" not in procedures


def test_applied_migrations_have_checksums_and_skip_guard(tmp_path):
    path = tmp_path / "V001__foundation.sql"
    path.write_text("CREATE TABLE IF NOT EXISTS EXAMPLE (VALUE VARCHAR);\n"
                    "INSERT INTO EXAMPLE SELECT 'quoted; value';\n")
    sql, checksum = tracked_migration(path)
    assert checksum == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "CHECKSUM !=" in sql
    assert "RAISE history_conflict" in sql
    assert "NOT EXISTS" in sql
    assert "INSERT INTO TRUST_SIGNAL_OPS.SCHEMA_MIGRATIONS" in sql
    statements = list(split_statements(StringIO(sql)))
    assert len(statements) == 1
    assert "quoted; value" in statements[0][0]
    path.write_text(path.read_text() + "-- changed\n")
    assert tracked_migration(path)[1] != checksum


def test_migration_versions_are_numeric_unique_and_contiguous(tmp_path):
    (tmp_path / "V001__foundation.sql").write_text("SELECT 1;")
    (tmp_path / "V003__gap.sql").write_text("SELECT 1;")
    with pytest.raises(ValueError, match="consecutive"):
        migration_paths(tmp_path)
    (tmp_path / "V002__second.sql").write_text("SELECT 1;")
    assert [path.name for path in migration_paths(tmp_path)] == [
        "V001__foundation.sql", "V002__second.sql", "V003__gap.sql"]
    (tmp_path / "V002__duplicate.sql").write_text("SELECT 1;")
    with pytest.raises(ValueError, match="Duplicate"):
        migration_paths(tmp_path)


def test_existing_artifacts_and_unsafe_parameters_are_rejected(tmp_path):
    build_plan(tmp_path, external_access=False)
    with pytest.raises(FileExistsError):
        build_plan(tmp_path, external_access=False)
    with pytest.raises(ValueError):
        initialize(tmp_path / "bad", Path("src"), Path("snowflake"),
                   "DB; DROP DATABASE DB", "WH", "ROLE", "ACCOUNTADMIN")
    with pytest.raises(ValueError, match="dedicated"):
        initialize(tmp_path / "bad", Path("src"), Path("snowflake"),
                   "DB", "WH", "ACCOUNTADMIN", "ACCOUNTADMIN")
    with pytest.raises(ValueError, match="together"):
        build_plan(tmp_path, ingestion_env_file=Path("private.env"))


def test_initialization_cli_only_generates_plan(tmp_path):
    result = subprocess.run([
        sys.executable, "-m", "trust_signal.persistence.initialize", "--database", "NEW_DB",
        "--warehouse", "NEW_WH", "--without-external-access",
        "--output-dir", str(tmp_path / "cli"),
    ], capture_output=True, text=True, check=True, timeout=30)
    assert json.loads(result.stdout)["executed"] is False
    assert json.loads(result.stdout)["migration_count"] == 7
