# Sanctions Specialist

## Scope

The first implemented specialist in research stage 3 screens a confirmed organization
against selected sanctions snapshots. It produces explainable candidates, exclusions,
evidence references and source coverage. It does not score risk, determine legal
applicability, infer criminal guilt or authorize rejection.

Deployment/bootstrap work is independent. This implementation does not change tasks,
roles, warehouses, migrations or the deployed Snowflake runtime.

## Data Flow

1. The registry branch persists GLEIF evidence and confirms the submitted name and LEI.
   Name discovery alone stops for clarification before any specialist fetch.
2. The orchestrator passes the request and confirmed identity to `SanctionsSpecialist`.
3. `PipelineSanctionsProvider` requests each selected registry connector's snapshot.
4. The existing ingestion pipeline stores exact raw responses in Snowflake RAW,
   verifies receipts and completes the OPS source-run log before releasing records.
5. The provider validates listing contracts and their receipt/hash/source associations.
   A failed write, failed terminal log or malformed snapshot releases no listings.
6. The pure `SanctionsMatcher` compares organization names, aliases and supported
   identifiers. The specialist emits findings and a typed screening result.
7. The aggregator receives those findings. The stage runner can persist the branch
   output and reuse it on retry. Validation/scoring remain separate; cases stay unscored
   and routed to analyst review under the current policy.

Snapshots are fetched sequentially to preserve the ingestion layer's single-writer
guarantee. Independent specialists can use the orchestrator's parallel fan-out; this
component does not introduce concurrent writes on a shared Snowflake session.

## Portable Components

| Component | Responsibility | Replaceable boundary |
| --- | --- | --- |
| `domain/sanctions.py` | Typed matches, evidence, coverage and screening result | Versioned JSON contracts |
| `screening/sanctions.py` | Pure matching and retrieval freshness policy | `SanctionsMatcher` |
| `screening/providers.py` | Persisted ingestion results to verified datasets | `SanctionsProvider.load(source_id)` |
| `agents/sanctions.py` | Research orchestration and finding creation | Two-argument specialist callable |
| Existing aggregator | Deduplication, comparisons and coverage | `AggregationService` |

A cached Snowflake provider can later implement the same provider interface. There
is no new normalized CORE sanctions cache/table in this change. Pure matching is
offline-capable; the pipeline provider requires the existing source and Snowflake
connections. Custom providers must enforce equivalent persisted-evidence guarantees;
the in-memory evidence contract alone is not a database verification.

## Matching And Coverage Policy

- Exact name or alias, and fuzzy similarity at least 0.8, are candidate discovery only.
  The existing identity resolver's similarity is a heuristic, not a probability.
- Confirmation requires exact name/alias plus exact LEI, or exact registration ID
  under the same issuing authority and registry jurisdiction. A comparable conflicting
  identifier excludes a candidate. Identifier-only name conflicts require review.
- Country/address text on a sanctions list does not establish registration scope.
- Individuals, vessels and aircraft are excluded from direct organization matching.
  Unknown subject types require review rather than being silently dismissed.
- Current adapters do not populate the new authoritative identifier fields. Their
  name candidates therefore normally require analyst identity confirmation.
- Retrieval evidence older than 24 hours, or more than five minutes in the future,
  is withheld. This does not independently verify the list's publication freshness.
- Failed, blocked, empty, stale or partial snapshots never mean clean screening.
  Valid matches from other sources remain visible with `complete=false`.
- `no_candidates` is limited to the selected lists and matching policy. It is not
  proof of no sanctions exposure. Excluded candidates remain in the screening audit.
- Potential findings have no confirmed `subject_id`. Confirmed identity matching
  still does not establish legal applicability. Neither status creates a risk score.
- Source designation dates are retained as supplied strings; no guessed timeline
  date is generated. Designation is not represented as a conviction.

## Usage

Run from the repository with the existing local environment and Snowflake config:

```bash
.venv/bin/trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live \
  --sanctions --sanctions-source un_security_council_consolidated_list
```

This performs network requests and existing RAW/OPS writes, not infrastructure
deployment. Without `--sanctions`, behavior stays registry-only. Repeat
`--sanctions-source` to choose lists. With no explicit selection, screening uses UN,
OFAC SDN, UK and EU. Australia is opt-in because its workbook access has previously
been intermittent. Operational availability is evaluated at execution time.

Supported adapters:

| Source ID | Current scope |
| --- | --- |
| `un_security_council_consolidated_list` | Organization entities in UN consolidated list |
| `us_ofac_sdn` | SDN; not all OFAC non-SDN lists |
| `uk_fcdo_sanctions` | UK sanctions list |
| `eu_financial_sanctions` | EU financial sanctions, not every EU restrictive measure |
| `au_dfat_sanctions` | DFAT consolidated workbook |

Local graph injection:

```python
specialist = SanctionsSpecialist(PipelineSanctionsProvider(pipeline))
result = run_case(request, ingestion_pipeline=pipeline,
                  specialists={"sanctions": specialist})
```

Existing stage runner injection:

```python
runner = StageRunner(workflow_store, identity_handler,
                     {WorkflowStage.SANCTIONS: specialist})
```

The deployed runtime still needs explicit provider/handler wiring and approved
source network access. The stage-runner injection above does not enable cloud tasks.

## Remaining Research Work

1. Ownership/leadership enhancements: the initial specialist now implements persisted
   GLEIF relationships and Norway roles; see [its design and usage](ownership-specialist.md).
   Cross-registry authority mapping and independent related-party resolution remain.
2. Legal/adverse-event enhancements: the initial [specialist](legal-specialist.md)
   preserves source procedural labels and gated court access. Primary-document
   interpretation and verified party roles remain.
3. News specialist: entity attribution, multilingual relevance, duplicate reporting,
   provider usage rights, publication dates and official newsroom supplementation.
4. Sanctions enhancements: authoritative identifier extraction with source locators,
   directors/related-party screening, ownership-rule evaluation, transliteration policy,
   calibrated matching benchmarks and licensed coverage where needed.
5. Shared operations: normalized cache/replay provider, refresh schedules, publication
   freshness checks, cost limits, deployed specialist wiring and integration validation.

Tests cover deterministic fixtures, provenance rejection, failure isolation, identity
gating, local graph integration and persisted stage retries. They do not establish
current live source availability or deployed Snowflake execution for this specialist.
