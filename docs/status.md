# Implementation status

Reviewed against the repository on 2026-10-15. This page reports implemented
behavior and the boundary to operational readiness. It is not a fresh live-source
or cloud verification. Read the [evidence ledger](verification/history.md),
[product scope](product/scope.md) and [delivery backlog](backlog/README.md) for
dated proof, accepted direction and remaining work.

The maintainer selected `ui/app.py` as the single user-facing application. Shared
settings live in `ui/streamlit/config.toml`. The target is provider-portable
Streamlit backed by managed procedures/jobs and DAG workflows. Snowflake is the
existing adapter foundation; Google Cloud is the requested next provider profile.
Neither is documented as a complete supported production deployment.
The target is provider-portable Streamlit with managed procedures/jobs and DAG
workflows. Hackathon obligations, trial-account workarounds and a required separate
always-running backend are no longer active requirements. Existing Snowflake code
is the first adapter, not proof of a complete supported deployment profile.

## Implemented Versus Operational

| Component | Implemented And Tested Locally | Remaining Operational/Product Boundary |
| --- | --- | --- |
| Identity | GLEIF discovery/exact lookup, typed candidates, scoped deterministic resolution and provenance gates | Name-only matches require confirmation; cross-registry mapping and multilingual evaluation remain |
| Source ingestion | Independent registry/connectors, exact RAW/chunk retention, readback and OPS coverage | Access/licensing gates, refresh, interrupted-run recovery and normalized CORE cache remain |
| Specialists | Sanctions, ownership/leadership, legal and news with replaceable providers; opt-in CLI fan-out after identity | Not injected into the Snowflake runtime; live persisted multi-specialist cases are not end-to-end verified |
| Aggregation | Explicit grouping, duplicate evidence, potential structured conflicts, explicit-date timeline and coverage | Event/syndication clustering, corrections and immutable case-version comparison remain |
| Validation | EvidenceValidator runs after aggregation in the local graph and durable stage runner; outputs can be persisted/reused | Structural/lineage validation does not reread RAW, verify claim truth or grant scoring eligibility |
| Assessment | Explicit unscored results, clarification and analyst-review routing | No approved scoring policy or risk engine; incomplete coverage never means low risk |
| Human review | ReviewService plus development SQLite persistence: rationale, snapshots, idempotency, versions, audit and supervisor reopen | Trusted actor context is not login/membership verification; production provider storage, authenticated wiring and outbox actions remain |
| Snowflake workflow | Five Python procedures, ten-task graph, queue/run/attempt repositories and reusable SQL templates | Historical restricted-path deployment is verified, not current specialist execution; managed end-to-end integration remains |
| Setup | Offline plan generation, ordered migrations/checksums, scoped grants, code upload and suspended tasks | Explicit administrator apply is separate; fresh cloud install/upgrade and complete provider capability verification remain |
| Streamlit | Selected reviewer/intake/queue/source/operations UI in `ui/app.py` | Durable intake/progress, authenticated review, measured telemetry, accessibility and hosting still need their integration gates |
| AI/provider portability | Provider/store injection and retained architecture boundaries | Application model extraction, retrieval/agents and alternative complete provider profiles are not implemented |

## Runtime boundaries

The live CLI uses the configured Snowflake evidence store and source APIs. It is
not the final managed-runtime topology. By default `gleif_live` performs identity
research only; specialists are explicitly enabled after confirmed identity.

| Enable | Optional Selection | Important Limits |
| --- | --- | --- |
| `--sanctions` | Repeat `--sanctions-source` | Defaults: UN entity entries, OFAC SDN, UK FCDO and EU financial sanctions; Australia is separately selectable. Name candidates are not authoritative identity or ownership/control screening. |
| `--ownership` | `--norway-organization-number` | Norway hint must be nine digits and does not confirm identity. GLEIF accounting relationships are not beneficial ownership. |
| `--legal` | Repeat `--legal-source` | Defaults: World Bank, FCA and corporate Gazette metadata. Courts are separately opt-in and remain permission-gated. Headlines do not establish guilt or legal finality. |
| `--news` | Repeat `--news-source` | GDELT and FCA metadata discovery; no article-body rights, automatic publisher trust or claim adjudication. |

All enable flags require `--source-mode gleif_live`. Selection flags require their
enable flag and reject duplicates. Without an LEI, discovery returns candidates and
requests confirmation; unresolved identity does not authorize specialist fan-out.
See the CLI help for exact source IDs:

```bash
uv run --locked --extra snowflake trust-signal --help
```

Example live invocation, **not an offline verification command**:

```bash
uv run --locked --extra snowflake trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --env-file .env \
  --sanctions --ownership --legal --news
```

This can fetch global snapshots, incur warehouse charges and encounter access/rate
limits. Run it only with approved access, source rights, private configuration and
budget. Its existence is not evidence that all four branches have been live verified.
Detailed contracts: [research](components/research.md),
[validation](components/validation.md) and
[human review](components/review.md).

## Verification Levels And Dates

- **Local tests:** baseline commit `0950e569c1f627521f288e79a84c4754829d48db` passed 365 tests in the working checkout and a clean archived tree on 2026-10-05. See [closure evidence](verification/history.md).
- **Live retrieval/readback:** [source register](verification/history.md) records 2026-10-03 source-specific retrieval, RAW hashes and OPS verification. It is historical evidence, not a fresh availability claim.
- **Replay:** Australia workbook and GDELT captured responses were parsed/stored from actual captured bytes; this differs from reliable fresh adapter HTTP. Fixture tests use synthetic data and are not live evidence.
- **Deployed operation:** [2026-10-03 report](verification/history.md) verified claim, failed-lookup handling and finalization in a restricted account; downstream research did not execute. [2026-10-04 trial report](verification/history.md) records additional bounded source-worker evidence, not complete managed case execution.
- **Current scope:** trial workarounds and hackathon obligations are not current release requirements. No source, cloud runtime, schedule or model service was reverified during the documentation consolidation.

Review and scoring remain distinct: a human command does not automatically make a
claim true, remove pending attribution, change evidence, assign a score or trigger
downstream business actions. No implementation document overrides source permissions,
tenant authorization or the approved release gates.

## Local verification commands

The evidence ledger records prior results. Run these against the current checkout
before making a new validation claim:

These require locked dependencies but no account credentials or source requests:

```bash
uv run --locked --extra dev --extra snowflake pytest
uv run --locked --extra dev ruff check .
uv run --locked trust-signal "Example Organization Ltd" --jurisdiction GB --registration-id 00000000
uv run --locked --extra snowflake python -m trust_signal.persistence.initialize --help
```

The case command uses the default `demo_fixtures` mode: its branches/evidence are
synthetic and its assessment is unscored. Help and tests do not establish cloud
permissions. Connection checks, ingestion, account apply and schedule activation
are deliberately excluded from offline verification.
