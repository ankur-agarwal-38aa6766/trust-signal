# Ownership And Leadership Specialist

## Scope

The second research specialist implements bounded GLEIF accounting relationships
and Norwegian organizational roles. It does not infer beneficial owners, ownership
percentages, control, conflicts of interest or risk scores. No cloud deployment,
migrations, task definitions or UI were changed.

GLEIF Level 2 reports direct and ultimate accounting-consolidating parents, which
must not be treated as beneficial ownership. See the official
[relationship format](https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-relationship-record-rr-cdf-2-1-format).

## Flow

1. The identity gate requires a unique persisted, confirmed legal party. Name-only
   discovery or conflicting identity stops before research.
2. `OwnershipSpecialist` sends explicit requests to a replaceable `ResearchProvider`.
3. `PipelineResearchProvider` runs existing connectors through ingestion. Exact raw
   responses and verified receipts are stored in RAW; terminal source-run logging
   must succeed in OPS before records are released.
4. For an LEI, GLEIF returns the queried organization, parent/child relationships and
   reporting exceptions. The specialist checks the queried identity, relationship
   direction, endpoints, type, status and exception subject scope.
5. For Norway, a scoped confirmed registration or an explicit organization-number
   hint triggers a persisted organization lookup. Only an exact legal name/alias
   with no scope conflict allows the subsequent roles fetch. Name-only linkage stays
   pending, not confirmed.
6. Typed records and findings retain evidence, source runs and source-reported
   statuses. The aggregator receives them; the stage runner can persist and reuse
   outputs. Validation and scoring remain independent and unconfigured.

The ingestion pipeline now serializes complete source runs within each shared
instance. Parallel local specialists can share that instance without overlapping
operations on its Snowflake session. Separate pipeline instances sharing the same
session are not protected; use one pipeline per session or independent sessions.

## Component Boundaries

| Component | Responsibility |
| --- | --- |
| `resolution/confirmed.py` | Shared specialist identity gate |
| `domain/ownership.py` | Typed research results, records and coverage |
| `research/provider.py` | Portable provider protocol and persisted ingestion adapter |
| `agents/ownership.py` | Source selection, bounded normalization, attribution and findings |
| Existing workflow/aggregator | Parallel research, comparison and review routing |

Alternative cached providers implement `load(SourceRequest) -> ResearchDataset`.
They must verify persisted evidence equivalently; merely constructing the in-memory
contracts does not verify storage. There is no new normalized CORE cache in this
change. The deployed runtime still needs handler wiring and source network access.

## Preserved Distinctions

- Accounting parent and direct child are directional relationships, not inferred
  shareholding. Relationship status, periods, validity dates, registration metadata
  and corroboration level are retained, not promoted to stronger verification.
- Reporting exceptions retain source reasons/category/reference. They do not mean
  the organization has no parent, and they are not a fraud signal.
- Norway roles preserve person/organization holders, board-role flags, role/group
  codes and deregistration flags. Deregistered roles are not current appointments.
- Role holders and related entities are not independently identity-resolved or
  screened against sanctions. Their displayed names do not establish unique identity.
- Norway linkage is confirmed only by the existing scoped registration policy:
  matching identifier, issuing authority, jurisdiction and legal name/alias.
  A supplied number plus matching name alone produces pending findings with no
  confirmed `subject_id`. A country conflict blocks that linkage.
- Role findings reference both lookup and roles observations; lookup run lineage
  is retained alongside the roles run ID.
- Retrieval older than 24 hours or more than five minutes in the future is withheld.
  Retrieval freshness does not independently establish publication freshness.
- Partial pagination, unavailable sources and absent source scope remain explicit.
  A verified empty roles response is allowed; unverified emptiness is not clean evidence.
- Unknown/malformed relationship types or direction mismatches fail the dataset
  closed, rather than silently dropping a record and implying complete coverage.
- Source dates remain supplied metadata. No guessed timeline date is emitted.

## Usage

Registry and GLEIF research, using the existing Snowflake configuration:

```bash
.venv/bin/trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --ownership
```

The command performs source requests and existing RAW/OPS writes. It does not
deploy infrastructure. Add `--sanctions` to run both implemented specialists.

For a Norwegian LEI case, `--norway-organization-number <9-digit-number>` supplies
an optional registry hint. It cannot bypass name/jurisdiction checks or independently
confirm the cross-registry linkage. GLEIF's current normalized identity does not
include a Norway issuing-authority mapping, so that hint normally remains pending.
Without a Norway scope or hint, Norway roles are explicitly not applicable; that
does not assert worldwide board coverage.

Portable injection:

```python
specialist = OwnershipSpecialist(PipelineResearchProvider(pipeline))
result = run_case(request, ingestion_pipeline=pipeline,
                  specialists={"ownership": specialist})

runner = StageRunner(workflow_store, identity_handler,
                     {WorkflowStage.OWNERSHIP: specialist})
```

## Verification And Remaining Work

Tests cover direction/type/identity checks, reporting exceptions, historical statuses,
scoped Norway attribution, pending number hints, malformed evidence, source failure
isolation, freshness, CLI validation, aggregation, stage persistence/retry and shared
ingestion serialization. A read-only live GLEIF parent endpoint and reporting-exception
endpoint were checked during implementation on 2026-10-04. This is schema verification,
not an end-to-end live Snowflake run; Norway was tested with deterministic fixtures.

Remaining: cross-registry issuing-authority mapping, independent related-entity and
person resolution, bounded recursive ownership traversal, beneficial ownership from
appropriate authorized sources, related-party sanctions evaluation, wider leadership
coverage, normalized caching, and deployed runtime integration.

The initial [legal/adverse-event specialist](legal-specialist.md) is now implemented.
The next research component is the news specialist.
