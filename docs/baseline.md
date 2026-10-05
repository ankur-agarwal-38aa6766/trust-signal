# Implementation Baseline: 2026-10-04

This is the accepted implementation starting point for future contributors, not
a declaration that the hosted product is complete. Preserve it while extending
the system. Planned work is tracked in the [development backlog](development-backlog.md).

## Revision And Evidence

- Inspected HEAD: `cd195d76aa6ce16aae54e5aa8d7164835982cd49`.
- Scope: current working tree, including uncommitted/untracked specialist,
  validation, review and concurrent deployment changes. HEAD alone does not contain
  this complete baseline. No baseline tag or release has been created.
- Last pre-backlog full verification on 2026-10-04: 360 tests passed. Recent module
  lint passed. This does not establish a full fresh-checkout install, deployed
  specialist execution or current remote provider availability.
- [TS-001](backlog/TS-001.md) records the remaining reviewed commit/checkpoint work.
  Record the actual baseline commit/tag here after explicit approval and verification.

### Approved Master Checkpoint: 2026-10-05

The maintainer authorized committing the complete working-tree baseline to `master`.
The commit containing this section is the checkpoint; resolve its exact revision
with `git log -1 --format=%H -- docs/baseline.md`. The earlier HEAD and uncommitted
scope above describe the original inspection, not the state after this checkpoint.
Full local pytest and full lint passed before committing. Private configuration,
keys and ignored evidence/build outputs are excluded. No release tag, push,
fresh-account verification or complete hosted-product readiness is implied.
TS-001 stays open for remaining clean-checkout reproduction and maintainer acceptance.

## Implemented Components

| Stage | Existing Behavior | Reference |
| --- | --- | --- |
| Intake/identity | Typed requests, GLEIF discovery/exact lookup, deterministic confirmation and attribution gates | [Identity](entity-resolution-and-evidence.md) |
| Registry/ingestion | Independent connectors, RAW exact-response retention/readback, OPS lifecycle/coverage, serialized shared ingestion | [Ingestion](source-ingestion.md) |
| Specialist research | Sanctions, ownership/leadership, legal and news branches; portable provider injection; opt-in CLI | [Sanctions](sanctions-specialist.md), [ownership](ownership-specialist.md), [legal](legal-specialist.md), [news](news-specialist.md) |
| Aggregation | Finding grouping, duplicate evidence, potential conflicts, explicit-date timeline and coverage | [Aggregation](aggregation.md) |
| Validation | Structural/lineage/attribution/conflict checks, persisted audit outputs; no scoring eligibility | [Validation](evidence-validation.md) |
| Assessment/routing | Explicit unscored results; clarification or analyst review | `models.py`, `orchestration/stages.py` |
| Human review | Portable review service and durable development SQLite adapter; rationale, versions, idempotency, audit history, supervisor reopen | [Review](human-review.md) |

## Operating Boundaries

- Local workflow wiring and tested components are not a deployed persistent
  end-to-end product. The Snowflake runtime still lacks specialist handler wiring.
- RAW/OPS real-source ingestion has recorded DEV verification; new specialist
  workflows have not been fully live-verified against persisted Snowflake cases.
- Australia workbook capture/replay is distinct from reliable adapter HTTP.
  GDELT has rate-limit/replay boundaries. Companies House is paused and court
  ingestion remains permission-gated. See the dated [source status](source-integration-status.md).
- Identity name hits, headline mentions and related-party names are not uniquely
  confirmed legal subjects. Consolidation is not beneficial ownership.
- Structural validation does not verify claim truth, legal finality or applicability.
  No risk scoring engine, application Cortex services or automatic business actions exist.
- SQLite reviewer context is not production login/tenant authorization. Production
  Snowflake review persistence and authenticated API integration are pending.
- UI is deferred; prototypes and design documents are not a connected reviewer product.
- Deployment/security/cost work is concurrent and partially verified. Preserve it;
  read [deployment readiness](deployment-readiness.md) before cloud changes.

## Baseline Protection

No new implementation may silently weaken identity gates, provenance verification,
source rights, coverage reporting, tenant boundaries or the unscored default.
Do not erase dated historical evidence to make newer status claims look complete.
New cloud spend, account changes, paid source access and schedule activation require
explicit approval. Secrets and ignored evidence outputs stay out of commits/issues.
