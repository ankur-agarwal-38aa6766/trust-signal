# Source connectors: expansion and operating boundaries

This is the backend ingestion layer, not a completed trust assessment. Every
connector is independently callable, injectable for tests, and registered behind
`SourceRequest`. Connected durable UI integration remains pending. Connectors retrieve source records;
identity matching, adverse attribution and risk scoring are separate components.

Code status reviewed 2026-10-15: four specialist components consume the shared
pipeline through opt-in CLI flags after identity confirmation. They are locally
tested but not injected into the Snowflake runtime. See
[current implementation status](../status.md), [baseline](../verification/history.md)
and [backlog](../backlog/README.md); source-specific live verification dates
remain in [verification history](../verification/history.md).

## Readiness classification

`Implemented` below means the adapter and normalization path have local contract
tests. `Independent` means the connector can call its source without Streamlit,
the case graph or a cloud store. Durable release of its records still requires an
injected observation store and source-run store through `IngestionPipeline`.

| Source | Implemented | Independent | Current evidence boundary |
| --- | --- | --- | --- |
| GLEIF | Yes: lookup, search and relationships | Yes; public API, no project credential | Fresh name and exact-LEI calls passed on 2026-10-15; persistence was not part of that check |
| Norway organization register | Yes: organization and roles | Yes; public API | Local tests pass; prior live evidence is dated 2026-10-03 and needs refreshing before a current availability claim |
| UN entity sanctions | Yes: entity snapshot | Yes; public feed | Local tests pass; prior live evidence is dated 2026-10-03; individuals are outside this adapter |
| OFAC SDN | Yes: snapshot | Yes; public export | Local tests pass; prior live evidence is dated 2026-10-03; non-SDN lists and ownership-rule evaluation are separate |
| UK FCDO sanctions | Yes: snapshot | Yes; public export | Local tests pass; prior live evidence is dated 2026-10-03 |
| EU financial sanctions | Yes: snapshot | Yes; public dataset | Local tests pass; prior live evidence is dated 2026-10-03 |
| Australia DFAT sanctions | Parser and storage path implemented | Yes in code | Captured-response replay is verified; fresh retrieval was not established |
| World Bank debarment | Yes: snapshot | Yes; public discovery flow | Local tests pass; prior live evidence is dated 2026-10-03 |
| FCA newsroom | Yes: recent metadata | Yes; public feed | Local tests pass; prior live evidence is dated 2026-10-03; it is not a final-notice parser |
| UK Gazette insolvency | Yes: bounded search | Yes; public search | Local tests pass; prior live evidence is dated 2026-10-03 |
| GDELT DOC | Yes: bounded metadata search | Yes in code | Captured replay passes; a later fresh request was rate-limited, so current availability is unverified |
| Companies House | Adapter and tests exist | Requires an API key | Project verification remains deliberately paused; do not call it ready for use |
| Find Case Law | Adapter and tests exist | Permission-gated | Automated use remains blocked until computational-analysis permission is approved |

The connector and ingestion-focused suite passed 80 tests on 2026-10-15. This
does not refresh every external service. Test each source separately and record
fresh, replay and fixture results independently.

## Independent GLEIF verification

The direct connector was exercised outside Streamlit, `run_case`, Snowflake and
Google Cloud on 2026-10-15 with:

- name: `Microsoft Corporation`
- LEI: `INR2EJN1ERAN0W5ZP974`

`search_by_name` returned four candidates and reported complete coverage for the
bounded response: Microsoft Corporation, Microsoft India Corporation, Microsoft
Corporation (India) Private Limited and the Microsoft Corporation Savings Plus
401(k) Plan. Every result remained `candidate_requires_resolution`.

`fetch_by_lei` returned `MICROSOFT CORPORATION`, jurisdiction `US-WA`, entity
status `ACTIVE` and registration status `ISSUED`. The exact response was normalized
with a SHA-256 observation hash. The check retained no cloud evidence and created
no source-run record; [verification history](../verification/history.md) records
the exact boundary and hashes.

The same two fresh calls also passed through `SourceRegistry` and
`IngestionPipeline` with in-memory implementations of `ObservationStore` and
`SourceRunStore`. The pipeline released four name candidates and one exact record,
attached verified observation IDs, and completed two run lifecycles. This proves
dependency injection and provider-independent orchestration at process scope. An
in-memory test double is not durable storage or evidence of a cloud adapter.

## Source-by-source implementation

