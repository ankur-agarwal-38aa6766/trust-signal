# Snowflake DEV deployment

## Verified scope

Deployed on 2026-10-03 using the `trust_signal_dev` Snowflake CLI connection:

| Item | Value |
| --- | --- |
| Account identifier | SLSSBSN-BQ70973; CURRENT_ACCOUNT returned KY28701 |
| Database | TRUST_SIGNAL_DEV |
| Workflow schema | TRUST_SIGNAL_OPS |
| Warehouse | TRUST_SIGNAL_PIPELINE_WH (existing) |
| Owner role | TRUST_SIGNAL_ORCHESTRATOR |
| Procedures | 5, successfully compiled |
| Tasks | 10, successfully created |
| Root task | TS_CLAIM, suspended; NO_OVERLAP |
| Child/finalizer tasks | Enabled, with no independent schedule |
| Deployment mode | Restricted account; no external access |
| Python / Pydantic | 3.11 / 2.11.7 |

Applied V001, V002, V005 and V007 for missing foundation, intake, identity and
workflow objects. Existing RAW observations, response chunks and source runs
were preserved. Uploaded the credential-free Python ZIP to `OPS.WORKFLOW_CODE`.
The dedicated role has scoped warehouse, task, procedure, stage and data privileges;
it was granted to SYSADMIN and the deployment user. No account upgrade was performed.

Final artifacts: `outputs/workflow/deployment-20261003-restricted-v3/`.
The generation manifest remains `plan_only`; this report records actual deployment.

Bundle: `trust_signal_eb3251b25faa8199.zip`.
SHA-256: `eb3251b25faa81997640869d0ecba22abb2241ece075cffa83e1d497964d1dc1`.

## Account restriction

Snowflake rejected creation of `TRUST_SIGNAL_GLEIF_EAI` with error 509009:
`External access is not supported for trial accounts.`
The narrowly scoped `TRUST_SIGNAL_SECRETS.GLEIF_EGRESS` network rule was created,
but no external access integration was created. The deployed identity procedure
uses `identity_unavailable`, not the live GLEIF handler. It records the missing
capability instead of attempting blocked network traffic or generating a score.

## One-off verification

Request: `workflow_smoke_microsoft_v1`.
Run: `workflow_d07c9f8b717b54b1ab16b8e577e475b9`.
Graph run: `4f9c642b-a80b-4e1b-b733-ee3fdc452e89`.

- TS_CLAIM, TS_IDENTITY and TS_FINALIZE succeeded.
- The four specialist tasks were conditionally skipped, as required by identity gating.
- No aggregation, validation or assessment stage ran in this smoke test.
- Request and run were saved as `completed_with_gaps`.
- Identity status: `identity_lookup_failed`.
- Score status: `not_scored_identity_lookup_failed`.
- Disposition: `analyst_review`.
- Saved reason explicitly states that no live identity lookup was performed.
- Root remained suspended after one-off execution; there is no recurring polling.

Task query IDs: claim `01c77b37-0002-26c9-000f-aa8e0008b156`, identity
`01c77b37-0002-25a0-000f-aa8e0008a656`, finalizer
`01c77b37-0002-26fb-000f-aa8e000899de`.

Local verification: 192 tests passed; Ruff passed. Task definitions use
`AS EXECUTE IMMEDIATE $$ ... $$` so CLI statement splitting preserves scripting
blocks; see [Snowflake's EXECUTE IMMEDIATE documentation](https://docs.snowflake.com/en/sql-reference/sql/execute-immediate).

## Remaining deployment gates

1. Obtain an account that permits external access or have Snowflake enable it for the hackathon; do not upgrade billing automatically.
2. Create the approved GLEIF EAI, rebuild without `--without-external-access`, apply grants and redeploy after confirming no graph is running.
3. Run a new live-source smoke request and verify RAW provenance, identity resolution and downstream stage outputs. The existing smoke request is terminal and will not be claimed again.
4. Implement/wire specialist agents, evidence validation and approved scoring policies. Current specialist slots are placeholders, not completed investigations.
5. Verify authorization, tenant isolation and operational monitoring before exposing intake or enabling the root schedule.

Cortex services, autonomous live ingestion, the UI and a production deployment
are not part of this verified release.

## Inspect results

Run `snow sql --connection trust_signal_dev --filename snowflake/tasks/VERIFY_DEPLOYMENT.sql`.
Do not resume the root schedule until the live-source deployment gates are closed.
