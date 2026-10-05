# Ingestion access hardening

## Reviewed change

The [access review](ingestion-access-review.md) identified selected PUBLIC grants
that let a source worker inherit AI/learning access and reach warehouses outside
the project monitor. This change relocates those grants to an explicit operator
role before revoking them from PUBLIC. It also clears the service user's default
secondary roles. No ingestion table privilege is removed.

The account-specific SQL is
[`HARDEN_INGESTION_ACCESS.sql`](../snowflake/operations/HARDEN_INGESTION_ACCESS.sql).
Preflight verified that the new role does not exist, the selected grants still
belong to PUBLIC, the current administrator user is the intended human operator,
and all listed warehouses are idle/suspended.

| Resource | Change |
| --- | --- |
| TRUST_SIGNAL_PLATFORM_OPERATOR | New role, assigned only to the verified human operator |
| AI/function/agent privileges | Preserve selected grants in operator role, remove from PUBLIC |
| Cortex/Copilot database roles | Move from PUBLIC to operator role |
| DATA_METRIC_USER | PUBLIC revoke denied by this account; preserve/report residual access |
| ML_USER | Retain irrevocable PUBLIC grant; operator also has preserved copy |
| Learning role | Move from PUBLIC to operator role |
| System Streamlit/notebook warehouse | Move PUBLIC USAGE to operator role |
| System CPU/GPU compute pools | Move PUBLIC USAGE to operator role |
| Ingestion default secondary roles | Empty list |
| Ingestion role and evidence/audit grants | Unchanged |
| Sample data, repository access, metadata viewer roles | Unchanged |
| Project quota, keys, billing, task schedules | Unchanged |

The SQL targets the existing operator's actual user name. Review and substitute
that target before reuse in another account. It is not a portable initializer.
It does not grant the operator role to PUBLIC, the ingestion role, or the service
user, and does not change the human user's default primary/secondary roles.

## Account-wide impact

PUBLIC revocations affect every user who depended on these grants. Only the
verified human operator receives the replacement role in this change. Other
approved users/apps need their own explicit grants before use. To use preserved
feature access, activate the operator role or appropriate secondary roles in the
human session. This preserves privileges, not a tested CoCo or model invocation.

This is targeted hardening, not removal of all PUBLIC access or a production
tenancy boundary. Metadata/application viewer roles and sample/repository access
remain public. AI entitlement, fine-grained AI authorization and budgets remain
separate; the operator's extra compute is not covered by the project monitor.

## Apply and verify

Apply only with explicit approval:

```bash
snow sql --connection trust_signal_dev --role ACCOUNTADMIN \
  --filename snowflake/operations/HARDEN_INGESTION_ACCESS.sql
```

CREATE ROLE intentionally fails on a rerun rather than replacing/reusing an
unexpected role. Each statement can commit independently. Grants are preserved
before revocations. Inspect partial state if execution fails; do not rerun the
whole file or drop the role blindly.

Use a fresh key-pair service session for verification:

- Default secondary-role mode is empty and primary role remains ingestion.
- Learning and selected AI roles are no longer active, even under ALL.
- Selecting the two inherited warehouses is rejected without running workloads.
- Evidence/audit read probes work and CORE/admin/operator access remains denied.
- The human can activate the new role with the preserved grants.
- One small real GLEIF ingestion verifies writes and source-run completion.
- Root task remains suspended and daily warehouse quota remains assigned.

No model, destructive DDL, warehouse workload outside the project, or quota-
exhaustion test should be used to verify this change.

## Recovery

If an approved human workflow lacks a grant, grant only the required replacement
role to that approved user. Do not restore all PUBLIC grants as an automatic
fallback. If source writes fail, inspect retained run IDs and observations before
replaying. The inverse of each selected revoke restores the previous PUBLIC grant,
but any such rollback requires separate review and approval.

## Status

Initial application was approved. Operator creation, preservation of all selected
grants, assignment to the human operator, four account-privilege revocations, and
Cortex/Copilot PUBLIC-role revocations succeeded. The script then stopped on
REVOKE DATABASE ROLE SNOWFLAKE.ML_USER FROM ROLE PUBLIC with error 3103.

Read-only query history and grant inventory confirmed the exact partial state.
Snowflake documents ML_USER as an irrevocable PUBLIC database role; do not retry
that revoke or interpret it as a missing administrator grant. See
[SHOW GRANTS irrevocable roles](https://docs.snowflake.com/en/sql-reference/sql/show-grants).

The canonical script was corrected to retain ML_USER. The separate
[`COMPLETE_INGESTION_HARDENING.sql`](../snowflake/operations/COMPLETE_INGESTION_HARDENING.sql)
contains only the inspected remaining revocations and user-default change.
Do not rerun the original script. Completion and fresh-session verification are
pending, and residual built-in ML/viewer access must stay visible in the result.

The first completion attempt also stopped on DATA_METRIC_USER revocation with
error 3103 under ACCOUNTADMIN. No other completion statement had applied. This
is an observed account restriction, not a claim that every account has the same
restriction. The scripts now retain that grant too; further data-metric isolation
requires Snowflake-supported policy/capability review. Do not bypass it by
changing entitlements or misrepresenting PUBLIC as empty.

### Final verification

The corrected completion script succeeded on 2026-10-04 after approval. Learning
role, system warehouse and CPU/GPU pool grants were removed from PUBLIC, and the
service user's secondary-role default was cleared. The root remains suspended.

Fresh service-session checks passed: empty secondary-role default, Cortex and
learning membership false, required RAW/OPS reads allowed, both extra warehouse
selections rejected, and operator-role activation rejected. No workloads ran on
the extra warehouses. Required ingestion grants remain unchanged.

A post-hardening GLEIF smoke also passed: run
`run_178895f6ce1049faafc2c14d72a9f308`, observation
`observation_de0558f2b9455d8ca1665e41a26d0ea4`, coverage available, one inserted
and verified observation, no errors or limitations. The pipeline verified raw
response/payload and terminal source-run history before returning the record.
Artifact: `outputs/live/trial-microsoft-post-hardening-20261004.json`.

The human CLI session successfully activated TRUST_SIGNAL_PLATFORM_OPERATOR and
confirmed inherited CORTEX_USER membership in the SNOWFLAKE database context.
No AI inference was performed; preserved role privileges do not prove a working
CoCo/model interaction. ML_USER and DATA_METRIC_USER remain PUBLIC. Targeted
hardening passed its service checks, with those explicit exceptions; this is not
a claim of complete account/tenant isolation or all-category spending control.
