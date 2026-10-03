# Shared deployment readiness

## Step 1: read-only account preflight

Checked on 2026-10-03 using the existing `trust_signal_dev` CLI connection.
This report describes metadata visible to `TRUST_SIGNAL_DEPLOYER`, not an
account-wide administrator audit. No cloud objects, grants, billing settings,
task states, warehouse settings, or Cortex settings were changed. No model
inference or workflow execution was performed.

The repeatable worksheet is
[`ACCOUNT_PREFLIGHT.sql`](../snowflake/tasks/ACCOUNT_PREFLIGHT.sql).
In Snowsight, select the existing deployment role and run statements individually.
For another installation, review and replace the DEV identifiers before running.
The existing [`VERIFY_DEPLOYMENT.sql`](../snowflake/tasks/VERIFY_DEPLOYMENT.sql)
remains the separate workflow/data verification worksheet.

## Observed baseline

| Check | Live observation | Readiness |
| --- | --- | --- |
| Connection | Existing CLI connection authenticated | Passed |
| Region | `AZURE_CENTRALINDIA` | Confirmed; AI feature availability still needs checking |
| Database | `TRUST_SIGNAL_DEV` | Present |
| Active role | `TRUST_SIGNAL_DEPLOYER` | Separate from runtime owner |
| Runtime owner | `TRUST_SIGNAL_ORCHESTRATOR` owns tasks and procedures | Full role inheritance/authorization audit pending |
| Procedures | Five workflow procedures present, none attached to an EAI | Restricted deployment remains |
| Tasks | Ten present; root suspended; nine children/finalizer started | Schedule remains safely inactive |
| Root configuration | One-minute schedule, `NO_OVERLAP` | Do not resume yet |
| GLEIF network rule | One-entry `HOST_PORT`, `EGRESS` rule present | Exact host list not inspected in this preflight |
| Integrations | Only local-application OAuth visible | No EAI visible; administrator inventory pending |
| Warehouse | Suspended, X-Small, one cluster, auto-suspend 60 seconds, auto-resume true | Basic idle controls present |
| Warehouse resource monitor | None attached | Cost guardrail missing |
| Resource monitors | None visible to deployment role | Administrator inventory pending |
| Query acceleration | Enabled, maximum scale factor 8 | Review before live workload |
| Cortex cross-region | `ANY_REGION`, account-level setting | Data-residency approval required before inference |
| Cortex model allowlist | Effective value `ALL` | Model governance review pending |
| Cortex Analyst | Parameter enabled | Not proof of privileges, entitlement, or a working service |
| Cortex Code estimated limits | CLI, desktop, and Snowsight values `-1` | No configured per-user estimated limits shown; review separately from application AI costs |
| Task notifications | Root has no error or success integration | Operational alerting pending |

Metadata settings are not proof that an AI request can succeed. No model call,
Search service, Agent, or paid-account eligibility was tested here.

## Outstanding account decisions

1. The user confirmed in this session that the account is still a trial. This is
   owner-reported confirmation, not an independently queried billing result.
   Edition, trial expiry, remaining credits, and hackathon terms still need review.
   The earlier deployment recorded error 509009 when creating an EAI; no new
   CREATE was attempted. In-Snowflake live external access is blocked on this trial.
2. Choose the deployment path: eligible in-Snowflake external access, or an
   external ingestion worker while retaining Snowflake storage/workflow services.
   The external-worker path still needs runtime wiring; it is not a configuration
   switch for the existing failure handler.
3. Approve a credit budget, alert recipients, warehouse thresholds, serverless/AI
   monitoring, and whether query acceleration is justified for this DEV workload.
4. Approve inference geography and allowed models before sending case evidence
   to Cortex. `ANY_REGION` permits processing outside the account's home region.
5. An authorized administrator should repeat integration/monitor visibility
   checks, review direct and inherited privileges, and confirm package policies
   and feature availability. Do not grant ACCOUNTADMIN to runtime roles.

Snowflake documents that external network access is unavailable on trial accounts.
Adding a credit card can enable trial AI, but does not convert the trial to a paid
account or remove the external-network limitation. Any upgrade requires explicit
account-owner approval; do not add payment information as a preflight action.
See [trial account limitations](https://docs.snowflake.com/en/user-guide/admin-trial-account).

Cross-region inference transmits the inference payload transiently to a processing
region; stored customer data remains in the account region. See
[cross-region inference](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cross-region-inference).

## Next step: reviewed security and cost configuration

Prepare proposed SQL only after account capability, budget, and residency decisions
are recorded. Review the impact on other workloads before changing account-wide
parameters. Resource monitors do not cover all serverless/AI costs; add supported
budgets and usage monitoring rather than claiming a universal hard cap.

Then, on an eligible account, provision the narrow GLEIF integration, regenerate
the versioned deployment bundle without the external-access fallback, upload and
replace the live identity procedure, and execute a fresh isolated smoke request.
Keep the root suspended throughout. Granting an EAI alone cannot replace the
deployed `identity_unavailable` handler. Follow the existing
[initialization guide](snowflake-initialization.md), rather than maintaining a
second provisioning path in manual worksheets.

Step 1 is partially complete: the live deployment baseline is inspected and trial
status is user-confirmed. Edition, administrator visibility, deployment-path
approval, budget, and inference geography remain open. Do not mark live deployment
ready or retry EAI creation on the unchanged trial account.
