# Shared source registry and ingestion

## Verification status: 3 October 2026

The shared pipeline has 92 passing repository tests and a passing lint check.
V004 was applied in Snowflake DEV. Live ingestion verified four GLEIF relationship
observations (18 returned records, explicitly partial due to the page cap) and one
Norway observation. Source-run start and completion were read back successfully.
The name-search and UN snapshot requests failed with `ObservationWriteError`;
their records were withheld and failures recorded. Collection readback projections
have since been adjusted, but the fix has not yet been verified live. Companies
House was recorded as blocked because its credential is absent. The complete
local run report is `outputs/live/shared-ingestion.json` (ignored by Git).
The pipeline is implemented and partially verified, not yet accepted end to end
for every implemented source.

The registry advertises explicit source IDs, operations, jurisdictions, connector
versions, and credential availability. Each adapter owns its client and parsing;
the ingestion pipeline depends on portable observation and run-store protocols.
The current Snowflake adapter uses the named local CLI connection.

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
uv run python -m trust_signal.ingestion.pipeline \
  --requests examples/source_requests.json \
  --connection trust_signal_dev \
  --output outputs/live/shared-ingestion.json
```

Requests are explicit: the sample array exercises unrelated entities to validate
connectors, and is not one unified party assessment. Export
`COMPANIES_HOUSE_API_KEY` to enable UK requests. Credentials are never included
in the catalog or source-run metadata.

## Contracts and behavior

- `SourceRequest`: source ID, supported operation, identifier/name, bounded page limit.
- `SourceBatch`: response observations, normalized records, completeness and limitations.
- `ObservationReceipt`: persisted ID, source/record ID, hash, insert count and verified count.
- `IngestionResult`: run ID, coverage, verified records, receipts, limitations and sanitized failure type.

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

This command provides the persisted ingestion boundary for future agents. The
existing local case graph still uses its direct lookup prototype and is not
automatically migrated by this change. Use `IngestionPipeline` for evidence-backed
consumers. Integrating case context and the resolver into that graph is the next
work package; search candidates must pass that resolver before adverse attribution.

The CLI store remains single-writer. `ingest_many` deliberately writes sequentially;
concurrent workers require a durable claim/queue design before enabling them.
There is no automatic retry, scheduled refresh, crash recovery, or normalized CORE
storage yet. A crash can leave a run `running`; operators must reconcile it.
Replaying an unchanged observation is idempotent within this single-writer model.
The current run log stores request names/identifiers as operational context; tenant
and case access controls are required before exposing this path to multiple users.
