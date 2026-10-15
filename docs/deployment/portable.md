# Portable configuration and installation

Account changes within Snowflake are configuration. Changing cloud provider needs
concrete adapters and verification; `TRUST_SIGNAL_PLATFORM=snowflake` is currently
the only accepted value. [Component layout](../architecture/components.md) owns
provider boundaries; [Google profile](google-cloud.md) is a proposal, not an enabled
runtime. [Readiness](readiness.md) owns installation/release acceptance.

## Configuration contract

Share [.env.example](../../.env.example), never a populated `.env`, private key,
passphrase or source token. Each installation owns its identities, secrets and
resource names. Exported variables override dotenv values; loading does not expand
shell variables or mutate global environment. Relative credential paths resolve
against the configuration file directory. Legacy TOML/CLI transports remain available.

Private dotenv files support local/configured installations. Production secret
storage and future customer onboarding require scoped workload identities, secret
references, tenant-bound pools and audit. An email/principal ID alone is not cloud
credentials. Do not share customer secrets across installations.

## Snowflake ingestion-only setup

Install locked dependencies using the root [quickstart](../../README.md#run-locally).
Copy the configuration template and edit it with your own account, dedicated service
user, restricted ingestion role, warehouse/database and key paths. Runtime roles
must not be account administrators. Remove stale exported settings before changing
accounts.

```bash
cp .env.example .env
chmod 600 .env
uv run --locked --extra snowflake python -m trust_signal.persistence.keys \
  --env-file .env --public-key-file .secrets/snowflake_key.pub

uv run --locked --extra snowflake python -m trust_signal.persistence.setup \
  --env-file .env --public-key-file .secrets/snowflake_key.pub \
  --output snowflake/build/setup.sql
```

Key generation uses configured paths, private directory/file modes and refuses
overwrites. Setup validates identifiers and matching key pairs, generates SQL, opens
no connection and provisions nothing. Review targets/current objects/costs, then
execute the SQL through your authorized administrator connection or Snowsight.
Do not reuse another installation's user or overwrite its working keys.

The ingestion-only plan creates configured database, initially suspended XSMALL
warehouse, ordered migrations, service identity and RAW/OPS grants. Stable application
schemas remain `TRUST_SIGNAL_RAW/CORE/OPS/SERVE`. It does not deploy workflow code/tasks,
production review authorization or AI. Existing objects/settings are not automatically
reconciled; DDL can partially commit. Inspect failed statements before retrying.
It has migration validation but not the complete initializer's applied checksum ledger.

For the full workflow backend, use [initialization](../operations/snowflake-initialization.md)
instead. Its separate plan/apply lifecycle includes checksummed migration history,
scoped grants, code upload, procedures and suspended tasks. Neither path proves a
fresh account is live-verified; check [status](../status.md).

After apply, [application connection](../operations/application-connection.md) owns
connection health, ingestion export and saved-bundle replay commands. Verify actual
identity/role/targets and RAW/OPS readback before releasing source records.

## Additional provider profiles

A profile implements operational state, evidence retention/readback, source-run and
identity stores, native execution, review, secrets and installation lifecycle. Optional
analytics/models/retrieval/events have separate capability declarations. Preserve
stable IDs, hashes, input/policy versions, unknown-write recovery and reviewer history.

Use one execution owner per run, with documented database transaction/concurrency
guarantees. Source selection is independent from hosting cloud. A missing mandatory
capability fails explicitly, without a different cloud or fixture fallback. Hybrid
installations need an explicit design. Migration needs permitted exports, verified
counts/hashes, active-run reconciliation, new credentials and history-preserving cutover.

First Google delivery uses configured cloud credentials/project/location directly.
Product signup, customer cloud authorization and hosted tenancy are later work.
No arbitrary provider becomes supported by changing an environment variable.
