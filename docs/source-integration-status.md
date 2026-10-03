# Source Integration Status and First Live Load

**Checked:** 3 October 2026. This document separates code availability, live retrieval, and Snowflake deployment. A source appearing in the catalog does not mean its connector exists.

## Current connector expansion

The new [connector operating guide](source-connectors.md) describes standalone
adapters, request examples, access gates, event labels and usage rights. These
checks used actual official/provider responses, not synthetic evidence:

| Source / operation | Result | Verification boundary |
| --- | --- | --- |
| Companies House | Paused by request | No API call, even when a key is present |
| GLEIF name search | 4 candidates | Fresh adapter HTTP retrieval, RAW and terminal-log readback in DEV |
| GLEIF Microsoft relationships | 18 records / 4 observations | Same path; child results capped and marked partial; includes parent reporting exceptions |
| GLEIF Microsoft India parents | 3 records / 3 observations | Exact record, direct and ultimate parent relationships stored/read back; partial because the child relationship link was absent |
| Norway Equinor roles | 15 records | Fresh HTTP retrieval, RAW and terminal-log readback in DEV |
| OFAC SDN | 19,488 listings | Fresh HTTP retrieval; complete chunk reconstruction/hash verified in DEV |
| UK FCDO sanctions | 6,370 designations | Fresh HTTP retrieval; complete chunk reconstruction/hash verified in DEV |
| EU financial sanctions | 6,241 listings | Fresh HTTP retrieval; complete chunk reconstruction/hash verified in DEV |
| Australia DFAT | 4,010 listings | Official workbook downloaded with curl; real adapter parser and binary readback verified by replaying those exact bytes. Adapter HTTP requests still timed out |
| World Bank debarment | 1,504 records | Fresh HTTP retrieval; both official page and JSON retained/read back in DEV |
| FCA newsroom | 20 entries, partial | Fresh HTTP retrieval and RAW readback; announcement metadata, not final-decision classification |
| Gazette Carillion search | 20 corporate notices, partial | Fresh HTTP retrieval and RAW readback; bounded page cap and unmatched identity |
| Find Case Law | Blocked in pipeline | Public metadata feed reachability checked; computational-analysis permission not confirmed |
| GDELT Microsoft discovery | 5 multilingual entries, partial | One live provider request succeeded; real adapter parsing and RAW readback verified through exact capture replay. Later adapter requests received HTTP 429 |

Live snapshots contain individuals and, where applicable, vessels/aircraft as
well as entities; counts are **not company-only counts** or matches to Microsoft.
Norway normalized role records omit birth dates; raw payloads still require
restricted access. No source snapshot establishes an entity-specific risk score.

The retained reports are under ignored `outputs/live/`:
`source-expansion.json` (initial run), `source-expansion-retry.json` (intermediate),
`source-expansion-final.json` (EU/World Bank/FCA after raw-retention fixes), and
`source-expansion-capture-replay.json` (Australia/GDELT replay boundary).
`name-first-case.json` confirms four candidates, no score and no specialist
fan-out before LEI confirmation. `gleif-actual-parent.json` retains the live
Microsoft India parent-record check.
Early errors remain visible rather than being overwritten as successes.
V006 and ingestion-role chunk grants are applied in DEV. Successful observations
and terminal run logs were verified before records were released.

Remaining gaps: Australia adapter HTTP reliability, GDELT shared-endpoint rate
limits, court permission, enforcement primary-document parsing, production news
rights clearance, entity-specific source matching and global event coverage.

The [reusable application connection](application-connection.md) now supports
key-pair authentication under a dedicated DEV service identity. Real Microsoft
ingestion and duplicate-free bundle replay have also been verified in this mode;
the CLI examples below remain available as the earlier administrative path.

## Working integration

The existing `GleifAdapter` was exercised against the official API for **MICROSOFT CORPORATION**, LEI `INR2EJN1ERAN0W5ZP974`. The returned entity jurisdiction is `US-WA`, entity status is `ACTIVE`, and LEI registration status is `ISSUED`. These are source-record fields; they do not constitute an overall risk assessment.

The captured response was observed at `2026-10-03T04:13:58.284108+00:00` (09:43:58 India time). Its exact HTTP response body contains 3,058 UTF-8 bytes and has SHA-256:

```text
d553abd7602964b66f64c1d87d590d98a6980215fee547aa24023d17508af191
```

