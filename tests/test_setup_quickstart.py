"""Exercise the public new-account commands offline, with temporary credentials."""

import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("cryptography")


def test_fresh_account_keys_and_setup_cli(tmp_path):
    config = tmp_path / ".env"
    config.write_text('''TRUST_SIGNAL_PLATFORM=snowflake
TRUST_SIGNAL_SNOWFLAKE_ACCOUNT=TEST-ACCOUNT
TRUST_SIGNAL_SNOWFLAKE_USER=FRIEND_SVC
TRUST_SIGNAL_SNOWFLAKE_ROLE=FRIEND_ROLE
TRUST_SIGNAL_SNOWFLAKE_WAREHOUSE=FRIEND_WH
TRUST_SIGNAL_SNOWFLAKE_DATABASE=FRIEND_DB
TRUST_SIGNAL_SNOWFLAKE_SCHEMA=TRUST_SIGNAL_RAW
TRUST_SIGNAL_SNOWFLAKE_PRIVATE_KEY_FILE=.secrets/key.p8
TRUST_SIGNAL_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE_FILE=.secrets/password
''')
    config.chmod(0o600)
    public = tmp_path / ".secrets/public.pem"
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("TRUST_SIGNAL_")}
    keys_command = [sys.executable, "-m", "trust_signal.persistence.keys", "--env-file", str(config),
                    "--public-key-file", str(public)]
    keys = subprocess.run(keys_command, capture_output=True, text=True, env=environment,
                          check=True, timeout=30)
    assert json.loads(keys.stdout)["status"] == "created"
    original = (public.parent / "key.p8").read_bytes()
    repeated = subprocess.run(keys_command, capture_output=True, text=True, env=environment,
                              check=False, timeout=30)
    assert repeated.returncode == 1
    assert (public.parent / "key.p8").read_bytes() == original
    assert "never overwritten" in repeated.stderr
    output = tmp_path / "output/setup.sql"
    setup_command = [sys.executable, "-m", "trust_signal.persistence.setup", "--env-file", str(config),
                     "--public-key-file", str(public), "--output", str(output)]
    setup = subprocess.run(setup_command, capture_output=True, text=True, env=environment,
                           check=True, timeout=30)
    result = json.loads(setup.stdout)
    assert result["executed"] is False
    assert result["account"] == "TEST-ACCOUNT"
    sql = output.read_text()
    assert "CREATE DATABASE IF NOT EXISTS FRIEND_DB" in sql
    assert "CREATE USER IF NOT EXISTS FRIEND_SVC" in sql
    assert "PRIVATE KEY" not in sql
    assert "GRANT SELECT, INSERT ON TABLE FRIEND_DB.TRUST_SIGNAL_RAW.SOURCE_RESPONSE_CHUNKS TO ROLE FRIEND_ROLE" in sql
    for version in range(1, 7):
        assert f"Migration: V{version:03}" in sql
    initialization = tmp_path / "output/initialization"
    complete = subprocess.run([
        sys.executable, "-m", "trust_signal.persistence.initialize",
        "--database", "FRIEND_DB", "--warehouse", "FRIEND_WH",
        "--workflow-role", "FRIEND_WORKFLOW", "--without-external-access",
        "--ingestion-env-file", str(config), "--public-key-file", str(public),
        "--output-dir", str(initialization),
    ], capture_output=True, text=True, env=environment, check=True, timeout=30)
    assert json.loads(complete.stdout)["executed"] is False
    identity = (initialization / "09_ingestion_identity.sql").read_text()
    assert "CREATE USER IF NOT EXISTS FRIEND_SVC" in identity
    assert "RSA_PUBLIC_KEY" in identity
    assert "PRIVATE KEY" not in identity
    assert "ALTER USER" not in identity
    assert "GRANT ROLE FRIEND_ROLE TO USER FRIEND_SVC" in identity
    assert "FRIEND_WORKFLOW TO USER FRIEND_SVC" not in identity
