# Shared source registry and ingestion

## Verification status: 3 October 2026

Live application-session ingestion verifies GLEIF name search (four candidates),
GLEIF relationships (four observations and 18 records, partial because of the
configured page cap), Norway (one observation), and UN XML (one observation and
all 275 entity listings). Raw body hashes, metadata, structured payloads, and
terminal source-run history were read back successfully. The earlier CLI
search/XML failures are superseded by this successful application run.
Companies House remains blocked because its credential is absent; that gap was
recorded in Snowflake. The complete local report is
`outputs/live/shared-ingestion-application.json` (ignored by Git). V004 is applied
in DEV. A live Microsoft case also resolved identity and produced a finding only
after raw evidence and source-run history were verified in Snowflake.

The registry advertises explicit source IDs, operations, jurisdictions, connector
versions, and credential availability. Each adapter owns its client and parsing;
the ingestion pipeline depends on portable observation and run-store protocols.
The application adapter shares a key-pair-authenticated Snowflake session between
observation and run repositories. The named CLI connection remains an alternative.

```text
SourceRequest -> registry -> adapter -> response page + normalized records
    -> Snowflake RAW write -> metadata/payload/raw hash readback
    -> OPS run completion + coverage readback -> records with observation IDs
```

## Execute

Apply `snowflake/migrations/V004__raw_response_retention.sql` in the selected
development database after V001 and V003. V004 adds `RAW_RESPONSE_TEXT` without
changing old rows. Old evidence requires its original bundle to be replayed;
existing rows without raw text fail the stronger readback check until reconciled.

```bash
uv run --extra snowflake python -m trust_signal.ingestion.pipeline --list-sources --env-file .env

uv run --extra snowflake python -m trust_signal.ingestion.pipeline \
  --requests examples/microsoft_identity.json \
  --env-file .env \
  --output outputs/live/microsoft-identity.json
```

Configure `.env` using `.env.example`; keep the populated file and key files
private. `--env-file` reads source and application connection settings without
changing the global environment. Exported variables override file values.
`--list-sources` does not open Snowflake; `configured` means credentials are
present, not that the API is currently reachable. Use `--connection trust_signal_dev`
instead of `--env-file` for the CLI transport, or `--application-config` for a
legacy application TOML. The application transport is the live-verified path.

Requests are explicit: `examples/microsoft_identity.json` looks up one party.
`examples/source_requests.json` exercises unrelated entities and a global sanctions
dataset to validate connectors; it is not one unified party assessment. Supply
`COMPANIES_HOUSE_API_KEY` in `.env` or the environment to enable UK requests.
Credentials are never included in the catalog or source-run metadata.

To run the actual live identity agent:

```bash
uv run --extra snowflake trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --env-file .env
```

This path stores and verifies the registry response and run history, then passes
the normalized entity to the resolver and creates a finding containing
`observation_ids` and `source_run_id`. If storage fails, the branch produces no
finding and the case routes to review with coverage gaps. Demo fixtures continue
to run without Snowflake. Local Streamlit live mode uses `.env`; an application
worker can inject its configured pipeline into `run_case` explicitly.

## Use from another component

```python
from pathlib import Path
from trust_signal.config import environment_config
from trust_signal.connectors.registry import SourceRequest, default_registry
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.persistence.connection import application_stores

config = Path(".env")
with application_stores(config) as (observations, runs):
    pipeline = IngestionPipeline(default_registry(environment_config(config)), observations, runs)
    result = pipeline.ingest(SourceRequest(
        source_id="gleif_lei_api", operation="search", value="Microsoft Corporation",
    ))
    # Search results are persisted candidates, not a confirmed party.
    candidates = result.records
    coverage = result.coverage
```

The registry is the directory of available sources, the connector knows one
source's HTTP format, and the pipeline coordinates fetching, storage and audit.
Other components can use the same pipeline without depending on a connector's
HTTP implementation or its Snowflake connection transport. Inject different
`ObservationStore` and `SourceRunStore` implementations to test it or replace
the storage platform. No alternative cloud storage adapter is implemented yet.

## Snowflake storage

