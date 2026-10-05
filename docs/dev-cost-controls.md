# DEV warehouse cost controls

## Scope and approved configuration

Account: existing DEV trial, with ten remaining days reported by the user.
Administrator metadata inspection on 2026-10-04 confirmed no existing resource
monitors. The project warehouse was idle and suspended. Remaining trial balance
is still unknown; a daily quota is not derived from the days remaining and does
not guarantee that credits will last through the trial.

The reviewed SQL is
[`DEV_COST_GUARDRAILS.sql`](../snowflake/operations/DEV_COST_GUARDRAILS.sql).
It is an explicitly approved operational change, separate from initialization
and application runtime. Do not run it as part of startup.

| Control | Applied value |
| --- | --- |
| Monitor | TRUST_SIGNAL_DEV_DAILY_RM |
| Warehouse assignment | TRUST_SIGNAL_PIPELINE_WH only |
| Credit quota | 1 Snowflake credit per day |
| Notifications | 50% and 80% |
| Suspension | 100%, graceful rather than immediate |
| Query acceleration | Disabled |
| Existing warehouse size/clusters | Retain X-Small, one cluster |
| Existing auto-suspend | Retain 60 seconds |
| Existing auto-resume | Retain enabled; quota exhaustion prevents resumption until reset |
| Task schedule | Leave TS_CLAIM suspended |

Daily monitor usage resets at 00:00 UTC, or 05:30 Asia/Kolkata. The first
interval may be shorter than a full day. Graceful suspension lets running
statements complete, so actual consumption can exceed the threshold. Subsequent
pipeline statements may then fail; preserve run IDs and reconcile writes before
retrying. It is not a transaction-wide graceful stop or an exact spending cap.

Resource monitors do not control all serverless/AI costs or retained-storage
costs. No Cortex call or scheduled workload is authorized by this configuration.
See [resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors)
and [monitor SQL](https://docs.snowflake.com/en/sql-reference/sql/create-resource-monitor).

## Application and verification

Apply only after quota approval using the existing administrator connection:

```bash
snow sql --connection trust_signal_dev --role ACCOUNTADMIN \
  --filename snowflake/operations/DEV_COST_GUARDRAILS.sql
```

The script intentionally uses CREATE without OR REPLACE or IF NOT EXISTS: reruns
must not silently reset/reuse an existing budget. DDL statements commit separately.
If creation succeeds but warehouse assignment fails, inspect both objects before
continuing; do not blindly recreate the monitor.

Verification requires the monitor quota/frequency/actions and warehouse assignment
to match, query acceleration to be disabled, existing idle controls unchanged,
and the root task still suspended. Do not exhaust the quota to test suspension.

## Notification delivery

NOTIFY triggers alone are not verified email delivery. Account administrators
must enable resource-monitor notifications in their Snowsight preferences and
have a verified email for email delivery. Preferences require the web interface.
No email address, notification preference, or additional recipient is modified
by this SQL. Delivery remains pending until enabled and observed; do not claim
operational alerts are complete merely because the monitor exists.

The user subsequently confirmed enabling resource-monitor notifications in
Snowsight. This is user-reported preference confirmation, not verified delivery
or an independently checked email-verification result.

## Recovery and rollback

At quota exhaustion, stop manual work and wait for the daily reset. A revised
quota requires explicit owner approval; do not remove the guardrail to bypass it.
Investigate the saved ingestion/source-run history before replaying failed work.

The previous warehouse had no monitor and query acceleration enabled. Restoring
either setting requires a separate reviewed operation; do not automatically
detach the monitor on errors. Other warehouses and account-wide Cortex routing,
permissions, billing, and schedule settings remain outside this change.

## Status

Applied on 2026-10-04 after explicit tool approval, using ACCOUNTADMIN only for
the reviewed operational statements. Live SHOW results confirmed:

- `TRUST_SIGNAL_DEV_DAILY_RM`: warehouse level, quota 1.00, DAILY, notify 50%/80%,
  suspend 100%, no immediate-suspension trigger.
- Monitor assigned to `TRUST_SIGNAL_PIPELINE_WH`; query acceleration false.
- Warehouse remains suspended, X-Small, one cluster, auto-suspend 60 seconds,
  auto-resume true; no warehouse workload was launched by this script.
- `TS_CLAIM` remains suspended with NO_OVERLAP.

The monitor initially reported used credits 0.00 and remaining quota 1.00. These
are monitor-period values, not the account's remaining trial balance. No explicit
extra notification users were configured, and notification delivery was not
tested. No quota-exhaustion test was performed.

Remaining trial balance, verified notification delivery, full effective-access
hardening, and Cortex budgets remain separate open items. Billing, data,
runtime roles, account-wide Cortex settings, and recurring task schedules were
not changed.

Subsequent access review found PUBLIC-inherited access to other unmonitored
warehouses and broader AI privileges. The project monitor is not a complete
service-user compute boundary. See [ingestion access review](ingestion-access-review.md).
