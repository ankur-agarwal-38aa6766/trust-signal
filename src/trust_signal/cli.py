"""Command-line entry point for the local case workflow."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from trust_signal.agents.legal import DEFAULT_LEGAL_SOURCES, LEGAL_SOURCES, LegalSpecialist
from trust_signal.agents.news import NEWS_SOURCES, NewsSpecialist
from trust_signal.agents.ownership import OwnershipSpecialist
from trust_signal.agents.sanctions import DEFAULT_SANCTIONS_SOURCES, SanctionsSpecialist
from trust_signal.config import environment_config
from trust_signal.connectors.registry import default_registry
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case
from trust_signal.persistence.connection import application_stores
from trust_signal.research.provider import PipelineResearchProvider
from trust_signal.screening.providers import PipelineSanctionsProvider
from trust_signal.screening.sanctions import SUPPORTED_SANCTIONS_SOURCES


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a TrustSignal demo or persisted live identity case.")
    parser.add_argument("legal_name", help="Submitted legal party name")
    parser.add_argument("--jurisdiction", help="Two-letter jurisdiction code, e.g. GB")
    parser.add_argument("--registration-id", help="Official registration identifier")
    parser.add_argument("--lei", help="20-character Legal Entity Identifier")
    parser.add_argument("--news", action="store_true", help="Discover reviewable news mentions")
    parser.add_argument("--news-source", action="append", choices=NEWS_SOURCES)
    parser.add_argument("--legal", action="store_true", help="Research official legal/adverse-event metadata after identity confirmation")
    parser.add_argument("--legal-source", action="append", choices=LEGAL_SOURCES,
                        help="Repeat to select sources; courts are opt-in and require existing approval")
    parser.add_argument("--ownership", action="store_true", help="Research accounting relationships and leadership after identity confirmation")
    parser.add_argument("--norway-organization-number", help="Optional 9-digit Norway organization hint; does not confirm identity")
    parser.add_argument("--sanctions", action="store_true", help="Screen sanctions after persisted identity confirmation")
    parser.add_argument("--sanctions-source", action="append", choices=SUPPORTED_SANCTIONS_SOURCES,
                        help="Repeat to select snapshot sources; defaults to UN, OFAC SDN, UK and EU")
    parser.add_argument("--env-file", type=Path, default=Path(".env"), help="Snowflake/source configuration for live mode")
    parser.add_argument(
        "--source-mode",
        choices=[mode.value for mode in SourceMode],
        default=SourceMode.DEMO_FIXTURES.value,
    )
    args = parser.parse_args()
    if args.news and args.source_mode != SourceMode.GLEIF_LIVE.value:
        parser.error("--news requires --source-mode gleif_live.")
    if args.news_source and not args.news:
        parser.error("--news-source requires --news.")
    if args.news_source and len(set(args.news_source)) != len(args.news_source):
        parser.error("Select distinct news sources.")
    if args.legal and args.source_mode != SourceMode.GLEIF_LIVE.value:
        parser.error("--legal requires --source-mode gleif_live.")
    if args.legal_source and not args.legal:
        parser.error("--legal-source requires --legal.")
    if args.legal_source and len(set(args.legal_source)) != len(args.legal_source):
        parser.error("Select distinct legal sources.")
    if args.ownership and args.source_mode != SourceMode.GLEIF_LIVE.value:
        parser.error("--ownership requires --source-mode gleif_live.")
    if args.norway_organization_number and not args.ownership:
        parser.error("--norway-organization-number requires --ownership.")
    if args.norway_organization_number and not re.fullmatch(r"[0-9]{9}", args.norway_organization_number):
        parser.error("Norwegian organization number must contain exactly 9 digits.")
    if args.sanctions_source and not args.sanctions:
        parser.error("--sanctions-source requires --sanctions.")
    if args.sanctions and args.source_mode != SourceMode.GLEIF_LIVE.value:
        parser.error("--sanctions requires --source-mode gleif_live.")
    if args.sanctions_source and len(set(args.sanctions_source)) != len(args.sanctions_source):
        parser.error("Select distinct sanctions sources.")
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
            specialists = {"sanctions": SanctionsSpecialist(
                PipelineSanctionsProvider(pipeline),
                source_ids=args.sanctions_source or DEFAULT_SANCTIONS_SOURCES)} if args.sanctions else {}
            if args.ownership:
                specialists["ownership"] = OwnershipSpecialist(
                    PipelineResearchProvider(pipeline), norway_organization_number=args.norway_organization_number)
            if args.legal:
                specialists["legal"] = LegalSpecialist(
                    PipelineResearchProvider(pipeline), source_ids=args.legal_source or DEFAULT_LEGAL_SOURCES)
            if args.news:
                specialists["news"] = NewsSpecialist(
                    PipelineResearchProvider(pipeline), source_ids=args.news_source or NEWS_SOURCES)
            result = run_case(request, ingestion_pipeline=pipeline, specialists=specialists)
    else:
        result = run_case(request)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
