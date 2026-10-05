# TrustSignal

TrustSignal is an open-source, worldwide evidence-led legal-entity research solution.
The hackathon scope is closed. Start with the [future scope and decision register](docs/future-scope.md)
for retained ideas, unresolved choices and their delivery issues. Snowflake remains
the first supported platform; other provider integrations are future work.

The [project context and decisions](docs/project-context.md) preserve the original
vision, constraints, open questions and links for future contributors.

For handoff and remaining work, start with the [development backlog](docs/development-backlog.md)
and [implementation baseline](docs/baseline.md). Issue-ready tasks cover all seven
flow stages and shared platform work; historical status sections below may lag this baseline.

Use [.env.example](.env.example) as the account-independent template and keep
your populated `.env` private. [Portable Deployment](docs/portable-deployment.md)
explains new-account setup and future provider adapters.

For the verified key-pair application connection and reusable worker session,
see [Application Connection](docs/application-connection.md). The OAuth CLI path
remains available for administration; application queries need no browser login.

TrustSignal is a global legal-entity and organization monitoring product. It resolves a business to the right legal party, gathers evidence from official registries and other trusted sources, and turns verified new information into a traceable, explainable trust profile.

This repository began as a US-oriented KYB research console. The existing implementation and its reconstruction notes are preserved in [docs/current-state-reconstruction.md](docs/current-state-reconstruction.md). The forward-looking product design is in the documents below.

## Run locally

Requires Python 3.11-3.14 and `uv`. This is a backend preview, not a one-command
installation of the complete hosted product. The workflow/UI demo is separate
from the real-source Snowflake ingestion path below.

## Try in Your Snowflake Account

For the **complete backend installation** (tables, views, permissions, procedures
and suspended task graph), use [Snowflake initialization](docs/snowflake-initialization.md).
The steps below remain the lightweight application-connection/raw-ingestion path.

1. Clone and install the locked dependencies:

```bash
git clone https://github.com/ankur-agarwal-38aa6766/trust-signal.git
cd trust-signal
uv sync --locked --extra dev --extra snowflake
cp .env.example .env
```

2. Edit `.env` with **your** organization-account identifier, dedicated service
   user, runtime role, pipeline warehouse and database names. The runtime role
   must not be `ACCOUNTADMIN`. Keep `TRUST_SIGNAL_PLATFORM=snowflake`; other
   platforms are not implemented. An account administrator is needed for setup.
   Explicitly exported environment variables override `.env` values, so remove
   stale settings from another account before proceeding.

3. Generate your own encrypted keys. The command uses the configured file paths,
   creates private directories/files, and refuses to overwrite existing credentials.

```bash
chmod 600 .env
uv run --locked --extra snowflake python -m trust_signal.persistence.keys \
  --env-file .env --public-key-file .secrets/snowflake_key.pub
```

4. Generate the setup SQL. This command does **not** connect or provision resources:

```bash
uv run --locked --extra snowflake python -m trust_signal.persistence.setup \
  --env-file .env --public-key-file .secrets/snowflake_key.pub \
  --output snowflake/build/setup.sql
```

Review `snowflake/build/setup.sql`, then execute it in **your account's**
Snowsight SQL editor using an authorized administrator role such as `ACCOUNTADMIN`.
It creates the configured database/warehouse, application schemas and tables,
service user and restricted ingestion grants. Do not reuse another installation's
user or overwrite its keys. The warehouse starts suspended; subsequent queries
can incur Snowflake charges. Existing objects are not automatically reconciled,
and setup DDL can partially commit. See [Portable Deployment](docs/portable-deployment.md).

5. Verify the connection and ingest a real Microsoft GLEIF record:

```bash
uv run --locked --extra snowflake python -m trust_signal.persistence.connection --env-file .env
uv run --locked --extra snowflake python -m trust_signal.ingestion.raw_export \
  --env-file .env --lei INR2EJN1ERAN0W5ZP974 \
  --expected-name "MICROSOFT CORPORATION" \
  --output-dir outputs/live/microsoft_gleif
```

Expect `session_reused: true` from the connection check, then
`load_status: verified_in_snowflake` and `run_status: succeeded` from ingestion.
This path uses actual official-source data, not synthetic evidence. Replay the
saved bundle without refetching to check sequential duplicate prevention:

```bash
uv run --locked --extra snowflake python -m trust_signal.ingestion.load \
  --env-file .env --bundle-dir outputs/live/microsoft_gleif
```

Expect `inserted_rows: 0` and `verified_rows: 1`. If a write fails, retain the bundle
and reconcile its stored result before retrying. Fresh-account provisioning has
not yet been independently live-tested; your trial helps validate these steps.
Never share `.env`, private keys, passphrases or API tokens. They and `outputs/`
are ignored by Git; `.env.example` is the shareable template.

## Local Workflow Demo

```bash
uv run --locked streamlit run app.py
```

