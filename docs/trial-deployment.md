# Deployment on the existing trial account

## Decision and scope

On 2026-10-03 the user selected continued use of the existing trial account.
No upgrade, payment change, external-access integration, or recurring schedule
is required for the first external ingestion demonstration.

```text
Manual invocation on the developer machine
    -> shared source registry -> official source HTTPS request
    -> key-pair Snowflake connection
    -> RAW evidence write and hash/payload readback
    -> OPS source-run completion and coverage readback
    -> verified records available to the calling component
```

Snowflake remains the evidence and audit store and executes storage queries.
The developer machine performs outbound HTTP fetching. This is an external
worker, not a Snowflake stored procedure or a hosted always-on service.
There is no second account or new cloud-hosting dependency for this DEV path.

## What remains unchanged

- Existing database, warehouse, service credentials, and source adapters.
- The Snowflake task root stays suspended; do not use it to run live fetching.
- Companies House stays paused, and licensed court/news access remains gated.
- No fixtures replace unavailable live evidence.
- No new multi-tenant or production-readiness claims.
- Cortex stays out of the ingestion test until entitlement, inference geography,
  permissions, and usage budget have been approved and verified separately.

Trial accounts cannot use external network access. Self-service trial AI access
is separately disabled by default until payment details are added. Do not add a
credit card or upgrade as part of this runbook. See
[Snowflake trial limitations](https://docs.snowflake.com/en/user-guide/admin-trial-account).

## Step 2: security and cost readiness

Connection verification during this work session passed using the existing
key-pair service identity: `TRUST_SIGNAL_INGEST_SVC`, role
`TRUST_SIGNAL_INGESTOR`, database `TRUST_SIGNAL_DEV`, warehouse
`TRUST_SIGNAL_PIPELINE_WH`. Two context queries returned the same session and
`session_reused: true`. No source fetch, data write, or model call was part of
this check. The initial sandboxed attempt failed; the approved network-enabled
retry succeeded. Cost controls and the complete privilege review remain pending.

1. Verify the existing `.env` configuration without printing it. Keep the private
   key and passphrase files private, separately stored, and outside Git.
2. Run the existing service-connection health check. Confirm the expected service
   user, ingestion role, database, warehouse, and reuse of the same session.
3. Review the ingestion role's direct and inherited grants, including response
   chunk-table access. It must not need ACCOUNTADMIN, task ownership, or arbitrary
   CORE writes for source ingestion.
4. In Snowsight, confirm trial expiry and remaining credits. Choose a daily credit
   allowance and notification recipient before preparing/applying a resource
   monitor. Do not assume an arbitrary quota is acceptable.
5. Review whether query acceleration should be disabled for this small DEV
   warehouse. Keep X-Small, one cluster, and short auto-suspend unless there is a
   measured reason to change them. Warehouse use and retained storage consume
   trial credits even though no account upgrade is performed.
6. Keep execution manual and single-writer. Do not install cron, launch a daemon,
   resume the task schedule, or retry failed writes blindly.

The current worksheet/report flags no warehouse resource monitor and enabled
query acceleration in the original baseline. These were subsequently changed
with approval: [DEV cost controls](dev-cost-controls.md) records the applied
1-credit daily monitor and disabled acceleration. Resource monitors do not cover
all serverless or AI spending; those need separately supported usage/budget
controls. See [resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors).

## Step 3: bounded live ingestion

The one-source external ingestion smoke has now passed its application checks.
See [2026-10-04 verification](trial-smoke-2026-10-04.md) for run IDs, receipts,
the scoped grant review, and remaining guardrails. Do not repeat it merely to
inspect the existing result; use the saved run/observation IDs in Snowsight.

Run from the repository root using the already-installed Snowflake extra:

```bash
.venv/bin/python -m trust_signal.persistence.connection --env-file .env

.venv/bin/python -m trust_signal.ingestion.pipeline \
  --requests examples/microsoft_identity.json \
  --env-file .env \
  --output outputs/live/trial-microsoft-identity.json
```

The second command performs one exact-LEI lookup at GLEIF and writes real data to
Snowflake. It is the explicit live ingestion action, not a read-only health check.
Review the credit allowance first. The output may contain entity information;
keep it private and retain it for reconciliation. Do not run the broad source
expansion example as the first smoke test.

Acceptance: no error category, coverage `available`, one verified observation
receipt, a matching legal entity, and terminal source-run history. Check the
returned run ID in Snowsight. If coverage is `partial`, `failed`, or `blocked`,
preserve that status; never report a clean assessment. Source timeouts or a
storage failure must not release unverified records.

The earlier application-mode tests are recorded in
[application connection](application-connection.md) and
[source ingestion](source-ingestion.md). They are historical evidence, not proof
that this new deployment smoke has run. Record new results explicitly.

## Downstream boundary

The deployed Snowflake identity procedure still uses the unavailable handler.
It cannot consume pre-ingested evidence merely because RAW records now exist.
Connecting the external worker to durable case claims, identity decisions,
stage outputs, and the task graph requires an explicit contract and later runtime
work. Until then, use only the existing local application path for identity;
do not claim automatic Snowflake case processing.

The existing local live case command is:

```bash
.venv/bin/trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --env-file .env
```

This is a separate action after successful ingestion verification. It may perform
another source lookup. It does not complete the unfinished sanctions matching,
specialist research, evidence validation, policy scoring, or human review work.

## Later deployment

Uploading the complete repository does not change trial entitlements. Streamlit
outbound source calls also require external-access configuration; moving HTTP
fetching from a procedure into the UI is not a workaround. See
[Streamlit external access](https://docs.snowflake.com/en/developer-guide/streamlit/features/external-access).

On an eligible account, the intended Snowflake-native mapping is RAW/OPS/CORE/SERVE
tables for persistence, Snowpark procedures and Tasks for bounded case stages,
Cortex services for approved evidence-grounded AI, and Streamlit for a later UI.
Snowpark Container Services is an optional container/API runtime if region,
account capabilities, dependencies, networking, and cost justify it. Neither
hosting option implements the missing specialist or scoring logic automatically.
The existing account can be reviewed for an owner-approved upgrade later; a
second account is not inherently required.

After the manual vertical slice passes, design durable external-worker claims,
crash recovery, freshness checks, and controlled scheduling. Select hosted worker
infrastructure only with approval for any new cloud cost. On a future eligible
Snowflake account, the existing portable ingestion interfaces can also support
in-Snowflake fetching; use versioned deployment artifacts for that migration.
