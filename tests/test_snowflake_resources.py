import json
import subprocess
import sys
from pathlib import Path

import pytest

from trust_signal.persistence.sql_resources import read_resource, render_sql


def test_resource_templates_are_versioned_sources_not_output_dependencies():
    assert Path("snowflake/procedures/WORKFLOW_PROCEDURE.sql.template").is_file()
    catalog = json.loads(read_resource("procedures/WORKFLOW.json"))
    assert len(catalog) == 5
    assert len({procedure["name"] for procedure in catalog}) == 5
    graph = json.loads(read_resource("tasks/WORKFLOW_GRAPH.json"))
    assert graph["root"] == "TS_CLAIM"
    assert graph["finalizer"] == "TS_FINALIZE"
    assert len(graph["children"]) == 8
    assert render_sql("bootstrap/WORKFLOW_CONTEXT.sql.template", role="ROLE", database="DB") == (
        "USE ROLE ROLE;\nUSE DATABASE DB;\nUSE SCHEMA TRUST_SIGNAL_OPS;\n"
    )


def test_template_directory_is_explicit_and_path_traversal_is_rejected(tmp_path):
    (tmp_path / "example.sql.template").write_text("SELECT '{name}';\n")
    assert render_sql("example.sql.template", resources=tmp_path, name="test") == "SELECT 'test';\n"
    with pytest.raises(ValueError, match="inside"):
        read_resource("../private.env", resources=tmp_path)
    with pytest.raises(KeyError):
        render_sql("example.sql.template", resources=tmp_path)


def test_default_initializer_bundle_is_under_snowflake_not_outputs(tmp_path):
    root = Path.cwd()
    result = subprocess.run([
        sys.executable, "-m", "trust_signal.persistence.initialize", "--database", "TEST_DB",
        "--warehouse", "TEST_WH", "--without-external-access",
        "--source-dir", str(root / "src"), "--snowflake-dir", str(root / "snowflake"),
    ], cwd=tmp_path, capture_output=True, text=True, check=True, timeout=30)
    assert json.loads(result.stdout)["executed"] is False
    assert (tmp_path / "snowflake/build/installation/apply.sh").is_file()
    assert not (tmp_path / "outputs").exists()


def test_source_scripts_are_valid_shell():
    for path in ("snowflake/setup/initialize.sh", "snowflake/setup/APPLY.sh.template"):
        subprocess.run(["sh", "-n", path], check=True, timeout=5)