| Source ID | Operation | Scope and boundary |
| --- | --- | --- |
| `uk_companies_house` | `lookup` | Deliberately paused, even if a key is supplied; ingestion records blocked coverage without calling the API |
| `gleif_lei_api` | `lookup`, `search`, `relationships` | Name candidates, exact LEI identity, accounting-consolidation parents/children and reporting exceptions; not automatic beneficial ownership |
| `no_bronnoysund_enhetsregisteret` | `lookup`, `roles` | Organization identity, board roles, other persons/organization role holders and deregistration flags |
| `us_ofac_sdn` | `snapshot` | SDN designations, subject types, aliases and programs; excludes non-SDN lists and ownership-rule screening |
| `uk_fcdo_sanctions` | `snapshot` | Current FCDO list, aliases including non-Latin names, regimes and individual sanction measures |
| `eu_financial_sanctions` | `snapshot` | European Commission consolidated financial sanctions; not all EU restrictive measures |
| `au_dfat_sanctions` | `snapshot` | Official workbook, primary/alias references, individuals/entities/vessels and separate sanction measures |
| `worldbank_debarment` | `snapshot` | Official sanctioned suppliers, debarment/cross-debarment flags, eligibility, source reason and start/end dates |
| `uk_fca_newsroom` | `snapshot` | Recent official regulator announcements, including enforcement discovery; not a complete enforcement database or final-notice parser |
| `uk_gazette_insolvency` | `search` | Bounded UK corporate notice search; excludes personal insolvency and preserves petition/order/dismissal distinctions |
| `uk_find_case_law` | `search` | UK judgment metadata; automated ingestion blocked until project computational-analysis permission is confirmed |
| `gdelt_doc_news` | `search` | Worldwide multilingual news discovery, last 24 hours, up to 50 metadata records; no article-body scraping or automatic publisher trust |

The existing `un_security_council_consolidated_list` adapter remains separate and
covers entity entries only.

## Execute

Install the locked dependencies with `uv sync --locked --extra dev --extra snowflake`.
`openpyxl` parses the actual DFAT workbook; other normalization is deterministic.

```bash
uv run --locked --extra snowflake python -m trust_signal.ingestion.pipeline \
  --list-sources --env-file .env

uv run --locked --extra snowflake python -m trust_signal.ingestion.pipeline \
  --requests examples/source-expansion-requests.json --env-file .env \
  --output outputs/live/source-expansion.json
```

The example intentionally exercises unrelated companies and global lists. It is
a connector acceptance run, not a combined assessment of one party. A blocked
court request or failed provider gives exit status 1; successful source results
remain in the report. This command can ingest tens of megabytes and incur
development warehouse charges. Run selected requests when iterating.

Name-first identity discovery is available without an LEI:

```bash
uv run --locked --extra snowflake trust-signal "Microsoft Corporation" \
  --source-mode gleif_live --env-file .env
```

The result contains identity candidates with persisted observation IDs, requests
confirmation of an LEI, and does not run adverse specialists or calculate a
score. Resubmit the confirmed name and `--lei` for the existing exact-identity
path. Parent relationships are separately requested via ingestion.

## Evidence storage and release

```text
request -> source registry -> independent adapter
  -> exact decoded HTTP body + normalized records
  -> RAW observation / ordered raw chunks
  -> complete byte/hash and metadata readback
  -> OPS terminal coverage record and readback
  -> records with observation IDs -> identity matching -> specialist analysis
```

For a new installation, generated setup SQL includes the migrations and runtime
grants. Existing installations must apply
`snowflake/migrations/V006__source_response_chunks.sql` after V004 and grant
`SELECT, INSERT` on `TRUST_SIGNAL_RAW.SOURCE_RESPONSE_CHUNKS` to their configured
ingestion role. V006 and the existing DEV role's grant were applied during this
expansion. Do not hardcode another installation's runtime role.

Bodies over 4 MiB and binary workbooks are stored in ordered 512 KiB base64 chunks.
Readback validates index sequence, per-chunk hash, complete reconstructed bytes,
manifest count, overall hash and source metadata. UTF-8 whitespace is preserved;
HTTP compression is decoded once, not retained as wire-level compressed bytes.
The RAW payload is structured JSON or parsed snapshot metadata, not a substitute
for the original body. OFAC provenance uses the stable official export endpoint,
not an expiring signed download URL.

Chunks are a single-writer development implementation, not an atomic durable
upload protocol. A partial write may remain when a later chunk or terminal log
fails; no records are released. Retain the original observation for reconciliation
and replay. There is no automatic scheduled retry or stale-run recovery yet.

HTTP errors retain status and `Retry-After` in coverage details without logging
provider exception messages. A 429 is a coverage failure, never a no-match result;
the pipeline does not retry in a tight loop. New HTTP adapters cap decompressed
responses at 64 MiB. Workbook expansion is capped before parsing.

## Procedural labels and privacy

