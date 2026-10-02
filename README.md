# TrustSignal

TrustSignal is a global legal-entity and organization monitoring product. It resolves a business to the right legal party, gathers evidence from official registries and other trusted sources, and turns verified new information into a traceable, explainable trust profile.

This repository began as a US-oriented KYB research console. The existing implementation and its reconstruction notes are preserved in [docs/current-state-reconstruction.md](docs/current-state-reconstruction.md). The forward-looking product design is in the documents below.

## Run locally

Requires Python 3.11 or newer and `uv`.

```bash
uv sync --extra dev
uv run streamlit run app.py
```

The starter runs the identity-input gate, parallel demo specialist branches, comparison board, and review routing. Demo mode uses clearly labeled fixtures. Live GLEIF mode performs an exact-LEI identity lookup only; no further specialist research runs until the identity is confirmed. Neither mode persists to Snowflake or calculates a risk score.

To run the JSON command-line workflow with local fixtures:

```bash
uv run trust-signal "Example Organization Ltd" --jurisdiction GB --registration-id 00000000
```

For a live GLEIF lookup, provide the exact LEI and opt into live mode:

```bash
uv run trust-signal "Bloomberg Finance L.P." --lei 5493001KJTIIGC8Y1R12 --source-mode gleif_live
```

## Design documents

- [Complete system design and operating plan](docs/system-design.md): requirements, service boundaries, multi-agent runtime, scoring, security, deployment, reliability, evaluation, cost, risks, and release gates.
- [Global product and technical design](docs/product-and-technical-design.md): product scope, architecture, components, entity and evidence model, Snowflake roles, and end-to-end data flows.
- [Official source catalog](docs/official-source-catalog.md): global source families and an initial, researched registry list with access and freshness notes.
- [Implementation roadmap](docs/implementation-roadmap.md): hackathon MVP, delivery phases, acceptance criteria, and work sequence.
- [Current-state reconstruction specification](docs/current-state-reconstruction.md): detailed record of the existing codebase and its gaps; this describes inspected behavior, not the new target architecture.
- [Snowflake foundation](snowflake/README.md): initial database schema migration and account setup boundary.

## Product principles

- Legal identity is established from jurisdictional identifiers and official records, not name similarity alone.
- Every claim links to its source, retrieval time, publication time when available, and verification state.
- "No evidence found" is distinct from "evidence of no issue"; unavailable sources remain visible as coverage gaps.
- Models help extract and summarize evidence. Deterministic checks, source provenance, and review controls govern what is presented as verified.
- "Real time" is measured against each source's actual publication and delivery cadence, not promised uniformly across countries.

## Snowflake and CoCo

Snowflake is the intended data and AI platform. Snowflake Cortex Code (CoCo) is intended to assist development. Snowflake Cortex Search, Cortex AI, and Cortex Agents are intended for the deployed product, alongside Snowflake ingestion, storage, and transformation services. CoCo is a development assistant, not a production source connector or monitoring service.

See the [technical design](docs/product-and-technical-design.md) and [roadmap](docs/implementation-roadmap.md) for the architecture and staged delivery plan.

## Current implementation

The current branch contains the initial Python/LangGraph application scaffold, local Streamlit interface, and exact-LEI GLEIF connector. The previous US-oriented KYB implementation is documented in the [current-state reconstruction](docs/current-state-reconstruction.md); it is not present in this checkout. Other live source connectors and Snowflake persistence are not yet implemented.