The configured warehouse executes ingestion and verification SQL.
`TRUST_SIGNAL_RAW.SOURCE_OBSERVATIONS` holds the original response, structured
JSON or XML snapshot metadata, source URL, observed time, version, and SHA-256.
`TRUST_SIGNAL_OPS.SOURCE_RUNS` holds request context, timestamps, counts, failure
type, coverage, limitations, and persisted observation IDs. Cortex services are
not invoked during this deterministic ingestion stage.

Inspect coverage in Snowsight with the intended database selected:

```sql
SELECT SOURCE_RUN_ID, SOURCE_ID, RUN_STATUS, RECORDS_SEEN, RECORDS_ACCEPTED,
       ERROR_CATEGORY, DETAILS:coverage::VARCHAR AS COVERAGE
FROM TRUST_SIGNAL_OPS.SOURCE_RUNS
ORDER BY STARTED_AT DESC;
```

The terminal JSON includes record counts and receipts. `--output` saves the full
normalized records and provenance. Exit status is 1 when any request fails or is
blocked; a deliberately capped `partial` result has no transport error and exits
0 unless another request fails. Callers must examine coverage and limitations.

## Contracts and behavior

- `SourceRequest`: source ID, supported operation, identifier/name, bounded page limit.
- `SourceBatch`: response observations, normalized records, completeness and limitations.
- `ObservationReceipt`: persisted ID, source/record ID, hash, insert count and verified count.
- `IngestionResult`: run ID, coverage, verified records, provenance, receipts, limitations, failure stage and sanitized failure type.

Coverage is `available`, `no_matches`, `partial`, `blocked`, or `failed`.
These values describe this request and operation, never all coverage for a country.
The UN operation covers entities only; its limitation remains visible even when
the entity snapshot succeeds. A capped GLEIF collection is partial.
Empty successful queries are not an assertion that the party has no risk.

Every response page is stored before its records become available. JSON retains
both the exact UTF-8 response and structured VARIANT. UN XML retains the exact
UTF-8 body with parsed snapshot metadata in VARIANT. Snowflake readback verifies
the exact response hash as well as metadata and structured payload. An invalid
encoding or mismatched hash stops ingestion; no reconstructed body is substituted.

Each returned record includes its batch observation IDs. A later fetch/write
failure keeps verified receipts and run counts but withholds all records for
that request. A lifecycle-write failure raises rather than releasing records.
Run start failure prevents fetching. Other source errors are recorded and allow
the next explicit request to proceed. Storage failures record an unknown outcome
because a timed-out write may have committed.

## GLEIF discovery

Name search uses `filter[entity.legalName]`, follows trusted API pagination links,
and returns candidates requiring identity resolution. It never picks the first
name hit as the legal party. Relationships include the exact LEI record, direct
and ultimate parent relationship records or reporting exceptions, and direct
child relationships. The source attributes and relationship status are preserved;
accounting consolidation is not automatically treated as beneficial ownership.
Missing relationship links produce a coverage limitation. Pagination is bounded,
rejects off-origin links, and detects loops.

Official reference: [GLEIF API capabilities and documentation](https://www.gleif.org/en/lei-data/gleif-api).

## Runtime boundaries

The default live GLEIF case graph uses this persisted ingestion boundary.
An application worker may inject `IngestionPipeline` into `run_case`, or call
`pipeline.ingest(SourceRequest(...))` directly from a specialist. Only returned
verified records should enter agent reasoning; connectors belong to ingestion.
Custom graph branches supplied by callers own their evidence discipline.
The default case graph still requires an exact LEI; name search is available
through ingestion and must pass identity resolution before adverse attribution.
Sanctions matching, other specialist agents, and case-scoped persistence remain
separate work packages.

The CLI store remains single-writer. `ingest_many` deliberately writes sequentially;
concurrent workers require a durable claim/queue design before enabling them.
There is no automatic retry, scheduled refresh, crash recovery, or normalized CORE
storage yet. A crash can leave a run `running`; operators must reconcile it.
Replaying an unchanged observation is idempotent within this single-writer model.
The current run log stores request names/identifiers as operational context; tenant
and case access controls are required before exposing this path to multiple users.
