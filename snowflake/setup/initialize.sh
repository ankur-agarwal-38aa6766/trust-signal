#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
uv run --locked --extra snowflake python -m trust_signal.persistence.initialize "$@"
