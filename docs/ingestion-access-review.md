# Ingestion service access review

## Scope

Read-only DEV review on 2026-10-04. Administrative inventories used the existing
ACCOUNTADMIN connection. Bounded authorization checks used the actual key-pair
service identity in disposable sessions. No grants, user properties, credentials,
data, billing, Cortex routing, or task schedules were changed.

The reusable metadata worksheet is
[`AUDIT_INGESTION_ACCESS.sql`](../snowflake/operations/AUDIT_INGESTION_ACCESS.sql).
Raw user metadata is private; this report intentionally omits email addresses,
public-key material/fingerprints, and connection credentials.

## Findings

### Broader PUBLIC access than required

The worker is not isolated to its eleven direct ingestion-role grants. PUBLIC
also grants USE AI FUNCTIONS, SNOWFLAKE.CORTEX_USER, other Snowflake feature roles,
system compute-pool usage, and usage of SYSTEM$STREAMLIT_NOTEBOOK_WH. PUBLIC
inherits SNOWFLAKE_LEARNING_ROLE, which adds:

- USAGE and CREATE SCHEMA on SNOWFLAKE_LEARNING_DB.
- USAGE, MONITOR, and OPERATE on SNOWFLAKE_LEARNING_WH.

Both inherited warehouses have no warehouse resource monitor attached. The
project's one-credit monitor protects TRUST_SIGNAL_PIPELINE_WH, not all compute
accessible through PUBLIC. Selecting another warehouse in a disposable session
does not require a grant to the worker's named ingestion role.

This is a least-privilege and cost-boundary gap, not evidence that unauthorized
workloads or model calls occurred. Trial entitlements/model permissions still
affect whether a particular AI operation can succeed. No AI call was tested.
PUBLIC changes affect other users, potentially including human hackathon/CoCo
workflows, and require separately reviewed approval.

### Secondary roles default to ALL

The service user has DEFAULT_SECONDARY_ROLES set to ALL. There is currently only
one explicitly assigned account role, so no additional directly assigned role
was active in the tested session. Future role assignments or direct user grants
can widen effective access without a worker configuration change.

Recommend an empty default secondary-role list plus explicit session discipline
for the worker. This is defense in depth, not a way to remove PUBLIC privileges.
The disposable USE SECONDARY ROLES NONE test left the learning role active.

## Checks that passed

| Check | Observed result |
| --- | --- |
| User type | SERVICE, enabled |
| Default primary role | TRUST_SIGNAL_INGESTOR |
| Explicit user grants | Only TRUST_SIGNAL_INGESTOR; no direct object grants shown |
| Ingestor hierarchy | No subordinate account/database/application roles in its direct grant inventory |
| Evidence tables | SELECT/INSERT on observations and response chunks |
| Audit history | SELECT/INSERT/UPDATE on source runs |
| Other direct privileges | USAGE on DEV database, RAW/OPS schemas, project warehouse |
| Grant options | None on ingestion-role/user grants |
| Future grants to ingestor or PUBLIC | None returned |
| Direct PUBLIC grants on TrustSignal objects | None found |
| Service read probes | RAW observations, chunks, and OPS source runs accepted with WHERE 1=0 |
| Service CORE.CASES read probe | Rejected, errno 2003, SQLSTATE 02000; admin confirmed table exists |
| Switch to ACCOUNTADMIN, SYSADMIN, orchestrator | All rejected, errno 3013, SQLSTATE 42501 |

The ingestion role is granted upward to SYSADMIN. That does not grant SYSADMIN
downward to the ingestion service. This review did not attempt destructive DDL,
DELETE, stored-procedure execution, or new evidence writes.

## Database-role check

Use the relative database-role name in the appropriate database context. A
fully qualified argument to IS_DATABASE_ROLE_IN_SESSION returns false by design
and is not evidence of denied Cortex access. The initial fully qualified probe
was excluded from the security conclusion; a corrected probe uses:

```sql
USE DATABASE SNOWFLAKE;
SELECT IS_DATABASE_ROLE_IN_SESSION('CORTEX_USER');
```

The corrected disposable-session probe returned true for CORTEX_USER and the
learning role under both ALL and NONE secondary-role modes. Warehouse selection
also succeeded for SNOWFLAKE_LEARNING_WH and SYSTEM$STREAMLIT_NOTEBOOK_WH under
NONE. No workload ran on either warehouse and neither probe invokes a model. See
[database-role context rules](https://docs.snowflake.com/en/sql-reference/functions/is_database_role_in_session).

## Proposed remediation, not applied

1. Review a user-scoped change to the ingestion service's default secondary roles.
   Existing sessions must be closed and a fresh worker connection checked.
2. Move human learning access from PUBLIC to an approved human/operator role,
   preserving the operator's access before revoking the PUBLIC assignment.
3. Move broad AI privileges to dedicated human/AI roles, preserving approved
   hackathon tools and later agent access. Do not grant these to source ingestion.
4. Review direct PUBLIC usage of the system warehouse and compute pools. Inspect
   affected apps before changing shared grants; do not blindly revoke defaults.
5. Recheck effective role membership, warehouse reachability, evidence access,
   and negative CORE/admin probes after approved changes.

Restricting PUBLIC is account-wide. There is no assumption that a per-worker
secondary-role change creates a deny rule overriding PUBLIC. Fine-grained AI
authorization, model entitlement, and serverless budgets remain separate gates.
See [Snowflake access control](https://docs.snowflake.com/en/user-guide/security-access-control-overview).

## Status

The scoped access review is complete with findings; the least-privilege
acceptance gate is not yet passed. It is not a full audit of every built-in
database/application role or of cross-tenant authorization. Continue manual DEV
work only with the known PUBLIC exposure visible, and do not expose a multi-user
application or enable autonomous scheduling on this review alone.

Subsequent update: approved [targeted hardening](ingestion-access-hardening.md)
removed the revocable Cortex, learning, agent and extra-compute grants from PUBLIC
and cleared the service user's secondary-role default. Fresh service checks and
one post-change GLEIF ingestion passed. ML_USER and DATA_METRIC_USER revocations
were rejected and remain explicit exceptions. The original findings above record
the pre-change state, not the current selected-role exposure.
