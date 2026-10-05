# Legal And Adverse-Event Specialist

## Scope

The third implemented research specialist discovers reviewable candidates from
official debarment, regulator, corporate insolvency and published-court metadata.
It does not determine guilt, legal applicability, adverse outcomes or risk scores.
Deployment work, Snowflake migrations/tasks and the UI are unchanged.

## Data Flow

1. The shared identity gate checks the request against a unique, persisted confirmed
   party. Unconfirmed name discovery cannot trigger specialist research.
2. `LegalSpecialist` selects explicit source requests. Snapshot sources are scanned;
   search sources receive the confirmed legal name and bounded pagination.
3. `PipelineResearchProvider` calls the existing source registry and ingestion
   pipeline. RAW response storage/readback and terminal OPS run logging must succeed
   before records are released. Sources run serially on a shared pipeline/session.
4. The specialist validates each event's source, expected event type, official URL,
   stable record ID, evidence references and schema. Malformed datasets are withheld;
   other sources continue and failures remain visible.
5. Named subjects are compared with the identity resolver. Feed titles are checked
   only for bounded full-name/alias mentions, not treated as resolved event parties.
6. Typed candidates retain the full normalized source event, source run, observation
   IDs, hashes, retrieval dates, procedural status and finality. Reviewable findings
   flow into the aggregator. Stage-runner results are persisted and reused on retry.
7. Validation and scoring remain separate. Cases remain unscored and routed to
   analyst review under the current workflow policy.

## Sources

| Source ID | Request | Meaning And Limit |
| --- | --- | --- |
| `worldbank_debarment` | Snapshot | Procurement eligibility listings; source flags and dates retained; not criminal convictions |
| `uk_fca_newsroom` | Snapshot | Recent official announcements; partial coverage, unclassified metadata, not enforcement history |
| `uk_gazette_insolvency` | Name search | UK corporate notices; petitions, orders and dismissals kept distinct |
| `uk_find_case_law` | Name search | Published UK judgment metadata only; licensing gate still enforced |

These adapters are not comprehensive worldwide legal coverage. Non-UK parties
can appear in UK proceedings, so the specialist does not silently skip those sources
based on incorporation country. Conversely, an empty UK search cannot establish
absence of proceedings in other jurisdictions.

Court metadata is opt-in and excluded from the default source selection. The registry
requires `FIND_CASELAW_COMPUTATIONAL_LICENSE_APPROVED=true` in the existing source
configuration before fetching. This implementation does not set that value or obtain
permission. Set it only after the project's actual approval requirements are met.

## Attribution And Interpretation

- Name similarity is candidate discovery, not identity certainty. A name-only match
  is `potential`, with no confirmed finding `subject_id`.
- An explicit source subject plus authoritative LEI, or correctly scoped registration
  ID, can confirm identity under the existing policy. Comparable identifier conflicts
  are excluded and retained in the audit result. Current adapters do not populate
  those authoritative identifier fields; they normally produce potential candidates.
- Headline mentions are always potential, with `event_party_role_unknown`. The party
  could be a claimant, defendant, unrelated namesake or merely mentioned. The specialist
  does not infer that the party is the adverse subject from search presence or a title.
- Full normalized name phrases and sufficiently long aliases are used for title
  discovery. No title-level fuzzy search or inferred translations are implemented.
  This conservative rule can miss abbreviations, transliterations and name variants.
- `allegation`, `proceeding`, `decision`, `final_decision`, `judgment_published`,
  `debarment_listing` and `unknown` remain distinct source labels. Finality is retained
  separately; an order or judgment publication is not promoted to final guilt.
- Gazette dismissal outcomes and World Bank eligibility/expiration flags remain in
  the event data. They are not discarded or turned into uniformly adverse conclusions.
- Publication dates are not assumed to be dates of alleged conduct or legal decisions.
  No guessed event timeline date is generated.
- Retrieval older than 24 hours or more than five minutes in the future is withheld.
  This freshness check does not establish source publication freshness or current
  legal status. An apparently old listing requires source eligibility review.
- A verified empty feed/search is distinct from failure. An empty World Bank snapshot
  is withheld as invalid rather than used as clean screening evidence.
- Unknown fields/status schema, duplicate record IDs, missing provenance, failed
  writes and failed terminal logging cannot produce an apparently clean result.
- Search names over the adapters' 200-character limit are blocked explicitly, not
  silently truncated. Alias query planning remains future work.

## Components

| Component | Boundary |
| --- | --- |
| `domain/legal.py` | Typed legal research result and candidate audit contracts |
| `agents/legal.py` | Source requests, relevance, attribution and findings |
| Existing `research/provider.py` | Replaceable verified ingestion/cached provider interface |
| Existing `resolution/confirmed.py` | Shared identity gate |
| Existing orchestrators | Local fan-out and durable stage execution |

A cached provider must enforce equivalent provenance and source-access/usage gates.
Constructing in-memory evidence contracts alone does not verify RAW persistence or
authorize court analysis. There is no new CORE cache or deployed runtime wiring.

## Usage

Default sources: World Bank, FCA and Gazette.

```bash
.venv/bin/trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --legal
```

Limit execution to one source:

```bash
.venv/bin/trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live \
  --legal --legal-source worldbank_debarment
```

Repeat `--legal-source` to select additional adapters. Add `--ownership` and/or
`--sanctions` for parallel specialist branches. These commands make network requests
and existing RAW/OPS writes, not infrastructure deployments. Without the opt-in flags,
the existing live registry-only behavior remains unchanged.

Portable injection:

```python
specialist = LegalSpecialist(PipelineResearchProvider(pipeline))
result = run_case(request, ingestion_pipeline=pipeline,
                  specialists={"legal": specialist})

runner = StageRunner(workflow_store, identity_handler,
                     {WorkflowStage.LEGAL: specialist})
```

## Verification And Next Work

Tests cover attribution, title boundaries, procedural/finality distinctions, eligibility
metadata retention, schema rejection, partial/stale coverage, source failure isolation,
court-access blocking, CLI constraints, graph aggregation and durable stage retries.
This turn does not establish live provider availability or end-to-end Snowflake execution.

Remaining: primary notice/document retrieval under appropriate usage rights, verified
party roles and identifiers, multilingual name resolution, source-specific procedural
classification, corrections/appeals/expired eligibility handling, broader official
jurisdictional coverage, cache/replay, live integration verification and deployed wiring.

Next specialist: news relevance and evidence, kept distinct from official legal records.
