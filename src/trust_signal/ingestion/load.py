"""Load a saved live-evidence bundle using an injected storage adapter."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from trust_signal.connectors.base import SourceObservation
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.connection import application_stores
from trust_signal.persistence.contracts import ObservationReceipt, ObservationStore
from trust_signal.persistence.snowflake_cli import SnowflakeCliObservationStore


def record_receipt(manifest_path: Path, receipt: ObservationReceipt) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["load_status"] = "verified_in_snowflake"
    manifest["last_load_receipt"] = asdict(receipt)
    manifest["verified_at"] = datetime.now(UTC).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def load_bundle(
    bundle_dir: Path, store: ObservationStore, database: str = "TRUST_SIGNAL_DEV"
) -> ObservationReceipt:
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("evidence_mode") != "live_source":
        raise ValueError("Only a live-source evidence bundle can be loaded with this command.")
    observation = SourceObservation.model_validate({
        **manifest["observation"],
        "raw_response_text": (bundle_dir / "raw_response.json").read_bytes().decode("utf-8"),
    })
    prepared = prepare_observation(observation, database)
    if (manifest.get("observation_id") != prepared.observation_id
            or manifest.get("target_table") != prepared.table):
        raise ValueError("Bundle identity or target table does not match the load request.")
    receipt = store.store_observation(observation)
    record_receipt(manifest_path, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and verify a saved GLEIF evidence bundle.")
    parser.add_argument("--bundle-dir", type=Path, required=True)
    connection = parser.add_mutually_exclusive_group(required=True)
    connection.add_argument("--env-file", type=Path)
    connection.add_argument("--connection")
    connection.add_argument("--application-config", type=Path)
    parser.add_argument("--database")
    args = parser.parse_args()
    config = args.application_config or args.env_file
    if config:
        with application_stores(config, args.database) as (store, _runs):
            receipt = load_bundle(args.bundle_dir, store, store.database)
    else:
        args.database = args.database or "TRUST_SIGNAL_DEV"
        store = SnowflakeCliObservationStore(args.connection, args.database)
        receipt = load_bundle(args.bundle_dir, store, args.database)
    print(json.dumps({"load_status": "verified_in_snowflake", **asdict(receipt)}, indent=2))


if __name__ == "__main__":
    main()
