import os
from dataclasses import replace
from pathlib import Path

import pytest

from trust_signal.config import environment_config
from trust_signal.persistence.connection import SnowflakeSettings


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    for name in list(os.environ):
        if name.startswith("TRUST_SIGNAL_"):
            monkeypatch.delenv(name)
    path = tmp_path / ".env"
    path.write_text('''TRUST_SIGNAL_PLATFORM=snowflake
TRUST_SIGNAL_SNOWFLAKE_ACCOUNT=OTHER-ACCOUNT
TRUST_SIGNAL_SNOWFLAKE_USER=OTHER_SVC
TRUST_SIGNAL_SNOWFLAKE_ROLE=OTHER_ROLE
TRUST_SIGNAL_SNOWFLAKE_WAREHOUSE=OTHER_WH
TRUST_SIGNAL_SNOWFLAKE_DATABASE=OTHER_DB
TRUST_SIGNAL_SNOWFLAKE_SCHEMA=TRUST_SIGNAL_RAW
TRUST_SIGNAL_SNOWFLAKE_PRIVATE_KEY_FILE=keys/private.p8
TRUST_SIGNAL_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_FILE=keys/passphrase
''')
    return path


def test_other_account_and_relative_secret_paths(env_file):
    settings = SnowflakeSettings.from_config(env_file)
    assert settings.account == "OTHER-ACCOUNT"
    assert settings.database == "OTHER_DB"
    assert settings.private_key_file == env_file.parent / "keys/private.p8"
    assert "TRUST_SIGNAL_SNOWFLAKE_ACCOUNT" not in os.environ


def test_environment_overrides_file(env_file, monkeypatch):
    monkeypatch.setenv("TRUST_SIGNAL_SNOWFLAKE_DATABASE", "DEPLOYED_DB")
    assert SnowflakeSettings.from_env(env_file).database == "DEPLOYED_DB"


def test_unknown_provider_never_falls_back_to_snowflake(env_file, monkeypatch):
    monkeypatch.setenv("TRUST_SIGNAL_PLATFORM", "gcp")
    with pytest.raises(ValueError, match="not implemented"):
        SnowflakeSettings.from_env(env_file)


def test_missing_explicit_file_fails(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        environment_config(tmp_path / "absent")


def test_dotenv_is_not_shell_code(env_file):
    with env_file.open("a") as file:
        file.write('EXAMPLE=$(touch /tmp/never-execute)\nLITERAL=${HOME}\n')
    config = environment_config(env_file)
    assert config["EXAMPLE"] == "$(touch /tmp/never-execute)"
    assert config["LITERAL"] == "${HOME}"


def test_source_credentials_are_injected_without_changing_environment(env_file, monkeypatch):
    from unittest.mock import Mock

    from trust_signal.connectors.registry import SourceRequest, default_registry

    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    with env_file.open("a") as file:
        file.write("COMPANIES_HOUSE_API_KEY=test-source-key\n")
    adapter = Mock()
    adapter.fetch_company_profile.return_value = None
    factory = Mock()
    factory.source_id = "uk_companies_house"
    factory.connector_version = "0.1.0"
    factory.return_value.__enter__ = Mock(return_value=adapter)
    factory.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr("trust_signal.connectors.registry.CompaniesHouseAdapter", factory)
    registry = default_registry(environment_config(env_file))
    request = SourceRequest(source_id="uk_companies_house", operation="lookup", value="00445790")
    assert list(registry.get(request).fetch(request))
    factory.assert_called_once_with(api_key="test-source-key")
    assert "COMPANIES_HOUSE_API_KEY" not in os.environ
    assert next(row for row in registry.catalog() if row["source_id"] == request.source_id)["configured"]


def test_setup_plan_uses_account_names_without_opening_connection(env_file, tmp_path):
    pytest.importorskip("cryptography")
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    from trust_signal.persistence.setup import setup_sql

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = tmp_path / "public.pem"
    public.write_bytes(key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    settings = SnowflakeSettings.from_env(env_file)
    settings.private_key_file.parent.mkdir(mode=0o700)
    settings.private_key_file.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(b"test-password"),
    ))
    settings.private_key_passphrase_file.write_text("test-password")
    settings.private_key_file.chmod(0o600)
    settings.private_key_passphrase_file.chmod(0o600)
    sql = setup_sql(settings, public, Path("snowflake/migrations"))
    assert "CREATE DATABASE IF NOT EXISTS OTHER_DB" in sql
    assert "CREATE WAREHOUSE IF NOT EXISTS OTHER_WH" in sql
    assert "CREATE USER IF NOT EXISTS OTHER_SVC" in sql
    assert "TYPE = SERVICE" in sql
    assert "ADD COLUMN IF NOT EXISTS RAW_RESPONSE_TEXT" in sql
    assert "PRIVATE KEY" not in sql
    assert "ALTER USER" not in sql
    assert "TRUST_SIGNAL_DEV" not in sql
    with pytest.raises(ValueError, match="uppercase"):
        setup_sql(replace(settings, role="ROLE;DROP DATABASE DB"), public, Path("snowflake/migrations"))
    with pytest.raises(ValueError, match="dedicated runtime role"):
        setup_sql(replace(settings, role="ACCOUNTADMIN"), public, Path("snowflake/migrations"))
