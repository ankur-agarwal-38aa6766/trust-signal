from dataclasses import replace
from unittest.mock import Mock

import pytest

pytest.importorskip("snowflake.connector")

from trust_signal.persistence.connection import (
    SnowflakeSession,
    SnowflakeSettings,
    application_stores,
)
from trust_signal.persistence.snowflake_cli import ObservationWriteError


@pytest.fixture
def settings(tmp_path):
    key = tmp_path / "key.p8"
    password = tmp_path / "password"
    key.write_text("test key")
    password.write_text("test-secret")
    key.chmod(0o600)
    password.chmod(0o600)
    return SnowflakeSettings("ORG-ACCOUNT", "APP_SVC", "INGESTOR", "PIPELINE_WH",
                             "TRUST_SIGNAL_DEV", "TRUST_SIGNAL_RAW", key, password)


def fake_connection():
    connection = Mock()
    connection.is_closed.return_value = False
    cursor = Mock()
    cursor.description = [("VALUE",)]
    cursor.fetchall.return_value = [(1,)]
    connection.cursor.return_value.__enter__ = Mock(return_value=cursor)
    connection.cursor.return_value.__exit__ = Mock(return_value=False)
    return connection, cursor


def test_reuses_connection_and_closes_it(settings):
    connection, _ = fake_connection()
    connect = Mock(return_value=connection)
    with SnowflakeSession(settings, connect=connect) as session:
        assert session.execute("SELECT 1;") == [{"VALUE": 1}]
        assert session.execute("SELECT 1;") == [{"VALUE": 1}]
    connect.assert_called_once()
    connection.close.assert_called_once()
    assert connect.call_args.kwargs["authenticator"] == "SNOWFLAKE_JWT"
    assert connect.call_args.kwargs["autocommit"] is True
    with pytest.raises(ObservationWriteError):
        session.execute("SELECT 1;")
    connect.assert_called_once()


def test_uses_official_statement_parser(settings):
    connection, cursor = fake_connection()
    with SnowflakeSession(settings, connect=Mock(return_value=connection)) as session:
        session.execute("SELECT ';' AS VALUE; -- a semicolon;\nSELECT 2 AS VALUE;")
    assert cursor.execute.call_count == 2
    assert "';'" in cursor.execute.call_args_list[0].args[0]


def test_failed_write_is_not_replayed_and_next_call_reconnects(settings):
    broken, cursor = fake_connection()
    cursor.execute.side_effect = RuntimeError("test-secret")
    healthy, _ = fake_connection()
    connect = Mock(side_effect=[broken, healthy])
    with SnowflakeSession(settings, connect=connect) as session:
        with pytest.raises(ObservationWriteError, match="unknown") as error:
            session.execute("INSERT INTO test VALUES (1);")
        assert "test-secret" not in str(error.value)
        assert cursor.execute.call_count == 1
        broken.close.assert_called_once()
        assert session.execute("SELECT 1;") == [{"VALUE": 1}]
    assert connect.call_count == 2


def test_closed_remote_connection_reconnects(settings):
    old, _ = fake_connection()
    new, _ = fake_connection()
    with SnowflakeSession(settings, connect=Mock(side_effect=[old, new])) as session:
        session.execute("SELECT 1;")
        old.is_closed.return_value = True
        session.execute("SELECT 1;")
    new.close.assert_called_once()


def test_insecure_key_rejected_before_connect(settings):
    settings.private_key_file.chmod(0o644)
    connect = Mock()
    with (
        SnowflakeSession(settings, connect=connect) as session,
        pytest.raises(ObservationWriteError),
    ):
        session.execute("SELECT 1;")
    connect.assert_not_called()


def test_settings_reject_invalid_context_and_hide_paths(settings):
    with pytest.raises(ValueError):
        replace(settings, database="DEV; DROP DATABASE DEV").connection_options()
    assert "test-secret" not in repr(settings)
    assert str(settings.private_key_file) not in repr(settings)


def test_settings_env_is_explicit(monkeypatch):
    monkeypatch.delenv("TRUST_SIGNAL_SNOWFLAKE_ACCOUNT", raising=False)
    with pytest.raises(ValueError, match="Set all"):
        SnowflakeSettings.from_env()


def test_config_relative_paths_and_database_guard(tmp_path):
    config = tmp_path / "snowflake.toml"
    config.write_text('''account="ORG-ACCOUNT"
user="APP_SVC"
role="INGESTOR"
warehouse="WH"
database="TRUST_SIGNAL_DEV"
schema="TRUST_SIGNAL_RAW"
private_key_file="key.p8"
private_key_passphrase_file="password"
''')
    assert SnowflakeSettings.from_file(config).private_key_file == tmp_path / "key.p8"
    with pytest.raises(ValueError, match="differs"), application_stores(config, "OTHER_DB"):
        pytest.fail("Unexpected database")


def test_shared_executor_is_injected_into_both_stores(tmp_path, monkeypatch):
    settings = Mock(database="TRUST_SIGNAL_DEV")
    monkeypatch.setattr(SnowflakeSettings, "from_config", Mock(return_value=settings))
    with application_stores(tmp_path / "config", "TRUST_SIGNAL_DEV") as (observations, runs):
        assert observations.executor is runs.cli.executor


def test_observation_store_delegates_without_cli(monkeypatch):
    from test_raw_export import lookup_for_test
    from test_snowflake_store import stored_row

    from trust_signal.persistence.snowflake_cli import SnowflakeCliObservationStore

    lookup, _ = lookup_for_test()
    executor = Mock()
    executor.execute.return_value = [{"number of rows inserted": 0}, stored_row(lookup.observation)]
    monkeypatch.setattr("subprocess.run", Mock(side_effect=AssertionError("CLI should not run")))
    receipt = SnowflakeCliObservationStore("application", executor=executor).store_observation(
        lookup.observation
    )
    assert receipt.inserted_rows == 0
    assert receipt.verified_rows == 1
    assert "INSERT INTO" in executor.execute.call_args.args[0]
