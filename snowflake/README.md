# Snowflake Resources

## Complete Initialization

All canonical installation definitions live here and are versioned in Git.
Start with [setup/README.md](setup/README.md) or run
`sh snowflake/setup/initialize.sh` with your target configuration.

Use [Snowflake initialization](../docs/snowflake-initialization.md) for a new
backend installation. `python -m trust_signal.persistence.initialize` generates
an ordered, administrator-reviewed SQL bundle containing all migrations, a
checksum ledger, optional ingestion identity, scoped network integration, grants,
code upload, procedures, tasks and inspection queries. Generation is offline;
the generated `apply.sh` is the explicit execution step. All tasks remain suspended.

The existing `persistence.setup` command below is retained for ingestion-only
bootstrap. Both paths share migration validation and service-user grant generation;
only the complete initializer tracks applied migration checksums.

## Ingestion-Only Setup

Follow [the repository quickstart](../README.md#try-in-your-snowflake-account).
Keep account settings in private `.env`, credentials in `.secrets/`, and generated
plans in ignored `snowflake/build/`. Use the key generator for a new installation;
it refuses to overwrite credentials. Preserve existing working keys.

```bash
uv run --locked --extra snowflake python -m trust_signal.persistence.setup \
  --env-file .env --public-key-file .secrets/snowflake_key.pub \
  --output snowflake/build/setup.sql
```

This validates configured identifiers and the matching key pair, then generates
administrator-reviewed SQL. It opens no connection and executes nothing. Review
and apply the plan in the intended account before running the application health
check. Do not use ingestion credentials to administer the account.

Versioned SQL templates are the canonical definitions; Python validates parameters
and assembles them into executable plans. Setup does not replace existing user keys, reconcile schema
drift or guarantee an atomic upgrade. It includes only the currently needed
ingestion grants.

## Layout

```text
snowflake/
  setup/                   # Setup entrypoint and application-script template
  bootstrap/               # Database/warehouse/context/upload/history templates
  migrations/              # Ordered schema changes; preserve migration history
  security/                # Workflow, operator and service-user grants
  integrations/            # Approved GLEIF network integration template
  procedures/              # SQL handler template and five-procedure catalog
  tasks/                   # Graph catalog, task templates and activation controls
  verification/            # Preflight and inventory SQL templates
  build/                   # Generated account-specific bundles; Git ignored
  app/streamlit_app.py      # Future hosted reviewer UI scaffold
  snowflake.yml            # Future Streamlit deployment scaffold
```

Files ending in `.sql.template` use named placeholders such as `{database}` and
must be rendered by setup before execution. `procedures/WORKFLOW.json` lists all
five handlers; `tasks/WORKFLOW_GRAPH.json` defines the complete dependency graph.
Neither requires generated files from `outputs/`. Existing historical output
bundles are retained, but new setup/deployment commands write to `build/`.

| Migration | Purpose |
|---|---|
| V001 | Foundation schemas and raw/core/run tables |
| V002 | Case intake, source configuration and serving views |
| V003 | Historical standalone source-run table setup |
| V004 | Exact JSON/XML response retention; required by the current writer |
| V005 | Identity-decision snapshots and evidence views |
| V006 | Exact-response chunk storage |
| V007 | Workflow runs, stage attempts, code stage and workflow views |

V003 intentionally repeats V001's `CREATE TABLE IF NOT EXISTS`: it enabled a
standalone log deployment before the entire foundation was deployed. Preserve
released migration history. A fresh setup applies all migrations in order;
don't stop at V001/V002 because current evidence verification also requires V004.

## Runtime Boundaries

Configuration: `persistence/settings.py`; lifecycle: `persistence/connection.py`.
Repositories consume `SqlExecutor`, not a particular authentication method.
Evidence, source runs and identity snapshots have independent repositories and
can share the reusable session. `snowflake_cli.py` is an optional SQL transport
with compatibility adapters, not the application storage layer.

The ingestion role has SELECT/INSERT on raw observations and SELECT/INSERT/UPDATE
on source runs. CORE writing, UI, network, Cortex and deployment permissions need
separate grants. Standard tables do not enforce application-ID uniqueness;
this is a single-writer path, not concurrent exactly-once processing.

## Verification and Remaining Work

Real GLEIF evidence, source-run logging, key-pair session reuse and bundle replay
have been verified in the existing DEV account. Full fresh-account provisioning
has not been independently live-tested. Setup tests do not claim cloud deployment.
See [the integration register](../docs/source-integration-status.md).

The Streamlit manifest and app are scaffolding, not a deployed persistent worker,
authenticated reviewer UI, Cortex service or Task/dbt pipeline. The CLI manifest
does not automatically consume `.env`; UI deployment needs explicit parameter mapping.

Before multi-user deployment, implement tenant-bound identities, row access,
retention/licensing controls and safe review actions. Do not grant the UI or AI
tools raw-response access. See [Portable Deployment](../docs/portable-deployment.md)
and [the delivery blueprint](../docs/snowflake-delivery-blueprint.md).
