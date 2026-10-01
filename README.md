# TrustSignal

TrustSignal is a global legal-entity and organization monitoring product. It resolves a business to the right legal party, gathers evidence from official registries and other trusted sources, and turns verified new information into a traceable, explainable trust profile.

This repository began as a US-oriented KYB research console. The existing implementation and its reconstruction notes are preserved in [docs/current-state-reconstruction.md](docs/current-state-reconstruction.md). The forward-looking product design is in the documents below.

## Design documents

- [Complete system design and operating plan](docs/system-design.md): requirements, service boundaries, multi-agent runtime, scoring, security, deployment, reliability, evaluation, cost, risks, and release gates.
- [Global product and technical design](docs/product-and-technical-design.md): product scope, architecture, components, entity and evidence model, Snowflake roles, and end-to-end data flows.
- [Official source catalog](docs/official-source-catalog.md): global source families and an initial, researched registry list with access and freshness notes.
- [Implementation roadmap](docs/implementation-roadmap.md): hackathon MVP, delivery phases, acceptance criteria, and work sequence.
- [Current-state reconstruction specification](docs/current-state-reconstruction.md): detailed record of the existing codebase and its gaps; this describes inspected behavior, not the new target architecture.

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

The checkout currently contains a Streamlit application and Python/LangGraph workflows that use SEC, GLEIF, and public web search, with local JSON artifacts and SQLite checkpoints. It does not yet implement the global source network or Snowflake-centered production architecture described in the design documents. See the [current-state specification](docs/current-state-reconstruction.md) for detail.
