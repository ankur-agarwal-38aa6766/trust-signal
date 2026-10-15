# TrustSignal

TrustSignal researches legal organizations using official-source evidence and
traceable human review. It resolves identity before attributing findings, preserves
source responses, compares independent research, and exposes uncertainty and gaps.
Worldwide coverage is a goal delivered source by source.

The direction is one shared Streamlit UI with durable provider-managed procedures,
jobs and DAG workflows. Snowflake has implemented foundations; Google Cloud is the
next planned profile. No complete profile is verified for production. The code
license remains undecided.

Start with the [documentation index](docs/README.md), then
[scope](docs/product/scope.md), [architecture](docs/architecture/overview.md),
[implementation status](docs/status.md), and [backlog](docs/backlog/README.md).

## Run locally

Requires Python 3.11–3.14 and `uv`. From the repository root:

```bash
uv sync --locked --extra dev --extra snowflake
uv run --locked python ui/run.py
```

The selected application is `ui/app.py`; the launcher applies
`ui/streamlit/config.toml`. See [UI setup](ui/README.md).
Intake invokes the local graph synchronously; dossier, queue and operations content
includes illustrative data. This preview does not provide durable connected review,
authentication, measured telemetry or a scoring service.

For an offline JSON case using labeled fixtures:

```bash
uv run --locked trust-signal "Example Organization Ltd" \
  --jurisdiction GB --registration-id 00000000
```

The assessment is unscored. Live source failures never fall back to fixture evidence.
For opt-in live flags, see [research usage](docs/components/research.md#cli-usage).

## Configure Snowflake

Copy [.env.example](.env.example) to a private `.env` and use your installation's
account, service identity, runtime role and resource names.
`TRUST_SIGNAL_PLATFORM=snowflake` is the only implemented configuration choice.

[Portable configuration](docs/deployment/portable.md) distinguishes ingestion-only
setup from [complete initialization](docs/operations/snowflake-initialization.md).
Plan generation is offline; administrator apply is a separate reviewed operation.
Fresh-account installation and a complete live case still need verification.

After setup, [application connection](docs/operations/application-connection.md)
and [ingestion](docs/components/ingestion.md) describe live retrieval, RAW/OPS readback
and saved-bundle replay. Keep `.env`, keys, tokens and evidence outputs private.

## Verify changes

```bash
uv run --locked --extra dev --extra snowflake pytest
uv run --locked --extra dev ruff check .
```

[Status](docs/status.md) separates code inspection, fixtures, replay, dated live
evidence and deployed operation. Offline tests do not establish cloud readiness.
