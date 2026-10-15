# Component boundaries and provider layout

The current ownership decision places all UI in `ui/`, shared algorithms/contracts
in `src/trust_signal`, and provider setup, command/read bindings, SDK/SQL adapters
and native deployment resources inside root `snowflake/` or `google_cloud/`.
There are no provider-specific UI copies. The backend code relocation is planned.

## Current dependency gaps

The reusable resolver, aggregator, injected specialists, StageRunner and review
service already have useful interfaces. Independence is incomplete because mixed
modules also contain cloud factories, SQL generation or concrete stores.

| Finding | Current evidence | Required boundary |
| --- | --- | --- |
| Cloud selection is embedded in environment reading | [config.py](../../src/trust_signal/config.py) merges dotenv/environment and rejects every platform except Snowflake | Separate value loading, selected-profile validation and adapter construction; continue rejecting unsupported profiles before connections |
| Registry research bootstraps its own cloud | [agents/registry.py](../../src/trust_signal/agents/registry.py) reads `.env`, calls application_stores and builds a default source registry when no pipeline is supplied | Require an injected ingestion capability in the reusable specialist; preserve convenience setup through an entry-point compatibility wrapper |
| Portable ingestion imports concrete stores | [ingestion/pipeline.py](../../src/trust_signal/ingestion/pipeline.py) contains both the core pipeline and a Snowflake-specific CLI/main | Keep pipeline computation separate from CLI/configuration factories |
| Interfaces import their implementations | [persistence/source_runs.py](../../src/trust_signal/persistence/source_runs.py) and [identity.py](../../src/trust_signal/persistence/identity.py) define protocols alongside Snowflake/CLI classes and imports | Put protocols and lifecycle values in pure modules; concrete SQL/SDK classes depend on those contracts |
| Evidence preparation generates Snowflake SQL | [ingestion/observation.py](../../src/trust_signal/ingestion/observation.py) combines exact-byte/hash checks and stable IDs with table names, SQL literals and chunk statements | Shared preparation returns verified bytes/identity/metadata; Snowflake SQL/chunk layout belongs to its storage adapter |
| Replay/export are tied to Snowflake targets | [load.py](../../src/trust_signal/ingestion/load.py) accepts an ObservationStore but also requires a Snowflake target table and writes `verified_in_snowflake`; [raw_export.py](../../src/trust_signal/ingestion/raw_export.py) exports provider SQL | Separate a portable evidence bundle/receipt from provider-specific loading artifacts; preserve old bundles/CLI behavior through versioned compatibility |
| Research provider interfaces bring in the pipeline | [research/provider.py](../../src/trust_signal/research/provider.py) defines ResearchProvider and PipelineResearchProvider together, importing IngestionPipeline | Keep the interface/data contract pure; move the ingestion-backed implementation behind an adapter |
| Review service contains development storage | [research/review.py](../../src/trust_signal/research/review.py) also implements SQLiteReviewStore | Keep review semantics separate from SQLite and future production stores |
| Generic orchestration folder owns cloud deployment | [snowflake_runtime.py](../../src/trust_signal/orchestration/snowflake_runtime.py) and [deployment.py](../../src/trust_signal/orchestration/deployment.py) are Snowflake-specific | Separate shared stage behavior from native runtime handlers and deployment generation |
| Selected UI still invokes the local backend directly | [ui/app.py](../../ui/app.py) runs synchronously and stores the result in session state | Use the same selected UI with a backend command/read contract; provider-specific connection/query wiring belongs in its provider backend |
| Source-specific live mode is treated as a runtime requirement | [models.py](../../src/trust_signal/models.py) exposes `gleif_live`; StageRunner translates `configured_sources` into that mode | Keep deployment profile, source selection and fixture/live evidence mode separate; evolve with versioned aliases, not a breaking rename |

The AST scan's broad research/screening/agents/ingestion/orchestration groups can
reach Snowflake connection/settings/store modules. Some of that is intentional
adapter code within a mixed folder; some is transitive through interface imports.
It is not a claim that every specialist opens a connection when imported. Cloud
connections are generally opened lazily. The restructuring should make imports and
construction independent as well as keep network execution explicit.


## Target placement

