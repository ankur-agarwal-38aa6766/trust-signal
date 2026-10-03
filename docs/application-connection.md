# Reusable Snowflake Application Connection

The preferred account-portable configuration is now `.env.example` plus a private
`.env`. See [Portable Deployment](portable-deployment.md) for account onboarding,
setup SQL generation and the boundary between account configuration and cloud adapters.

## Verified DEV setup

The application uses the official Snowflake Python Connector with key-pair
authentication. It no longer starts a Snowflake CLI subprocess for every query
when `--env-file` or `--application-config` is selected. The existing OAuth CLI mode remains
available for administration and backwards compatibility.

| Setting | DEV value |
|---|---|
| Account | `SLSSBSN-BQ70973` |
| Service user | `TRUST_SIGNAL_INGEST_SVC` (`TYPE=SERVICE`) |
| Runtime role | `TRUST_SIGNAL_INGESTOR` |
| Warehouse | `TRUST_SIGNAL_PIPELINE_WH` |
| Database | `TRUST_SIGNAL_DEV` |
| Default schema | `TRUST_SIGNAL_RAW` |

The role has database/schema/warehouse USAGE, SELECT/INSERT on
`RAW.SOURCE_OBSERVATIONS`, and SELECT/INSERT/UPDATE on `OPS.SOURCE_RUNS`
(both with the `TRUST_SIGNAL_` schema prefix). It has no account administration,
object creation, table deletion, or future-table grants. The identity-research
tables are deliberately not granted yet. Administrative setup is captured in
`snowflake/bootstrap/APPLICATION_IDENTITY.sql.template`; review it before use in
another account and never replace an existing user's public key blindly.

An encrypted RSA private key and random passphrase are stored separately in
ignored `.secrets/` files, with directory permissions 0700 and file permissions
0600. Only the public key was registered in Snowflake. This is local DEV secret
storage, not a production vault: anyone able to read both files can authenticate.
Do not share these files, paste their contents into chat, commit them, or put them
in a container image. Use a secret manager/mounted secrets for external production
workers, or the provided service identity when deploying inside Snowflake.

## Run locally

From the repository root:

```bash
uv sync --extra dev --extra snowflake

.venv/bin/python -m trust_signal.persistence.connection \
  --env-file .env
```

The health check executes two context queries on the same application session
and reports `session_reused: true`. It does not print credentials.

```bash
.venv/bin/python -m trust_signal.ingestion.raw_export \
  --lei INR2EJN1ERAN0W5ZP974 \
  --expected-name "MICROSOFT CORPORATION" \
  --output-dir outputs/live/microsoft_gleif_application \
  --env-file .env
```

For saved-bundle replay without another source fetch:

```bash
.venv/bin/python -m trust_signal.ingestion.load \
  --bundle-dir outputs/live/microsoft_gleif_application \
  --env-file .env
```

The multi-source ingestion command also accepts `--env-file` or `--application-config`
instead of `--connection`. Application and CLI modes are mutually exclusive. TOML key
paths resolve relative to the config file, not the current working directory.
The selected database must match the config. The health check additionally
supports explicitly exported environment variables from `.env.example`, with those
values taking precedence over dotenv configuration. It discovers a local `.env`
when no config flag is provided. No process-global environment changes are made.

Example config (paths only; no private key material):

```toml
account = "SLSSBSN-BQ70973"
user = "TRUST_SIGNAL_INGEST_SVC"
role = "TRUST_SIGNAL_INGESTOR"
warehouse = "TRUST_SIGNAL_PIPELINE_WH"
database = "TRUST_SIGNAL_DEV"
schema = "TRUST_SIGNAL_RAW"
private_key_file = "snowflake_key.p8"
private_key_passphrase_file = "snowflake_key.pass"
```

## Session Lifecycle

`SnowflakeSession` opens lazily, serializes SQL with a lock, reuses the connection
across repository operations, and closes explicitly on context exit. One session
is shared by evidence storage and source-run logging within a worker. This is a
single-worker session manager, not a multi-process pool. Parallel research can
fetch independently; its database writes are serialized. Do not share a session
across processes or let agents change its role/schema/session context.

SQL uses Snowflake's statement parser. Statement, login and network timeouts are
bounded; queries carry the `trust_signal_application` query tag. Keep-alive is
disabled. A failed operation discards its connection; a subsequent caller can
establish a new one. Failed writes are never automatically re-executed. Autocommit
means earlier statements may have committed even if a later statement fails.
Readback verification and replayable observation IDs remain the recovery tools.

Existing repository class names retain `SnowflakeCli` for compatibility; their
optional executor injection routes all SQL through the reusable session in
application mode, without duplicating payload verification logic.

## Live Verification

On 2026-10-03, key-pair login succeeded and two queries returned the same session
ID under the service identity. Full real Microsoft ingestion also succeeded:

- Run: `run_2a5d861093fc44c98889df7e5877b091`, status `succeeded`.
- Observation: `observation_c29f64343d925f7b80cb9d467e3fce93`.
- Inserted: 1; verified: 1; source: official GLEIF API.
- Bundle: ignored `outputs/live/microsoft_gleif_application/`.

No synthetic records were inserted. Neither test required browser login or
CLI subprocesses for application queries.
Replaying the same bundle through application mode returned `inserted_rows: 0`
and `verified_rows: 1`, confirming no duplicate observation was inserted.

## Deployment and Rotation

Maintain separate users/keys for DEV and production. Before multi-user hosting,
implement tenant isolation, network restrictions, monitoring and durable worker
recovery. For key rotation, register a replacement public key in `RSA_PUBLIC_KEY_2`,
test it with a separate protected key/config, switch the worker, then retire the
old public key and local secret files after confirming no active workers depend
on them. Do not overwrite the sole working key first.

References: [Python Connector authentication](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect),
[connector lifecycle](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api),
[key-pair rotation](https://docs.snowflake.com/en/user-guide/key-pair-auth).
