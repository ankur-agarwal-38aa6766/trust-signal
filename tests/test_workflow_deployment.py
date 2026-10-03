import io
from zipfile import ZipFile

import pytest

from trust_signal.orchestration.deployment import build, render, source_bundle


def test_bundle_contains_only_package_code_and_is_repeatable(tmp_path):
    package = tmp_path / "src" / "trust_signal"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""Test package."""\n')
    (package / ".env").write_text("PRIVATE_CREDENTIAL=value")
    (tmp_path / "src" / "other.py").write_text("private = True\n")
    first = source_bundle(tmp_path / "src")
    assert first == source_bundle(tmp_path / "src")
    with ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == ["trust_signal/__init__.py"]


def test_graph_fanout_join_gating_retries_and_activation_are_explicit():
    artifacts = render("TEST_DB", "TEST_WH", "TEST_ROLE", "GLEIF_EAI", "trust_signal_" + "a" * 16 + ".zip")
    tasks = artifacts["tasks.sql"]
    assert "OVERLAP_POLICY = NO_OVERLAP" in tasks
    assert "TASK_AUTO_RETRY_ATTEMPTS = 2" in tasks
    assert "AFTER TEST_DB.TRUST_SIGNAL_OPS.TS_IDENTITY, TEST_DB.TRUST_SIGNAL_OPS.TS_SANCTIONS" in tasks
    assert "SYSTEM$GET_PREDECESSOR_RETURN_VALUE('TS_IDENTITY') != 'NONE'" in tasks
    assert "FINALIZE = TEST_DB.TRUST_SIGNAL_OPS.TS_CLAIM" in tasks
    assert " RESUME" not in tasks
    assert "TS_CLAIM RESUME" not in artifacts["enable_children.sql"]
    assert artifacts["procedures.sql"].count("EXTERNAL_ACCESS_INTEGRATIONS") == 1


def test_generated_handler_python_is_valid_and_dependency_names_are_pinned():
    artifacts = render("TEST_DB", "TEST_WH", "TEST_ROLE", "GLEIF_EAI", "trust_signal_" + "a" * 16 + ".zip")
    fragments = artifacts["procedures.sql"].split(" AS $$\n")[1:]
    assert len(fragments) == 5
    for fragment in fragments:
        compile(fragment.split("$$;", 1)[0], "stored_handler.py", "exec")
    assert "pydantic==2.11.7" in artifacts["procedures.sql"]


def test_build_is_plan_only_and_refuses_to_overwrite_changed_release(tmp_path):
    source = tmp_path / "src"
    (source / "trust_signal").mkdir(parents=True)
    (source / "trust_signal" / "__init__.py").write_text('"""Test package."""\n')
    output = tmp_path / "release"
    first = build(source, output, "TEST_DB", "TEST_WH", "TEST_ROLE", "GLEIF_EAI")
    assert not first["deployed"] and not first["tasks_enabled"]
    assert first == build(source, output, "TEST_DB", "TEST_WH", "TEST_ROLE", "GLEIF_EAI")
    (output / "tasks.sql").write_text("User changes")
    with pytest.raises(FileExistsError):
        build(source, output, "TEST_DB", "TEST_WH", "TEST_ROLE", "GLEIF_EAI")


def test_unsafe_identifiers_and_wrong_pydantic_major_are_rejected():
    with pytest.raises(ValueError):
        render("DB;DROP", "WH", "ROLE", "EAI", "trust_signal_" + "a" * 16 + ".zip")
    with pytest.raises(ValueError):
        render("DB", "WH", "ROLE", "EAI", "trust_signal_" + "a" * 16 + ".zip", "3.0.0")
def test_restricted_account_artifacts_omit_egress_and_fail_closed():
    from trust_signal.orchestration.deployment import render

    files = render("DB", "WH", "ROLE", "EAI", "trust_signal_0123456789abcdef.zip",
                   external_access=False)
    assert "GRANT USAGE ON INTEGRATION" not in files["grants.sql"]
    assert "EXTERNAL_ACCESS_INTEGRATIONS" not in files["procedures.sql"]
    assert "snowflake_runtime.identity_unavailable" in files["procedures.sql"]
    from io import StringIO

    from snowflake.connector.util_text import split_statements

    statements = list(split_statements(StringIO(files["tasks.sql"])))
    assert sum("CREATE OR REPLACE TASK" in sql for sql, _ in statements) == 10
    assert "END;" in statements[3][0]