Provider Python modules below are planned; current shared backend modules retain their existing paths.
Add each adapter only when implemented and verified. Existing public import paths,
CLI commands and deployment handlers should remain compatibility wrappers during
incremental moves.

```text
ui/                                    shared top-level UI, never inside src/providers
  app.py                               single selected final Streamlit UI
  run.py                               launcher applying relocated shared settings
  streamlit/
    config.toml                        moved from .streamlit/config.toml
snowflake/                             complete Snowflake provider boundary; no UI
  bootstrap/                          existing installation templates plus planned runtime wiring
  application/                        planned provider command/read bindings
  adapters/                           planned concrete stores/workflow/model integrations
  setup/, migrations/, procedures/, tasks/, ...
google_cloud/                          complete Google provider boundary; no UI
  bootstrap/                          planned direct configured-account setup/runtime wiring
  application/                        planned provider command/read bindings
  adapters/                           planned PostgreSQL/Storage/Workflows/Vertex integrations
  infrastructure/, workflows/, deployment/

src/trust_signal/
  domain/                               shared typed contracts
  models.py                             existing public contracts; later compatibility facade
  connectors/                           official/approved source adapters and source requests
  ingestion/                            fetch -> verify -> persist -> release components
  resolution/                           entity matching and identity evidence
  screening/                            deterministic sanctions screening and its contracts
  agents/                               reusable specialist research
  aggregation/                          comparison, conflicts, chronology and coverage
  research/                             validation/review services and research contracts
  orchestration/                        stage definitions, handlers and workflow contracts
  persistence/                          pure storage contracts, receipts and lifecycle values

  cli.py                                existing CLI, selects/injects backend dependencies
  config.py                             environment values; cloud validation moves to provider
```

Provider infrastructure and concrete integration code remain inside the corresponding
provider locations. A backend component receives a store or research interface and
does not need to know which provider supplies it. Cloud-independent helpers can stay
with their existing backend component rather than be copied into every provider.

The provider folders are physical ownership boundaries, not the import names of the
cloud SDKs. Provider packaging must use distinct module names such as
`trust_signal_snowflake` and `trust_signal_google_cloud`; do not shadow the installed
`snowflake` SDK with an application package of the same name. Package discovery,
workflow uploads and compatibility wrappers need verification during the actual
backend move. Keep the shared package independently installable and cloud SDKs in
the provider distributions.

Provider groups may start with small modules until they need more structure.
Do not fill this target with empty implementations or mandatory dependencies for
unused services. Preserve today's folders for stable components rather than rename
every feature just to obtain a uniform tree.


## Composition rules

Bootstrap reads validated installation settings, constructs clients/stores and
injects them into shared components. Runtime construction is separate from resource
provisioning. Application bindings expose typed submit/confirm/read/review operations
to the UI using installed stores and trusted actor context; this interface is planned
and does not require an HTTP server. Adapters implement the component's required
contract using concrete database, workflow, secret or model services.

Interfaces live with their consuming component and must import without concrete
cloud implementations. SQL execution stays internal to an adapter. Core components
receive dependencies rather than discover accounts or credentials. A GLEIF source
adapter stays shared regardless of the hosting provider.

Preserve current public imports, CLI names, handler paths, persisted schemas and
bundle compatibility through incremental moves. Provider distributions need distinct
import names, such as `trust_signal_snowflake`, to avoid shadowing the Snowflake SDK.
Verify packaging, optional dependencies and code uploads during implementation;
do not create empty target packages as evidence of completion.

One native engine owns each run; stage jobs call shared computations without starting
another full graph. Keep source selection, cloud profile and demo/live evidence mode
as separate axes. Unsupported profiles fail before connection, without fallback.

Retain IngestionPipeline's whole-run serialization for a shared session. Different
pipeline instances sharing a session are not protected by the same lock. A concurrency
change needs ownership, transaction/write/readback and competing-writer tests first.

Boundary cleanup and conformance are owned by [TS-037](../backlog/TS-037.md),
onboarding by [TS-038](../backlog/TS-038.md), and provider implementation by
[TS-039](../backlog/TS-039.md). [Backlog](../backlog/README.md) owns sequencing;
[Google profile](../deployment/google-cloud.md) owns its service-specific design.
