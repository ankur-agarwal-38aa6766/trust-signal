# Snowflake profile

Snowflake is the first implemented adapter foundation. It provides RAW/OPS retention,
key-pair sessions, identity snapshots, workflow repositories, five procedures and a
ten-task graph. Full specialist execution, production review and a complete fresh
installation are still pending; see [status](../status.md).

## Installation paths

Use [portable configuration](portable.md) for private account/service settings and
keys. Choose one installation path:

- Ingestion-only: `trust_signal.persistence.setup` generates database/warehouse,
  schema migrations and restricted ingestion identity/grants.
- Complete backend: [initialization](../operations/snowflake-initialization.md)
  adds migration checksums, workflow grants/code/procedures/tasks and inventory.

Generation opens no connection. Review target account, object ownership, credentials,
costs and partial-DDL behavior before explicit administrator apply. Runtime identities
do not administer the account. Keep generated bundles in ignored `snowflake/build/`.

## Execution and evidence

[Application connection](../operations/application-connection.md) owns session/rotation
instructions; [ingestion](../components/ingestion.md) owns source requests, retention
and readback. Shared source refresh is distinct from the case DAG.
[Workflow operations](../operations/snowflake-workflows.md) owns native stage mapping,
deployment, requeue and schedule controls. Do not run a nested full LangGraph inside
every native stage.

The selected shared UI stays in [ui/](../../ui/README.md). Its old Snowflake-specific
copy and deployment manifest are removed. Hosting and durable UI connection require
their own reviewed integration; there is no current hosted deployment recipe.

Cortex extraction, Search, Agent and analytical tools remain optional future
integrations under TS-023/024. They need separate model/geography/access/evaluation
evidence and do not replace required branch execution, scoring policy or review.

[Readiness](readiness.md) owns activation gates. The old restricted-account deployment
is dated evidence in [history](../verification/history.md), not the prescribed topology.
