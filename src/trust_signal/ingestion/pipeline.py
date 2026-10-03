"""Persist source evidence and run history before releasing records to callers."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

from trust_signal.config import environment_config
from trust_signal.connectors.registry import (
    SourceRegistry,
    SourceRequest,
    SourceUnavailableError,
    default_registry,
)
from trust_signal.persistence.connection import application_stores
from trust_signal.persistence.contracts import ObservationReceipt, ObservationStore
from trust_signal.persistence.snowflake_cli import SnowflakeCliObservationStore
from trust_signal.persistence.source_runs import (
    SnowflakeCliSourceRunStore,
    SourceRun,
    SourceRunStore,
)


@dataclass
class IngestionResult:
    run_id: str
    source_id: str
    coverage: str
    records: list[dict] = field(default_factory=list)
    receipts: list[ObservationReceipt] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    error_category: str | None = None
    error_stage: str | None = None
    evidence: list[dict] = field(default_factory=list)
    http_status: int | None = None
    retry_after: str | None = None


class IngestionPipeline:
    def __init__(self, registry: SourceRegistry, observations: ObservationStore, runs: SourceRunStore):
        self.registry = registry
        self.observations = observations
        self.runs = runs

    def ingest(self, request: SourceRequest) -> IngestionResult:
        definition = self.registry.get(request)
        run = SourceRun.create(definition.source_id, definition.connector_version)
        details = {"operation": request.operation, "requested_value": request.value,
                   "max_pages": request.max_pages, "stage": "fetch"}
        self.runs.start(run, details)
        result = IngestionResult(run.run_id, definition.source_id, "failed")
        records: list[dict] = []
        seen = accepted = 0
        complete = True
        stage = "fetch"
        try:
            if definition.paused_reason:
                result.limitations.append(definition.paused_reason)
                raise SourceUnavailableError("Source integration is paused.")
            for batch in definition.fetch(request):
                seen += len(batch.records)
                complete = complete and batch.complete
                result.limitations.extend(batch.limitations)
                if batch.records and not batch.observations:
                    raise ValueError("Records must have source observations.")
                stage = "storage"
                batch_ids = []
                for observation in batch.observations:
                    if observation.source_id != definition.source_id:
                        raise ValueError("Observation belongs to another source.")
                    receipt = self.observations.store_observation(observation)
                    if (receipt.verified_rows != 1 or receipt.source_id != observation.source_id
                            or receipt.source_record_id != observation.source_record_id
                            or receipt.content_hash != observation.content_hash):
                        raise ValueError("Observation receipt is not verified.")
                    result.receipts.append(receipt)
                    result.evidence.append({"observation_id": receipt.observation_id,
                                            **observation.model_dump(mode="json", exclude={"raw_payload"})})
                    batch_ids.append(receipt.observation_id)
                accepted += len(batch.records)
                records.extend({**record, "observation_ids": batch_ids} for record in batch.records)
                stage = "fetch"
            result.coverage = "partial" if not complete else "available" if records else "no_matches"
        except Exception as exc:  # noqa: BLE001 - isolate sources, never disclose provider secrets
            result.coverage = "blocked" if isinstance(exc, SourceUnavailableError) else "failed"
            result.error_category = type(exc).__name__
            result.error_stage = stage
            if isinstance(exc, SourceUnavailableError) and definition.access_requirement:
                result.limitations.append(definition.access_requirement)
            if isinstance(exc, httpx.HTTPStatusError):
                result.http_status = exc.response.status_code
                result.retry_after = exc.response.headers.get("Retry-After")
        terminal_details = {**details, "stage": stage, "coverage": result.coverage,
                            "limitations": result.limitations,
                            "http_status": result.http_status, "retry_after": result.retry_after,
                            "observation_ids": [r.observation_id for r in result.receipts]}
        if result.coverage == "failed" and stage == "storage":
            terminal_details["storage_outcome"] = "unknown"
        self.runs.finish(run, "failed" if result.error_category else "succeeded",
                         seen, accepted, result.error_category, terminal_details)
        # A failed fetch/write/log must never release partially verified research.
        if result.error_category is None:
            result.records = records
        return result

    def ingest_many(self, requests: list[SourceRequest]) -> list[IngestionResult]:
        # Keep the existing Snowflake single-writer storage guarantee.
        return [self.ingest(request) for request in requests]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", help="JSON file containing a SourceRequest array")
    parser.add_argument("--list-sources", action="store_true", help="List connector capabilities without opening Snowflake")
    connection = parser.add_mutually_exclusive_group()
    connection.add_argument("--env-file", type=Path)
    connection.add_argument("--connection")
    connection.add_argument("--application-config", type=Path)
    parser.add_argument("--database")
    parser.add_argument("--output", type=Path, help="Save verified records and receipts as JSON")
    args = parser.parse_args()
    if args.list_sources:
        credentials = environment_config(args.env_file) if args.env_file else None
        print(json.dumps(default_registry(credentials).catalog(), indent=2))
        return 0
    if not args.requests or not (args.env_file or args.connection or args.application_config):
        parser.error("Ingestion requires --requests and one connection configuration.")
    requests = [SourceRequest.model_validate(value)
                for value in json.loads(Path(args.requests).read_text(encoding="utf-8"))]
    config = args.application_config or args.env_file
    if config:
        credentials = environment_config(args.env_file) if args.env_file else None
        with application_stores(config, args.database) as (observations, runs):
            results = IngestionPipeline(default_registry(credentials), observations, runs).ingest_many(requests)
    else:
        args.database = args.database or "TRUST_SIGNAL_DEV"
        pipeline = IngestionPipeline(default_registry(),
                                     SnowflakeCliObservationStore(args.connection, args.database),
                                     SnowflakeCliSourceRunStore(args.connection, args.database))
        results = pipeline.ingest_many(requests)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps([asdict(result) for result in results], indent=2), encoding="utf-8")
    print(json.dumps([{**asdict(result), "records": {"count": len(result.records)}}
                      for result in results], indent=2))
    return int(any(result.error_category for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
