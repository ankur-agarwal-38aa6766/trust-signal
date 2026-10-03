"""Command-line entry point for the local case workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from trust_signal.config import environment_config
from trust_signal.connectors.registry import default_registry
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case
from trust_signal.persistence.connection import application_stores


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a TrustSignal demo or persisted live identity case.")
    parser.add_argument("legal_name", help="Submitted legal party name")
    parser.add_argument("--jurisdiction", help="Two-letter jurisdiction code, e.g. GB")
    parser.add_argument("--registration-id", help="Official registration identifier")
    parser.add_argument("--lei", help="20-character Legal Entity Identifier")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="Snowflake/source configuration for live mode")
    parser.add_argument(
        "--source-mode",
        choices=[mode.value for mode in SourceMode],
        default=SourceMode.DEMO_FIXTURES.value,
    )
    args = parser.parse_args()
    request = CaseRequest(
        party={
            "legal_name": args.legal_name,
            "jurisdiction": args.jurisdiction,
            "registration_id": args.registration_id,
            "lei": args.lei,
        },
        source_mode=args.source_mode,
    )
    if request.source_mode == SourceMode.GLEIF_LIVE:
        with application_stores(args.env_file) as (observations, runs):
            pipeline = IngestionPipeline(default_registry(environment_config(args.env_file)), observations, runs)
            result = run_case(request, ingestion_pipeline=pipeline)
    else:
        result = run_case(request)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
