"""Protected local key generation; never overwrite an existing credential."""

from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

from trust_signal.persistence.settings import SnowflakeSettings


def generate_keys(settings: SnowflakeSettings, public_key_file: Path) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    settings.validate_context()
    paths = [settings.private_key_file, settings.private_key_passphrase_file, public_key_file]
    if len({path.resolve() for path in paths}) != 3:
        raise ValueError("Key, passphrase and public key paths must be distinct.")
    if any(path.exists() or path.is_symlink() for path in paths):
        raise ValueError("Credentials already exist; generation refuses to overwrite them.")
    for parent in {path.parent for path in paths}:
        parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if parent.stat().st_mode & 0o077:
            raise ValueError("Credential directories must be private (0700).")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    password = secrets.token_hex(48).encode("ascii")
    bodies = [key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.BestAvailableEncryption(password)),
              password + b"\n",
              key.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)]
    created = []
    try:
        for path, body in zip(paths, bodies, strict=True):
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created.append(path)
            with os.fdopen(descriptor, "wb") as file:
                file.write(body)
    except BaseException:
        # Only remove files created by this failed attempt, never pre-existing keys.
        for path in created:
            path.unlink(missing_ok=True)
        raise


def validate_keypair(settings: SnowflakeSettings, public_key_file: Path):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    password = settings.key_passphrase().encode("utf-8")
    private = serialization.load_pem_private_key(settings.private_key_file.read_bytes(), password)
    public = serialization.load_pem_public_key(public_key_file.read_bytes())
    if not isinstance(private, rsa.RSAPrivateKey) or private.key_size < 2048:
        raise ValueError("A private RSA key of at least 2048 bits is required.")
    if not isinstance(public, rsa.RSAPublicKey) or public.public_numbers() != private.public_key().public_numbers():
        raise ValueError("The setup public key does not match the application's private key.")
    return public


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--public-key-file", type=Path, required=True)
    args = parser.parse_args()
    try:
        generate_keys(SnowflakeSettings.from_env(args.env_file), args.public_key_file)
        print(json.dumps({"status": "created", "private_material_printed": False}, indent=2))
    except (ValueError, OSError, ImportError):
        parser.exit(1, "Key generation refused. Check configuration and directory permissions; "
                    "existing credential files are never overwritten.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
