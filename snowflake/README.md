# Snowflake Foundation

`migrations/V001__foundation.sql` creates the first raw, core, operations, and serving schemas plus append-oriented case, evidence, assessment, reviewer-action, and source-run tables.

## Apply in development

1. Select the intended development account, role, warehouse, and database in Snowflake CLI or Snowsight.
2. Review the migration and data-retention requirements for the source data you intend to store.
3. Run `migrations/V001__foundation.sql` with the development database as the current database.
4. Confirm the four `TRUST_SIGNAL_*` schemas and tables exist before wiring application writes.

This migration does not create a database, warehouse, users, roles, grants, network integrations, secrets, Cortex objects, or production policies. It has not been applied to an account from this repository. Snowflake standard tables do not enforce these application identifiers as unique; idempotency must be implemented by the writer and verified with tests.

`TENANT_ID` on case-scoped records must be assigned from authenticated server-side context, never accepted from an untrusted browser request. The local starter has no authentication or tenant isolation and is not suitable for multi-user deployment.

Raw payload storage is intentionally separated from core findings. Before retaining any source response, configure permitted fields, source-specific retention, access roles, and any jurisdictional deletion obligations.