The starter runs the identity-input gate, parallel demo specialist branches, comparison board, and review routing. Demo mode uses clearly labeled fixtures. Live GLEIF mode stores and verifies the raw registry response and source-run history in Snowflake before resolving identity and producing a finding. Full case persistence and scoring remain pending.

To run the JSON command-line workflow with local fixtures:

```bash
uv run trust-signal "Example Organization Ltd" --jurisdiction GB --registration-id 00000000
```

For a live exact GLEIF lookup, provide the LEI and opt into live mode:

```bash
uv run --locked --extra snowflake trust-signal "Bloomberg Finance L.P." \
  --lei 5493001KJTIIGC8Y1R12 --source-mode gleif_live --env-file .env
```

Without `--lei`, live mode searches by name and returns persisted candidates for
confirmation. It does not automatically select a candidate or calculate risk.

The preferred real-data path is the `.env` application setup above. Optional
OAuth/CLI examples are in the [source integration register](docs/source-integration-status.md).
The live registry branch now uses shared ingestion; demo fixtures remain local.
Persistent case processing beyond raw evidence and source runs remains pending.

To list source capabilities and ingest a real party independently of the UI:

```bash
uv run --locked --extra snowflake python -m trust_signal.ingestion.pipeline --list-sources --env-file .env
uv run --locked --extra snowflake python -m trust_signal.ingestion.pipeline \
  --requests examples/microsoft_identity.json --env-file .env \
  --output outputs/live/microsoft-identity.json
```

See [shared source ingestion](docs/source-ingestion.md) for the request format,
coverage meanings, Snowflake inspection query, and agent usage.

## Validation

```bash
uv run --locked --extra dev --extra snowflake pytest
uv run --locked --extra dev ruff check src tests app.py snowflake/app
```

## Design documents

- [Figma product and backend handoff](docs/figma-design-handoff.md): complete UI scope, personas, screens, stage/agent flows, backend mappings, readiness boundaries, and prototype acceptance criteria.
- [Figma design prompt](docs/figma-design-prompt.md): concise design-tool brief with current-backend and future-product journeys.
- [Snowflake initialization](docs/snowflake-initialization.md): complete repeatable onboarding, ordered SQL, migration checksums, service identity and safe activation boundaries.
- [Source connectors](docs/source-connectors.md): expanded adapters, live verification boundaries, event labels, access/rights gates and sample requests.
- [Snowflake workflow orchestration](docs/snowflake-orchestration.md): durable case/stage runs, reusable task graph, deployment artifacts, retries and recovery.
- [Research aggregation](docs/aggregation.md): standalone aggregator, comparison rules, evidence deduplication, timeline and component integration.
- [Shared source ingestion](docs/source-ingestion.md): registry, GLEIF discovery, verified JSON/XML storage, coverage and execution commands.
- [Entity resolution and evidence](docs/entity-resolution-and-evidence.md): implemented identity rules, provenance contracts, component flow, Snowflake integration and remaining work.
- [Source integration status](docs/source-integration-status.md): working versus planned connectors and the first real Microsoft/GLEIF raw-evidence load.
- [Complete implementation plan](docs/complete-implementation-plan.md): authoritative work packages, dependencies, repository changes, source integrations, UI requirements, Snowflake deployment, estimates, and acceptance criteria.
- [Complete system design and operating plan](docs/system-design.md): requirements, service boundaries, multi-agent runtime, scoring, security, deployment, reliability, evaluation, cost, risks, and release gates.
- [Global product and technical design](docs/product-and-technical-design.md): product scope, architecture, components, entity and evidence model, Snowflake roles, and end-to-end data flows.
- [Official source catalog](docs/official-source-catalog.md): global source families and an initial, researched registry list with access and freshness notes.
- [Implementation roadmap](docs/implementation-roadmap.md): hackathon MVP, delivery phases, acceptance criteria, and work sequence.
- [Current-state reconstruction specification](docs/current-state-reconstruction.md): detailed record of the existing codebase and its gaps; this describes inspected behavior, not the new target architecture.
- [Snowflake foundation](snowflake/README.md): initial database schema migration and account setup boundary.
- [Snowflake delivery blueprint](docs/snowflake-delivery-blueprint.md): account setup, deployment topology, connector choices, data flow, UI plan, operating controls, and delivery gates.

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

Implemented: source connectors/registry, raw JSON/XML evidence persistence,
source-run tracking, identity/evidence contracts and resolution, a reusable
key-pair Snowflake session, dotenv configuration, administrator-reviewed setup
SQL generation, and a local Python/LangGraph/Streamlit demo. Real Microsoft
ingestion and duplicate-free replay have been verified in DEV. Other connector
availability and live-test status are in the [source register](docs/source-integration-status.md).

Not ready yet: automatic `init/start` provisioning, an end-to-end persistent case
worker, risk scoring, deployed Cortex services, Tasks/dbt, a connected hosted
Streamlit reviewer UI, production tenant isolation, or non-Snowflake backends.
Generated schemas and deployment scaffolding do not mean those features are running.
