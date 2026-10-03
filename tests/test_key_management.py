from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from trust_signal.persistence.keys import generate_keys, validate_keypair
from trust_signal.persistence.settings import SnowflakeSettings
from trust_signal.persistence.setup import setup_sql


@pytest.fixture
def settings(tmp_path):
    return SnowflakeSettings("ORG-ACCOUNT", "APP_SVC", "INGESTOR", "PIPELINE_WH",
                             "APP_DB", "TRUST_SIGNAL_RAW", tmp_path / "keys/private.p8",
                             tmp_path / "keys/passphrase")


def test_generation_is_encrypted_private_and_refuses_overwrite(settings):
    public = settings.private_key_file.parent / "public.pem"
    generate_keys(settings, public)
    assert b"BEGIN ENCRYPTED PRIVATE KEY" in settings.private_key_file.read_bytes()
    for path in (settings.private_key_file, settings.private_key_passphrase_file, public):
        assert path.stat().st_mode & 0o777 == 0o600
    assert public.parent.stat().st_mode & 0o777 == 0o700
    assert validate_keypair(settings, public).key_size == 2048
    original = settings.private_key_file.read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        generate_keys(settings, public)
    assert settings.private_key_file.read_bytes() == original


def test_existing_partial_credentials_are_preserved(settings):
    settings.private_key_file.parent.mkdir(mode=0o700)
    settings.private_key_passphrase_file.write_text("existing-secret")
    public = settings.private_key_file.parent / "public.pem"
    with pytest.raises(ValueError, match="overwrite"):
        generate_keys(settings, public)
    assert settings.private_key_passphrase_file.read_text() == "existing-secret"
    assert not settings.private_key_file.exists()


def test_key_mismatch_is_rejected_before_setup_sql(settings, tmp_path):
    public = settings.private_key_file.parent / "public.pem"
    generate_keys(settings, public)
    other = replace(settings, private_key_file=tmp_path / "other/private.p8",
                    private_key_passphrase_file=tmp_path / "other/password")
    other_public = other.private_key_file.parent / "public.pem"
    generate_keys(other, other_public)
    with pytest.raises(ValueError, match="does not match"):
        setup_sql(settings, other_public, Path("snowflake/migrations"))


def test_publicly_readable_secret_directory_is_rejected(settings):
    settings.private_key_file.parent.mkdir(mode=0o755)
    settings.private_key_file.parent.chmod(0o755)
    with pytest.raises(ValueError, match="directories must be private"):
        generate_keys(settings, settings.private_key_file.parent / "public.pem")
    assert not settings.private_key_file.exists()


def test_colliding_secret_paths_are_rejected(settings):
    with pytest.raises(ValueError, match="distinct"):
        generate_keys(settings, settings.private_key_file)


def test_partial_write_cleanup_only_removes_new_files(settings, monkeypatch):
    import os

    original = os.open
    # Inject a failure after the private key write, with no pre-existing credentials.
    calls = 0

    def fail_second(path, flags, mode):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        return original(path, flags, mode)

    monkeypatch.setattr(os, "open", fail_second)
    with pytest.raises(OSError, match="disk full"):
        generate_keys(settings, settings.private_key_file.parent / "public.pem")
    assert not settings.private_key_file.exists()
    assert not settings.private_key_passphrase_file.exists()
