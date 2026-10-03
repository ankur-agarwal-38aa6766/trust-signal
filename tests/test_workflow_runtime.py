from unittest.mock import Mock

from trust_signal.orchestration.snowflake_runtime import (
    SnowparkExecutor,
    identity,
    identity_unavailable,
)


def test_snowpark_executor_uses_existing_session_and_parses_quoted_semicolons():
    session = Mock()
    row = Mock()
    row.as_dict.return_value = {"VALUE": "a;b"}
    session.sql.return_value.collect.return_value = [row]
    result = SnowparkExecutor(session).execute("SELECT 'a;b' AS VALUE; SELECT 'c' AS VALUE;")
    assert len(result) == 2
    assert session.sql.call_count == 2
    assert "'a;b'" in session.sql.call_args_list[0].args[0]


def test_identity_handler_passes_only_confirmed_runs_to_children(monkeypatch):
    worker = Mock()
    monkeypatch.setattr("trust_signal.orchestration.snowflake_runtime.runner", lambda session: worker)
    worker.execute.return_value = {"confirmed": False}
    assert identity(Mock(), "run") == "NONE"
    worker.execute.return_value = {"confirmed": True}
    assert identity(Mock(), "run") == "run"


def test_restricted_identity_handler_records_gap_without_network(monkeypatch):
    worker = Mock()
    captured = {}

    def make_worker(store, handler):
        captured["branch"] = handler(None)
        return worker

    monkeypatch.setattr("trust_signal.orchestration.snowflake_runtime.repository", lambda _: Mock())
    monkeypatch.setattr("trust_signal.orchestration.snowflake_runtime.StageRunner", make_worker)
    assert identity_unavailable(Mock(), "run") == "NONE"
    assert captured["branch"].status == "failed"
    assert "no live identity lookup" in captured["branch"].limitations[0]
    worker.execute.assert_called_once()
