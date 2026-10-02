"""Command-line entry point for the local case workflow."""

from __future__ import annotations

import argparse

from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local TrustSignal demonstration case.")
    parser.add_argument("legal_name", help="Submitted legal party name")
    parser.add_argument("--jurisdiction", help="Two-letter jurisdiction code, e.g. GB")
    parser.add_argument("--registration-id", help="Official registration identifier")
    parser.add_argument("--lei", help="20-character Legal Entity Identifier")
    parser.add_argument(
        "--source-mode",
        choices=[mode.value for mode in SourceMode],
        default=SourceMode.DEMO_FIXTURES.value,
    )
    args = parser.parse_args()
    result = run_case(
        CaseRequest(
            party={
                "legal_name": args.legal_name,
                "jurisdiction": args.jurisdiction,
                "registration_id": args.registration_id,
                "lei": args.lei,
            },
            source_mode=args.source_mode,
        ),
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
