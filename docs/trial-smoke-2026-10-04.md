# Trial external ingestion verification

## Scope

Verified on 2026-10-04 (Asia/Kolkata). The user reported ten trial days remaining
and approved continued work. The remaining credit/currency balance is unknown;
ten days is not a compute allowance. No upgrade, payment change, grant change,
Cortex call, or recurring schedule was performed.

The smoke used one existing exact-LEI GLEIF request through the local worker and
the existing key-pair Snowflake service connection. Storage and verification SQL
consume trial credits. This verifies external ingestion, not Snowflake-hosted
HTTP fetching or complete case assessment.

## Permission review

The live `SHOW GRANTS TO ROLE TRUST_SIGNAL_INGESTOR` inventory showed:

| Object | Privileges |
| --- | --- |
| DEV database, RAW/OPS schemas, pipeline warehouse | USAGE |
| RAW.SOURCE_OBSERVATIONS | SELECT, INSERT |
| RAW.SOURCE_RESPONSE_CHUNKS | SELECT, INSERT |
| OPS.SOURCE_RUNS | SELECT, INSERT, UPDATE |

No granted subordinate roles, account administration, task ownership, CORE writes,
DELETE privileges, or grant options appeared in this role inventory. The role is
assigned to the ingestion service user and to SYSADMIN. SYSADMIN inheriting the
ingestion role does not give the ingestion role SYSADMIN privileges.

This is a scoped role review, not a full user/PUBLIC/secondary-role audit or
production tenant-authorization test. Chunk access was verified through metadata;
this small GLEIF response did not exercise chunked writes.

## Live result

- Source: official GLEIF LEI API, one `lookup` operation.
- LEI: `INR2EJN1ERAN0W5ZP974`.
- Run ID: `run_c4dcacd6504a44f3917a324605496d47`.
- Observation ID: `observation_36784aaa8ac654d488086c3be9542479`.
- Coverage: `available`; one normalized record released.
- Inserted observations: 1; verified observations: 1.
- Error category/stage: null; no coverage limitations reported.
- SHA-256: `4700311e580ba60955fa0ab0c63013ba1201a746fe2616372b33ae90879a9aad`.
- Artifact: `outputs/live/trial-microsoft-identity-20261004.json`, ignored by Git.

The application pipeline verified the original response, structured payload,
metadata, and source-run lifecycle before releasing records. Independent SQL
readback also confirmed:

- Run status `succeeded`, completed timestamp present, seen/accepted counts 1/1,
  coverage `available`, and no error category.
- Legal name `MICROSOFT CORPORATION` and the expected LEI in RAW.
- Stored original response SHA-256 matches `CONTENT_HASH`; chunk count 0.
- Root `TS_CLAIM` remains suspended with `NO_OVERLAP` after ingestion.

## Cost and deployment status

Before ingestion, the warehouse was suspended, X-Small, one cluster, with
auto-suspend 60 seconds and auto-resume enabled. It still had no warehouse
resource monitor, and query acceleration was enabled with maximum scale factor 8.
No settings were changed. The root task was suspended before this test.

Step 2 is partially complete: the service connection and direct role grants
passed review; a usage quota, notification recipient, full effective-access
audit, and configured cost controls remain open. Step 3's one-source external
ingestion smoke passed its pipeline checks and independent SQL readback. Neither step enables production
tenancy, Cortex, specialist agents, or the deployed live case DAG.

## Next operations

Subsequent configuration update: the approved warehouse-specific daily monitor
is now applied, and query acceleration is disabled. See
[DEV cost controls](dev-cost-controls.md) for live verification. This changes the
current warehouse baseline, not the settings used for the smoke above.
Remaining balance, notification delivery, and effective-access audit are still
open. The root schedule remains suspended.

1. Confirm remaining trial balance and agree a project warehouse credit quota.
2. Review/apply a warehouse-specific resource monitor and notification settings
   through ACCOUNTADMIN; do not grant that role to the worker.
3. Review disabling query acceleration for this small DEV workload, retaining
   X-Small/single-cluster/60-second auto-suspend. Do not alter other workloads.
4. Inspect other user/PUBLIC/secondary-role access before exposing a shared app.
5. Plan the worker-to-case-stage handoff before trying to resume the task DAG.

A proposed monitor should notify before exhaustion and use a graceful SUSPEND
threshold to avoid cancelling ingestion mid-write. Immediate suspension can
interrupt writes; any such interruption requires reconciliation. Quotas must be
chosen from the actual balance, not inferred from days remaining. Resource
monitors are not a hard cap for every cost category: serverless/AI spending needs
separate monitoring. See
[Snowflake resource monitors](https://docs.snowflake.com/en/user-guide/resource-monitors).