Source: [official GLEIF record](https://search.gleif.org/#/record/INR2EJN1ERAN0W5ZP974). GLEIF makes LEI reference data available under its [LEI data terms of use](https://www.gleif.org/en/meta/lei-data-terms-of-use).

## Connector implementation queue

| Priority | Source | Current code / access status | Implementation scope |
|---|---|---|---|
| 1 | GLEIF | Exact lookup, name search and relationships stored and verified in Snowflake DEV; live registry agent uses shared ingestion | Name results remain candidates; parent exceptions and bounded child coverage preserved |
| 2 | UK Companies House | Contract-tested; deliberately paused while API access is unavailable | Company profile lookup by company number. Next after access: officers, filing history, insolvency and approved ownership fields |
| 3 | Norway organization registry | EQUINOR ASA identity and 15 role records stored and read back with verified raw hashes in Snowflake DEV | Organization-number lookup, board/organizational roles. Next: allowed change endpoints |
| 4 | UN consolidated sanctions list | Full XML stored and hash-verified in Snowflake DEV; all 275 entity nodes parsed | Entity listings, aliases, listed date and regime. Individuals are not parsed. Next: candidate matching |
| 5 | SEC EDGAR | Planned in this checkout; declared user agent and access rules required | Relevant issuer submissions and filings; not a general company register |
| 6 | News provider / official newsroom feeds | GDELT metadata adapter and FCA newsroom implemented; live/replay distinctions above | Metadata and links only; production usage-rights review, publisher trust and primary-document classification pending |
| 7 | OFAC / EU / UK / Australia sanctions | Separate adapters implemented; raw/binary Snowflake retention verified with boundaries above | Designation measures, aliases, dates; entity matching and ownership rules pending |
| 8 | France / Canada / Australia / India / Singapore / Japan / New Zealand / South Africa registries | Catalogued; connectors not implemented | Jurisdiction-specific identity and permitted disclosures |
| 9 | Courts, insolvency, regulator enforcement, debarment and safety | World Bank, corporate Gazette, court metadata and FCA announcement adapters implemented; court gate blocked | Procedural metadata without adverse inference; enforcement document parsing, safety sources and broader jurisdictions pending |

Official endpoint discovery, access notes and jurisdiction boundaries are in [official-source-catalog.md](official-source-catalog.md). No synthetic fixture branch is counted as a working source integration.

## Repeatable live verification

Run the original registry/UN adapter checks (Companies House deliberately paused):

```bash
uv run python -m trust_signal.connectors.verify_live
```

The command checks Microsoft's LEI, Equinor's organization number, Tesco's company
number `00445790` (currently paused), and the UN XML snapshot.
Entity checks validate the expected legal name; adapters validate requested identifiers.
Each successful check validates the retained response hash and writes the raw response,
normalized data, and provenance under ignored `outputs/live/source-verification/`.
The UN check also verifies that every entity XML node was parsed and identifiers are unique.
`report.json` records each source separately as `passed`, `failed`, or `paused`.
The command exits with status 1 while any source is paused or failed. Use the
shared ingestion command and expanded request example in the operating guide
for the new connectors and Snowflake verification.
Each rerun replaces this output directory's per-source files and report; use
`--output-dir outputs/live/<run-name>` to retain separate runs.

On 3 October 2026, the live UN response contained 2,187,322 bytes, generated at
`2026-10-02T23:00:05.487Z`, with SHA-256
`80119f94467cfcbb750c6e33145633f873d239b6f8b99ddfe04daa4962d22a48`.
The Norway record returned `EQUINOR ASA`, legal form `ASA`, jurisdiction `NO`,
and address `Forusbeen 50, 4035, STAVANGER, Norge`.
Companies House credentials were unavailable, so its live API parsing remains unverified.
These checks validate retrieval and normalization of sample data; they do not validate
all endpoints, establish entity sanctions matches, or load data into Snowflake.

## First live evidence load

Retrieve and export the real record using the connector:

```bash
uv run python -m trust_signal.ingestion.raw_export \
  --lei INR2EJN1ERAN0W5ZP974 \
  --expected-name "Microsoft Corporation" \
  --database TRUST_SIGNAL_DEV \
  --output-dir outputs/live/microsoft_gleif
```

The command produces `raw_response.json` (exact response bytes), `manifest.json` (provenance), and `load_observation.sql` (INSERT and verification SELECT). Generated evidence stays in ignored `outputs/`; it is not automatically committed. There is no synthetic fallback: a lookup failure or mismatching legal name stops the export.

The generated INSERT decodes the captured response, checks its hash and parses it into `RAW_PAYLOAD`. It carries retrieval time, source record ID, citation URL, connector version and content hash. Optional tenant/case links are left null because this is a standalone public-source observation, not an authenticated case request. The original response file retains byte-level fidelity; Snowflake VARIANT retains structured JSON rather than original JSON formatting.

In the existing Snowsight SQL editor, use role `TRUST_SIGNAL_DEPLOYER`, warehouse `TRUST_SIGNAL_PIPELINE_WH`, and database `TRUST_SIGNAL_DEV`. Execute the entire generated INSERT first, then its verification SELECT separately. Expect one row inserted on the first load, then a returned row with Microsoft's legal name and source status. Sequential replay of the same bundle skips the same observation ID. This is a manual single-writer load, not a guarantee of concurrent exactly-once ingestion.

## Automated insertion verified

The `trust_signal_dev` CLI connection was tested with local OAuth login, role
`TRUST_SIGNAL_DEPLOYER`, database `TRUST_SIGNAL_DEV`, and warehouse
`TRUST_SIGNAL_PIPELINE_WH`. A direct read confirmed the user-loaded Microsoft observation.
Replaying that saved observation through the storage adapter returned `inserted_rows: 0`
and `verified_rows: 1`, proving sequential replay kept the existing record.

A fresh real GLEIF retrieval at `2026-10-03T05:19:00.556643+00:00` was then automatically
inserted and verified with observation ID `observation_1b5c81f332b2534b869b3808ff61a585`.
The adapter reported `inserted_rows: 1` and `verified_rows: 1`. It compares stored source
metadata, content hash and the complete parsed JSON against the captured response.
Its bundle is in ignored `outputs/live/microsoft_gleif_automated/`; its manifest now
reports `verified_in_snowflake` and contains a load receipt.

```bash
uv run python -m trust_signal.ingestion.raw_export \
  --lei INR2EJN1ERAN0W5ZP974 \
  --expected-name "Microsoft Corporation" \
  --output-dir outputs/live/microsoft_gleif_automated \
  --snowflake-connection trust_signal_dev
```

To replay an existing bundle without fetching a new record:

```bash
uv run python -m trust_signal.ingestion.load \
  --bundle-dir outputs/live/microsoft_gleif_automated \
  --connection trust_signal_dev
```

`ObservationStore` is a platform-independent storage interface. The current adapter
invokes the installed Snowflake CLI without a shell and sends SQL through stdin using
the named connection; it does not read or print credentials. A Python-driver or SPCS
adapter can implement the same interface later. Timeouts and command failures leave
the write outcome explicit as unknown; verify/replay the saved bundle rather than
refetching to retry. Concurrent writer guarantees, normalized entity
persistence, deployed worker execution and Cortex integration remain pending.

## Source-run tracking

Live verification on 2026-10-03 succeeded for Microsoft: run
`run_e260367546e14a9ea71e2b54b83eac09` finished `succeeded` with one record seen,
one accepted and one newly inserted observation,
`observation_bc22f58748b55445b8e1552a22a596b5`. Its real response was retrieved at
`2026-10-03T05:42:21.339877+00:00`; the saved bundle is
`outputs/live/microsoft_gleif_tracked/`. Both storage and terminal-log readback passed.

`V003__source_run_tracking.sql` creates the operations log independently of the
remaining foundation tables. Apply it before using `--snowflake-connection`:

```bash
snow sql --connection trust_signal_dev --database TRUST_SIGNAL_DEV \
  -f snowflake/migrations/V003__source_run_tracking.sql
```

Automated GLEIF ingestion starts a `running` log before fetching, then records
`succeeded` or `failed`, retrieval/verification counts, connector version, failure
stage and linked observation ID. `RECORDS_ACCEPTED` counts verified observations,
not new inserts; `DETAILS:inserted_rows` distinguishes insertion from replay.
The local bundle manifest also contains `source_run_id`. Export-only and saved
bundle replay commands do not create a new live-fetch log.

```sql
SELECT SOURCE_RUN_ID, SOURCE_ID, RUN_STATUS, STARTED_AT, COMPLETED_AT,
       RECORDS_SEEN, RECORDS_ACCEPTED, ERROR_CATEGORY, DETAILS
FROM TRUST_SIGNAL_DEV.TRUST_SIGNAL_OPS.SOURCE_RUNS
ORDER BY STARTED_AT DESC
LIMIT 20;
```

`SourceRunStore` is a replaceable lifecycle contract separate from evidence storage.
Both start and terminal writes require readback verification. Error categories are
sanitized stages, not raw exception text. A timeout during storage means the commit
outcome is unknown. A terminal-log failure can leave already verified evidence;
retain its bundle and reconcile the run rather than fetching again.

This is a single-writer development path, not a durable job system. Process termination
can leave a `running` row; stale-run reconciliation, scheduled retries, concurrency
control and tracking for other connectors are still pending. Fixture failure tests
run locally only; they do not insert synthetic records into Snowflake.
