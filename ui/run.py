"""Launch the shared UI with settings from ui/streamlit/config.toml."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


def main() -> int:
    directory = Path(__file__).resolve().parent
    settings = tomllib.loads((directory / "streamlit" / "config.toml").read_text())
    flags = []
    for section, options in settings.items():
        for option, value in options.items():
            rendered = str(value).lower() if isinstance(value, bool) else str(value)
            flags.append(f"--{section}.{option}={rendered}")
    # Use Streamlit's public CLI. Later flags override the shared defaults.
    return subprocess.call([
        sys.executable, "-m", "streamlit", "run", str(directory / "app.py"),
        *flags, *sys.argv[1:],
    ])


if __name__ == "__main__":
    raise SystemExit(main())
