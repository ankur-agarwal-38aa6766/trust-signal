# Snowflake Foundation

The [application connection guide](../docs/application-connection.md) documents
the verified reusable Python session, dedicated DEV service identity, key storage,
runtime grants, health check and application-mode ingestion commands.

`migrations/V001__foundation.sql` creates the first raw, core, operations, and serving schemas plus append-oriented case, evidence, assessment, reviewer-action, and source-run tables. `migrations/V002__case_requests_and_serving.sql` adds durable intake requests, source configuration, scoring-policy storage, and analyst-facing views.

## Apply in development

1. Select the intended development account, role, warehouse, and database in Snowflake CLI or Snowsight.
2. Review the migration and data-retention requirements for the source data you intend to store.
3. Use `bootstrap/ACCOUNT_SETUP.sql.template` as a reviewed, account-admin-only starting point for a database, warehouses, and roles. Replace its placeholders locally; do not execute it unchanged.
4. Run `migrations/V001__foundation.sql`, then `migrations/V002__case_requests_and_serving.sql`, with the development database as the current database.
5. Confirm the four `TRUST_SIGNAL_*` schemas, serving views, and tables exist before wiring application writes.

The migration files do not create a database, users, grants, network integrations, secrets, Cortex objects, or production policies. The bootstrap template creates only a database, warehouses, and empty roles. V003 has been applied to the user's DEV account; V001/V002 have not been verified in full. Snowflake standard tables do not enforce these application identifiers as unique; idempotency must be implemented by the writer and verified with tests.

`TENANT_ID` on case-scoped records must be assigned from authenticated server-side context, never accepted from an untrusted browser request. The local starter has no authentication or tenant isolation and is not suitable for multi-user deployment.

Raw payload storage is intentionally separated from core findings. Before retaining any source response, configure permitted fields, source-specific retention, access roles, and any jurisdictional deletion obligations.

## Verified raw-evidence path

The `TRUST_SIGNAL_DEV.TRUST_SIGNAL_RAW.SOURCE_OBSERVATIONS` table has been created
in the user's DEV account. The `trust_signal_dev` CLI connection uses local OAuth,
the deployer role, and `TRUST_SIGNAL_PIPELINE_WH`. A real Microsoft GLEIF observation
has been automatically inserted and read back, and replay of the original saved
observation was verified without an additional row. This verifies the raw table and
storage adapter only; it does not mean V001/V002 were applied in full.

See the [source integration register](../docs/source-integration-status.md) for the
commands and captured load receipt. The remaining migration objects, connector roles,
and case workflow persistence still need implementation/validation.

`migrations/V003__source_run_tracking.sql` has separately created
`TRUST_SIGNAL_DEV.TRUST_SIGNAL_OPS.SOURCE_RUNS`. The automated GLEIF command now
uses this table to track fetch-to-storage execution. See the integration register
for the inspection query, failure semantics and remaining durability limitations.

## Streamlit deployment

`migrations/V004__raw_response_retention.sql` adds exact JSON/XML body retention
for the [shared ingestion pipeline](../docs/source-ingestion.md). Apply it before
using the strengthened observation writer, including the existing GLEIF loader.

`snowflake.yml` declares a warehouse-runtime Streamlit application whose source is `app/streamlit_app.py`. It is a thin analyst UI: it queues a case request and reads serving views. The LangGraph worker owns request claiming, source fetches, evidence persistence, scoring, and status changes.

Set the target database, warehouse, schema, and app name through the project environment before deployment. Deploy from a reviewed commit with the Snowflake CLI after confirming the connection, privileges, and [Streamlit project-definition requirements](https://docs.snowflake.com/en/developer-guide/snowflake-cli/streamlit-apps/manage-apps/initialize-app). The account configuration and execution checklist are in [the Snowflake delivery blueprint](../docs/snowflake-delivery-blueprint.md).
