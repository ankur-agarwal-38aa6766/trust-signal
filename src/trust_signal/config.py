"""Local configuration without mutating process-global environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values


def environment_config(path: Path | None = None) -> dict[str, str]:
    values = {}
    if path is not None:
        if not path.is_file():
            raise ValueError("Configuration file does not exist.")
        # Avoid expansion against a different account's process environment.
        values = {key: value for key, value in dotenv_values(path, interpolate=False).items()
                  if value is not None}
    values.update(os.environ)
    provider = values.get("TRUST_SIGNAL_PLATFORM", "snowflake").strip().lower()
    if provider != "snowflake":
        raise ValueError(f"Platform {provider!r} is not implemented; no connection was opened.")
    return values