`SourceEvent` separates `event_type`, `procedural_status`, `finality`, `outcome`,
source category and identity status. Possible procedural statuses include
`allegation`, `proceeding`, `decision`, `final_decision`, `judgment_published` and
`debarment_listing`; unsupported conclusions stay `unknown`.

- A Gazette company petition (2450) is a proceeding, not a winding-up decision.
- An order (2452) or dismissal (2461) is a published decision; appeal/finality remains unknown.
- A court judgment's publication does not establish who lost, guilt or exhaustion of appeals.
- World Bank procurement ineligibility is not a criminal conviction. Original eligibility flags and dates remain available.
- A regulator headline is not sufficient to classify an allegation or final decision. Primary-notice retrieval and classification remain the next enforcement work package.
- News provider seen time is not publication time. News records have unassessed publisher trust and unmatched identity.

No connector automatically changes a trust score or approves/rejects a party.
All event metadata is an unmatched candidate until entity resolution confirms
the subject. General announcements may be neutral or positive.

Norway role normalization omits birth dates and personal national identifiers;
the raw official response can still contain birth dates. Restrict raw-table and
local-output access, establish retention controls, and do not expose raw role
payloads to the future reviewer UI by default. Role IDs based on snapshot indexes
are not persistent person identifiers across snapshots.

## Access and usage rights

Official documentation reviewed for the implementation:

- [GLEIF API](https://www.gleif.org/en/lei-data/gleif-api) and [data terms](https://www.gleif.org/en/meta/lei-data-terms-of-use).
- [Norway roles dataset](https://www.brreg.no/bruke-data-fra-bronnoysundregistrene/datasett-og-api/roller-i-virksomheten/) and [API documentation](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/no/index.html). Organization roles are public; person-identifier queries require separate protected access and are not implemented.
- [OFAC SDN exports](https://sanctionslist.ofac.treas.gov/Home/SdnList).
- [Current UK Sanctions List](https://www.gov.uk/government/publications/the-uk-sanctions-list). The former OFSI consolidated export is not used.
- [EU consolidated financial-sanctions dataset](https://data.europa.eu/data/datasets/consolidated-list-of-persons-groups-and-entities-subject-to-eu-financial-sanctions). Its public XML distribution is published in the official dataset metadata.
- [DFAT consolidated list](https://www.dfat.gov.au/international-relations/security/sanctions/consolidated-list) and [column guide](https://www.dfat.gov.au/international-relations/security/sanctions/consolidated-list/guide-australias-consolidated-list).
- [World Bank debarment](https://www.worldbank.org/en/Projects-operations/procurement/debarred-firms). The page publishes a browser-access token used only in an HTTP header for its official JSON endpoint; it is not a project credential. Discovery fails closed if the page changes.
- [FCA publications and feeds](https://www.fca.org.uk/what-we-publish).
- [Gazette feed API](https://github.com/TheGazette/DevDocs/blob/master/notice/notice-feed.md), [notice codes](https://www.thegazette.co.uk/noticecodes) and [commercial data service](https://www.thegazette.co.uk/dataservice). Public targeted discovery is not a license for an unrestricted bulk redistribution service.
- [Find Case Law API and licensing restrictions](https://nationalarchives.github.io/ds-find-caselaw-docs/public). Computational analysis requires separate permission. Set `FIND_CASELAW_COMPUTATIONAL_LICENSE_APPROVED=true` only after approval for this project's intended use; do not set it merely to make a check pass. The initial unauthenticated feed reachability probe was metadata-only; the automated pipeline remains blocked.
- [GDELT DOC API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/amp/) and [GDELT data access](https://www.gdeltproject.org/data.html).

GDELT is the prototype discovery provider. Worldwide discovery does not imply
exhaustive coverage, licensed full article text, verified publisher identity, or
commercial redistribution clearance. Retain source links and limited provider
metadata only. Publisher copyright and database rights still apply; production
storage/display rights require a documented review. Full-text extraction needs
a separately licensed provider agreement or source-specific permission. FCA
official newsroom metadata supplements provider discovery without inheriting
legal conclusions from the article title.

## Remaining work

Authoritative sanctions identifiers and ownership/control rules; normalized CORE storage;
official enforcement document retrieval and evidence-backed procedural
classification; court permission; source refresh jobs and snapshots/diffs;
publisher allowlisting and production rights clearance; durable retries and
recovery; and global jurisdiction expansion beyond these initial event adapters.
The default live case runs identity only. `--sanctions`, `--ownership`, `--legal`
and `--news` inject implemented specialists into the local graph; unresolved
identity stops fan-out. Sanctions name matching yields candidates, not confirmed
legal attribution. Snowflake procedure handlers still omit specialist injection.
This is not complete worldwide coverage or a deployed full-case workflow.
