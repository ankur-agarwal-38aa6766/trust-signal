# Snowflake initialization

Every installation needs the same reviewed schemas, tables, views, permissions,
code stage, Python procedures and task graph. Full initialization generates these
from versioned repository sources; it is separate from runtime application startup.
No Snowflake connection is opened when generating a plan.

## Generate a complete plan

From the repository root, after installing the Snowflake extra:

```bash
uv run --locked --extra snowflake python -m trust_signal.persistence.initialize \
  --database YOUR_TRUST_SIGNAL_DEV \
  --warehouse YOUR_PIPELINE_WH \
  --workflow-role YOUR_WORKFLOW_ROLE \
  --operator-user YOUR_ADMIN_USER \
  --without-external-access \
  --output-dir snowflake/build/installation-v1
```

Replace the uppercase identifiers with your installation's names. `--operator-user`
is optional and must refer to an existing administrator/operator, not an application
or analyst user. The default administrator role is ACCOUNTADMIN; select another
authorized role with `--admin-role`. That role needs provisioning and grant
permissions plus visibility/control of the existing task graph. Runtime tasks run
as the separate workflow role, never as ACCOUNTADMIN.

The current DEV account requires `--without-external-access` because Snowflake
rejected external access on its trial. This deploys an explicit failed-lookup
handler, not a live-source pipeline. For an approved account, omit the flag: the
plan includes GLEIF-only network provisioning and attaches it only to identity.
The EAI is named `<workflow-role>_GLEIF_EAI` to avoid sharing unrelated integrations.
Review existing integration/rule definitions before reuse; IF NOT EXISTS does not
reconcile configuration drift or narrow an existing rule.

## Include the application identity

Configure your private `.env` and generate encrypted keys using the existing
[quickstart](../README.md#try-in-your-snowflake-account). Add these options to the
initializer command to include the ingestion service user and grants:

```bash
--ingestion-env-file .env --public-key-file .secrets/snowflake_key.pub
```

The configured database and warehouse must match the initializer's target. The
ingestion role must differ from the workflow role. The public key must match the
application's private key. Existing keys/users are not overwritten; existing
user configuration must be reviewed. Only the public key enters the SQL bundle;
private keys, passwords, `.env` contents and API tokens do not.

## Review and apply

Review the generated SQL, `manifest.json`, selected account connection and cloud
cost implications before applying. The manifest contains ordered files, migration
checksums and artifact hashes. Database/warehouse names are explicit; the CLI
connection determines the account. Never reuse another person's connection or
bundle without reviewing its targets.

```bash
sh snowflake/build/installation-v1/apply.sh YOUR_ADMIN_CONNECTION
```

This requires Snowflake CLI and is the explicit cloud-changing step. The script
executes each SQL file separately under the selected administrator role, stops on
the first error and does not run sample cases or enable any task. It supports SQL
PUT for the Python ZIP, so applying only DDL in Snowsight is not a complete install.
Keep the generated bundle at its original location until PUT completes because
`upload.sql` references the local bundle's absolute path.

Execution order:

1. Database, initially suspended XSMALL warehouse, OPS schema and migration ledger.
2. Suspend the root if present; refuse deployment while graph runs remain active or scheduled.
3. All reviewed schema migrations, in numeric version order.
4. Optional key-pair ingestion identity, then optional approved GLEIF integration.
5. Dedicated workflow role and scoped grants; repeat the graph guard before changing runtime code.
6. Package/privilege preflight, code upload, five procedures and ten suspended tasks.
7. Read-only inventory and migration-history inspection.

The warehouse may resume for initialization queries and incur compute costs.
Existing warehouse configuration is not changed. The root and child tasks all
remain suspended after installation. Procedure/task replacement can change task
object IDs; inspect grants and task history after redeployment.

## Query ownership

| Resource | Canonical source |
| --- | --- |
| Schemas, tables, views, schema changes | `snowflake/migrations/V001__*.sql` through V007 and future migrations |
| Migration ledger | `snowflake/bootstrap/MIGRATION_HISTORY.sql` |
| Database/warehouse and upload SQL | `snowflake/bootstrap/*.sql.template` |
| Approved GLEIF integration | `snowflake/integrations/GLEIF.sql.template` |
| Migration checksum execution wrapper | `snowflake/bootstrap/APPLY_MIGRATION.sql.template` |
| Service identity and scoped role grants | `snowflake/security/*.sql.template` |
| Five procedures and their SQL template | `snowflake/procedures/WORKFLOW.json` and `WORKFLOW_PROCEDURE.sql.template` |
| Complete graph, task SQL and activation controls | `snowflake/tasks/WORKFLOW_GRAPH.json` and `*.sql.template` |
| Preflight and inventory queries | `snowflake/verification/*.sql.template` |
| Smoke case and inspection examples | `snowflake/tasks/` |

The setup entrypoint is `snowflake/setup/initialize.sh`. Python validates
configuration and renders these versioned resources; the canonical SQL is no
longer embedded in the setup/workflow generators. Generated installation bundles
live in `snowflake/build/`, which is Git ignored because bundles contain
account-specific names, public keys, local upload paths and code ZIPs. All source
definitions needed to regenerate them are versioned under `snowflake/`.
`outputs/` remains available for test results and collected evidence; no installer
depends on its historical setup bundles. Do not maintain a second set of deployment queries
in notebooks or manual account-specific scripts. The deployment report records
what happened in one account, not how to provision the next one.

## Re-runs and upgrades

Generate each release into a fresh output directory. The initializer refuses to
overwrite a nonempty directory. Apply installations one at a time: standard tables
do not provide a unique migration lock.

`OPS.SCHEMA_MIGRATIONS` records version, filename, SHA-256, time, user and role.
Matching applied versions are skipped. Changed checksums, changed filenames or
duplicate history rows fail the migration. Add a new numbered migration for
schema changes; do not modify an applied migration. The legacy ingestion-only
setup shares migration validation but does not write this ledger.

Existing installations without a ledger are adopted by running the current
idempotent migrations once. Review the actual schemas first: this is not a schema
drift reconciler. DDL can partially commit; if a migration fails, inspect and
reconcile partial changes before re-running it. History is recorded only after
that migration's statements succeed. Never delete history to bypass a conflict.

Suspending the root does not cancel active descendants. The initializer checks
[CURRENT_TASK_GRAPHS](https://docs.snowflake.com/en/sql-reference/functions/current_task_graphs)
before migrating and before replacing runtime code. Prevent other operators from
starting a graph during deployment; this is an operational single-deployer rule,
not an account-wide distributed lock.

## Activation and scope

After verifying objects and account capabilities, separately review/apply
`workflow/enable_children.sql`, queue a new isolated smoke request, and execute
`workflow/execute_once.sql`. Enable `workflow/start_schedule.sql` only after the
live-source gates are closed. See [workflow orchestration](snowflake-orchestration.md).

An installation is not a new tenant: do not recreate all database objects for each
application user. Tenant provisioning and authorization are a separate workflow;
production tenant isolation, authenticated intake and analyst grants remain pending.
The initializer provisions implemented backend resources, not the future UI,
Cortex services or unimplemented specialist/scoring capabilities.

Offline generation, SQL statement boundaries, ordering, checksum guards and
service-key integration are tested. This new complete initializer has not yet been
executed against a clean Snowflake account; the earlier DEV deployment only
verified the restricted workflow path, as recorded in its deployment report.
