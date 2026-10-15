# Verification history

This ledger preserves dated evidence that still matters. It is not a current
availability report. Current product state lives in [status](../status.md), and
remaining acceptance work lives in the [backlog](../backlog/README.md).

## 2026-10-15 — independent GLEIF connector verification

The shared `GleifAdapter` was called directly, without Streamlit, the case graph,
Snowflake or Google Cloud. Local GLEIF connector/collection tests passed 10 tests;
connector-to-ingestion/identity boundary tests passed 21 tests; the wider source
and ingestion selection passed 80 tests.

Fresh public API inputs were `Microsoft Corporation` and
`INR2EJN1ERAN0W5ZP974`. Name search returned four explicit candidates with complete
bounded coverage and no limitations; it did not select an identity. Its response
hash was `sha256:d743b880f8d33a0cff46ed67adbaab1157cc35158f901e9a04f3bdb6c59b69ec`.
Exact LEI lookup returned `MICROSOFT CORPORATION`, `US-WA`, `ACTIVE`, `ISSUED`,
with response hash
`sha256:a7dc24292fc9f97ce9962c628b1c2aa0608fb22bd92233e5e92637a90afa01e4`.

This establishes fresh connector HTTP and normalization only. No observation or
source-run store was supplied, so the result is not durable evidence and was not
released into a case. Current UI integration and the Google provider remain pending.

A second fresh run passed both operations through `SourceRegistry` and
`IngestionPipeline` with in-memory observation/run stores. It released four name
candidates and one exact record only after verified test receipts, and completed
two local run lifecycles. The run IDs and observations existed only in that process;
this verifies injectable boundaries, not durable persistence or replay.

## 2026-10-15 — documentation consolidation

The repository documentation was reorganized around one owner per topic. Obsolete
roadmaps, duplicated architecture narratives, trial plans and repeated status
reports were removed. Their still-valid facts were retained here or in the current
product, architecture, deployment and operations owners. This change did not
recheck any cloud account, live source, schedule, model or production deployment.

The current checkout passed 367 tests, Ruff, the repository Markdown-link check,
the 51-task backlog/manifest integrity checks and `git diff --check`. These are
local results over a dirty working tree containing other maintainer changes; they
do not establish a publishable commit or any live/cloud behavior.

## 2026-10-07 — TS-030 documentation reconciliation

The then-current README and implementation-status claims were compared with code.
The locked suite passed 366 tests and Ruff passed. Documentation links were also
checked. This evidence was local and unpublished at that time; it did not prove a
live source, cloud install, end-to-end provider profile or production readiness.

## 2026-10-05 — accepted implementation baseline

Commit `0950e569c1f627521f288e79a84c4754829d48db` was verified in the working
checkout and an isolated archive of that exact commit. Both passed 365 tests;
Ruff and the reviewed secret scan passed. The commit was confirmed on remote
`master`, and TS-001 / GitHub issue #2 was closed. Generated deployment plans and
ignored private outputs were excluded from the baseline claim.

## 2026-10-04 — bounded Snowflake trial hardening

The project applied and read back a daily one-credit resource monitor for
`TRUST_SIGNAL_PIPELINE_WH`, retained its X-Small/one-cluster/60-second idle
settings, disabled query acceleration and left `TS_CLAIM` suspended. This was a
warehouse guardrail, not an account-wide budget or verified notification delivery.

Targeted access hardening moved selected PUBLIC grants to an operator role and
cleared the ingestion service user's default secondary roles. Fresh service-session
checks preserved required RAW/OPS reads and rejected access to two extra warehouses.
`ML_USER` and `DATA_METRIC_USER` remained PUBLIC because the account rejected their
revocation. This proves the selected controls only, not complete tenant isolation.

A post-hardening GLEIF ingestion completed as run
`run_178895f6ce1049faafc2c14d72a9f308`, persisted observation
`observation_de0558f2b9455d8ca1665e41a26d0ea4`, and verified raw response,
payload and terminal source-run history. The root task remained suspended.

## 2026-10-03 — source retrieval and evidence readback

Source-specific checks exercised GLEIF identity, Norway registry data, UN/OFAC/
UK/EU sanctions, an Australia captured workbook, World Bank/FCA/Gazette legal
metadata and a captured GDELT response. Stored bytes, SHA-256 provenance and OPS
source-run records were read back where the connector supported persistence.
Captured replay differs from fresh HTTP, fixtures are synthetic, and an empty or
successful query never establishes universal coverage or claim truth.

The checks did not establish article-body rights, beneficial ownership, legal
finality, production source reliability or a complete multi-specialist case.
Connector-specific current limits remain in the [source catalog](../sources/catalog.md).

## 2026-10-03 — restricted Snowflake workflow deployment

The `trust_signal_dev` account compiled five Python procedures and created a
ten-task graph in `TRUST_SIGNAL_DEV.TRUST_SIGNAL_OPS`. The root `TS_CLAIM` task
remained suspended with `NO_OVERLAP`. Snowflake rejected the external access
integration with error 509009 because the trial account did not support external
access, so the deployed identity procedure recorded `identity_unavailable`.

One request (`workflow_smoke_microsoft_v1`) ran claim, identity and finalization.
Specialists were correctly skipped after identity failure; aggregation, validation
and assessment did not run. The saved result was `completed_with_gaps`,
`not_scored_identity_lookup_failed`, and `analyst_review`. Local verification at
that point passed 192 tests and Ruff. This was restricted-path behavior, not a
live-source or production deployment.

The bundle was `trust_signal_eb3251b25faa8199.zip` with SHA-256
`eb3251b25faa81997640869d0ecba22abb2241ece075cffa83e1d497964d1dc1`.
Inspect retained environments with
`snow sql --connection trust_signal_dev --filename snowflake/tasks/VERIFY_DEPLOYMENT.sql`;
do not resume a schedule without current authorization and readiness checks.
