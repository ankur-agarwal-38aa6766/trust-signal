"""Export a real GLEIF observation and its replayable Snowflake load statement."""

from __future__ import annotations

import argparse
import json
import unicodedata
from dataclasses import asdict
from pathlib import Path

from trust_signal.connectors.base import EntityLookup
from trust_signal.connectors.gleif import GleifAdapter
from trust_signal.ingestion.load import record_receipt
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.connection import SnowflakeSettings, application_stores
from trust_signal.persistence.snowflake_cli import SnowflakeCliObservationStore
from trust_signal.persistence.source_runs import (
    SnowflakeCliSourceRunStore,
    SourceRun,
    SourceRunStore,
)


def _name_key(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKC", value).casefold() if char.isalnum()
    )


def export_observation(
    lookup: EntityLookup,
    output_dir: Path,
    database: str = "TRUST_SIGNAL_DEV",
) -> dict[str, str]:
    """Keep exact response text and generate SQL without interpolating raw JSON."""
    observation = lookup.observation
    prepared = prepare_observation(observation, database)
    observation_id = prepared.observation_id
    response_bytes = prepared.raw_bytes
    digest = observation.content_hash
    table = prepared.table
    sql = f"""-- Official GLEIF response, fetched live. No synthetic payload.
-- Select and run this entire INSERT statement in Snowsight.
-- Sequential replay of this file skips the already stored observation ID.
{prepared.insert_sql}

-- Run this SELECT separately after the INSERT succeeds.
{prepared.verify_sql}
"""
    manifest = {
        "evidence_mode": "live_source",
        "entity": lookup.entity.model_dump(mode="json"),
        "observation": observation.model_dump(mode="json"),
        "observation_id": observation_id,
        "raw_response_bytes": len(response_bytes),
        "target_table": table,
        "load_status": "prepared_not_executed",
        "hash_basis": "exact UTF-8 HTTP response body before JSON parsing",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "raw_response.json"
    sql_path = output_dir / "load_observation.sql"
    manifest_path = output_dir / "manifest.json"
    raw_path.write_bytes(response_bytes)
    sql_path.write_text(sql, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "observation_id": observation_id,
        "legal_name": lookup.entity.legal_name,
        "lei": lookup.entity.lei,
        "observed_at": observation.observed_at.isoformat(),
        "content_hash": digest,
        "raw_response": str(raw_path.resolve()),
        "load_sql": str(sql_path.resolve()),
        "manifest": str(manifest_path.resolve()),
        "load_status": "prepared_not_executed",
    }


def ingest_tracked(adapter, lei, expected_name, output_dir, database, store, runs: SourceRunStore):
    """Coordinate fetching and persistence through independently replaceable adapters."""
    run = SourceRun.create(adapter.source_id, adapter.connector_version)
    details = {"mode": "live_fetch", "requested_record_id": lei, "stage": "fetch"}
    runs.start(run, details)
    seen = accepted = 0
    try:
        lookup = adapter.fetch_by_lei(lei)
        if lookup is None:
            details = {**details, "stage": "not_found"}
            raise ValueError("No source record")
        seen = 1
        details = {**details, "stage": "identity_check"}
        if _name_key(lookup.entity.legal_name) != _name_key(expected_name):
            raise ValueError("Identity mismatch")
        details = {**details, "stage": "export"}
        result = export_observation(lookup, output_dir, database)
        details = {**details, "observation_id": result["observation_id"], "stage": "storage"}
        manifest_path = Path(result["manifest"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["source_run_id"] = run.run_id
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        receipt = store.store_observation(lookup.observation)
        accepted = receipt.verified_rows
        details = {**details, "stage": "manifest", "inserted_rows": receipt.inserted_rows,
                   "verified_rows": receipt.verified_rows}
        record_receipt(manifest_path, receipt)
    except Exception as exc:
        # A storage error may occur after commit. Never claim that no evidence exists.
        failure = {**details, "storage_outcome": "unknown" if details["stage"] == "storage"
                   else "verified" if accepted else "not_attempted"}
        runs.finish(run, "failed", seen, accepted, details["stage"], failure)
        raise RuntimeError(
            f"Source run {run.run_id} failed at {details['stage']}; "
            "check its history and retain any exported bundle for replay."
        ) from exc
    # Do not overwrite success with failure if terminal-log verification itself fails.
    runs.finish(run, "succeeded", seen, accepted, None, {**details, "stage": "complete"})
    result.update(load_status="verified_in_snowflake", receipt=asdict(receipt),
                  source_run_id=run.run_id, run_status="succeeded")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch real GLEIF evidence for Snowflake loading.")
    parser.add_argument("--lei", required=True)
    parser.add_argument("--expected-name", required=True)
    parser.add_argument("--database")
    parser.add_argument("--output-dir", type=Path, required=True)
    connection = parser.add_mutually_exclusive_group()
    connection.add_argument("--env-file", type=Path, help="Use dotenv application configuration")
    connection.add_argument("--application-config", type=Path,
                            help="Use a reusable key-pair application session configured by TOML")
    connection.add_argument(
        "--snowflake-connection", help="Named CLI connection; write and verify after export"
    )
    args = parser.parse_args()
    config = args.application_config or args.env_file
    if config:
        try:
            database = args.database or SnowflakeSettings.from_config(config).database
            with (
                application_stores(config, database) as (store, runs),
                GleifAdapter(timeout=20) as adapter,
            ):
                result = ingest_tracked(adapter, args.lei, args.expected_name, args.output_dir,
                                        database, store, runs)
        except (RuntimeError, ValueError, OSError, KeyError, TypeError):
            parser.exit(1, "Application ingestion failed. Check run history and retain any "
                        "exported bundle; no credentials were printed.\n")
        print(json.dumps(result, indent=2))
        return
    args.database = args.database or "TRUST_SIGNAL_DEV"
    if args.snowflake_connection:
        store = SnowflakeCliObservationStore(args.snowflake_connection, args.database)
        runs = SnowflakeCliSourceRunStore(args.snowflake_connection, args.database)
        try:
            with GleifAdapter(timeout=20) as adapter:
                result = ingest_tracked(adapter, args.lei, args.expected_name, args.output_dir,
                                        args.database, store, runs)
        except RuntimeError as exc:
            parser.exit(1, f"{exc}\n")
        print(json.dumps(result, indent=2))
        return
    with GleifAdapter(timeout=20) as adapter:
        lookup = adapter.fetch_by_lei(args.lei)
    if lookup is None:
        parser.error("GLEIF returned no record; no evidence bundle was written.")
    if _name_key(lookup.entity.legal_name) != _name_key(args.expected_name):
        parser.error("GLEIF legal name conflicts with the expected party; no bundle was written.")
    result = export_observation(lookup, args.output_dir, args.database)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
