"""Opt-in live source checks with locally retained evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import httpx

from trust_signal.connectors.companies_house import CompaniesHouseAdapter
from trust_signal.connectors.gleif import GleifAdapter
from trust_signal.connectors.norway import NorwayRegistryAdapter
from trust_signal.connectors.un_sanctions import UNSanctionsAdapter


def verify_source(source: str, output_dir: Path) -> dict:
    """Fetch through the actual adapter; never substitute fixture data."""
    result = {"source": source, "checked_at": datetime.now(UTC).isoformat()}
    key = os.environ.get("COMPANIES_HOUSE_API_KEY", "").strip()
    if source == "companies_house":
        return {**result, "status": "paused", "reason": "Companies House verification paused by project owner"}
    adapters = {
        "gleif": lambda: GleifAdapter(timeout=30),
        "norway": lambda: NorwayRegistryAdapter(timeout=30),
        "un_sanctions": lambda: UNSanctionsAdapter(timeout=30),
        "companies_house": lambda: CompaniesHouseAdapter(api_key=key, timeout=30),
    }
    try:
        with adapters[source]() as adapter:
            if source == "gleif":
                data = adapter.fetch_by_lei("INR2EJN1ERAN0W5ZP974")
                expected_name = "MICROSOFT CORPORATION"
            elif source == "norway":
                data = adapter.fetch_organization("923609016")
                expected_name = "EQUINOR ASA"
            elif source == "companies_house":
                data = adapter.fetch_company_profile("00445790")
                expected_name = "TESCO PLC"
            else:
                data = adapter.fetch_snapshot()
                expected_name = None
        if data is None:
            raise ValueError("Sample record was not found")
        observation = data.observation
        raw = (observation.raw_response_text or "").encode("utf-8")
        if not raw or observation.content_hash != f"sha256:{hashlib.sha256(raw).hexdigest()}":
            raise ValueError("Retained response does not match source content hash")
        if source == "un_sanctions":
            listing_ids = [listing.source_record_id for listing in data.listings]
            if len(set(listing_ids)) != len(listing_ids):
                raise ValueError("Duplicate sanctions identifiers")
            root = ElementTree.fromstring(raw)
            if len(root.findall(".//ENTITY")) != len(data.listings):
                raise ValueError("Some source entity listings were not parsed")
            summary = {
                "entity_count": len(data.listings),
                "generated_on": observation.raw_payload.get("generated_on"),
                "sample": data.listings[0].model_dump(mode="json"),
                "scope": "entity listings only; individuals are not parsed",
            }
        else:
            if data.entity.legal_name.upper() != expected_name:
                raise ValueError("Sample legal name does not match the expected entity")
            summary = data.entity.model_dump(mode="json")
        source_dir = output_dir / source
        source_dir.mkdir(parents=True, exist_ok=True)
        extension = "xml" if source == "un_sanctions" else "json"
        (source_dir / f"raw_response.{extension}").write_bytes(raw)
        (source_dir / "normalized.json").write_text(data.model_dump_json(indent=2), encoding="utf-8")
        return {
            **result,
            "status": "passed",
            "observation": observation.model_dump(mode="json", exclude={"raw_payload"}),
            "response_bytes": len(raw),
            "summary": summary,
        }
    except httpx.HTTPStatusError as exc:
        return {**result, "status": "failed", "error": type(exc).__name__,
                "http_status": exc.response.status_code}
    except (httpx.HTTPError, RuntimeError, ValueError, OSError, ElementTree.ParseError) as exc:
        # Exception messages can include credential-bearing URLs; report only the type.
        return {**result, "status": "failed", "error": type(exc).__name__}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/live/source-verification"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sources = ["gleif", "norway", "un_sanctions", "companies_house"]
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda source: verify_source(source, args.output_dir), sources))
    report = {"checked_at": datetime.now(UTC).isoformat(), "results": results,
              "snowflake_load": "not_performed"}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if all(result["status"] == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
