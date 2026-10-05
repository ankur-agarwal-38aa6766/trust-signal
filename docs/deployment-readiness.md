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
2. Decision: retain this trial account for now. Source fetching will run outside
   Snowflake, initially as a manually invoked local worker using the existing
   application connection and ingestion pipeline. RAW evidence and source-run
   history stay in Snowflake. See [trial deployment](trial-deployment.md).
   Integration with the deployed task graph remains pending; this decision does
   not turn its failure handler into a live identity stage.
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

For the selected trial path, verify the external worker's existing service
connection, configure approved cost/security controls, and run one bounded GLEIF
ingestion. Keep the Snowflake root suspended. Do not provision an EAI or redeploy
the live outbound identity procedure on this account. A future eligible-account
migration can use the existing [initialization guide](snowflake-initialization.md),
rather than maintaining a second provisioning path in manual worksheets.

The external service-connection health check has now passed in this work session:
the expected ingestion identity/context was verified and the session was reused.
Only context queries ran; this is not a new ingestion smoke, role-inheritance
audit, cost-control deployment, or Cortex verification.

Update, 2026-10-04: the user reported ten trial days remaining and approved
continued work. The direct ingestion-role grant inventory was reviewed, and one
external-worker GLEIF ingestion passed pipeline storage/lifecycle verification.
See [trial smoke report](trial-smoke-2026-10-04.md). The remaining balance is
unknown; no credit quota, monitor, warehouse setting, or schedule was changed.

Subsequent update, 2026-10-04: after explicit approval, a warehouse-only daily
1-credit monitor was created and attached, and query acceleration was disabled.
Live metadata verified the quota, thresholds, assignment, retained idle controls,
and suspended task root. This supersedes the earlier warehouse-cost baseline,
not the historical ingestion result. See [DEV cost controls](dev-cost-controls.md).
Notification delivery and the full effective-access review remain pending; no
billing, data, runtime-role, Cortex-routing, or schedule changes were made.

Step 1 is partially complete: the live deployment baseline is inspected and trial
status is user-confirmed. The deployment path is selected. Edition, administrator
visibility, budget, and inference geography remain open. Do not mark live deployment
ready or retry EAI creation on the unchanged trial account.

Access review update, 2026-10-04: the service user's sole explicit role and
bounded positive/negative authorization checks were reviewed. PUBLIC learning,
warehouse, and AI access plus default ALL secondary roles create least-privilege
gaps. No grants were changed; approval is needed for remediation. See
[ingestion access review](ingestion-access-review.md). The user reported enabling
resource-monitor notifications; delivery remains unverified.

Hardening update, 2026-10-04: selected PUBLIC AI/learning/extra-compute grants were
preserved for the human operator and revoked where supported. The service default
secondary roles are empty. Fresh-session access checks and one bounded GLEIF
write/readback passed. Built-in ML_USER and DATA_METRIC_USER PUBLIC access remains
because the attempted revocations were denied. See
[hardening results](ingestion-access-hardening.md); full production isolation and
the external-worker case-stage handoff remain pending.
