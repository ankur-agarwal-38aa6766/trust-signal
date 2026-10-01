# TrustSignal Implementation Roadmap

This roadmap turns the product design into a focused Snowflake COCO hackathon build and a credible path beyond the demo. Prioritize a complete evidence flow over superficial country counts.

System-level service boundaries, security, operations, testing, cost, and launch gates are detailed in [system-design.md](system-design.md).

## 1. Hackathon demo target

Demonstrate one company across at least two jurisdictions and show:

1. User submits a company name plus a jurisdiction or identifier.
2. TrustSignal resolves the legal entity and explains the identifier-based match; ambiguous identity pauses for user clarification.
3. The LangGraph orchestrator dispatches at least three specialist agents in parallel, such as registry, board, and news/sanctions research.
4. Each branch returns structured findings, evidence references, status, and source coverage to Snowflake; one failed branch does not erase other results.
5. The comparison board shows agreement, conflicts, chronology, duplicates, confidence, and gaps across agents.
6. A versioned scoring policy calculates dimensions and routes to more details, analyst review, monitor/approve recommendation, or reject recommendation.
7. The UI exposes evidence and rationale behind each result; a Cortex Agent answers follow-up questions over the stored case with citations.
8. Cortex Code (CoCo) is shown as part of the developer workflow used to build or refine SQL, connectors, tests, or agent configuration. CoCo is not presented as the production orchestrator.

Use actual API access the team has obtained. If a source requires credentials or approval that are unavailable, use a lawfully permitted sample or static official file and visibly label it as such. Never simulate a successful live source fetch.

## 2. Delivery phases

### Phase 0: Decide the demo and Snowflake account constraints

- Choose a primary entity and a second jurisdiction/source pair that the team can actually access.
- Confirm Snowflake account region, edition, Cortex feature availability, allowed models, outbound network rules, role grants, warehouses, storage/stage permissions, and hackathon constraints.
- Register CoCo CLI/Desktop access for the engineering workflow; keep Snowflake credentials in the approved local auth flow.
- Create a source access checklist for the selected APIs, including terms, rate limits, user agent, authentication, retention, attribution, and refresh expectations.

**Exit:** one selected vertical slice, confirmed source access, and a working Snowflake development connection.

### Phase 1: Contracts and Snowflake foundation

- Define source, source-run, raw-observation, entity, identifier, match, relationship, claim, event, evidence, case-run, agent-run, agent-finding, comparison-item, coverage, assessment, and case-action schemas from the technical design.
- Create separate raw, core, serving, and operations schemas and least-privilege roles.
- Define stable IDs and idempotency keys. Use source record ID plus source version/content hash; never identify an event solely by generated text.
- Build a small set of synthetic, explicitly labeled fixtures for deterministic validation and UI development.

**Exit:** migrations run in a development database; sample source records can be loaded and queried; no real secret or personal-data sample is checked into the repository.

### Phase 1a: Orchestrator and specialist contracts

- Keep `src/` as the Python source root and `src/trust_signal/` as the importable package (`import trust_signal`). Do not place application code directly in `src/` without a package namespace.
- Define `CaseRequest`, `ResolvedParty`, specialist branch state, branch envelope, comparison board, score explanation, and disposition schemas.
- Implement the case graph with an identity gate, parallel specialist nodes, distinct result keys, an explicit join barrier, partial/timeout handling, and durable run IDs.
- Implement a mock specialist for every lane first so the comparison and route paths can be demonstrated without inventing fake live-source results.
- Keep source connectors as reusable tools called by specialist agents. Keep Cortex Agent as analyst follow-up over stored outcomes; do not rely on model tool selection alone to guarantee all specialist branches ran.

**Exit:** a synthetic case demonstrates concurrent fan-out, isolated branch outputs, a completed comparison board, scoring, and each disposition route.

### Phase 2: Connector contract and ingestion

- Implement a typed source adapter contract: `health`, `search`, `fetch`, `parse_raw`, `checkpoint`, and source-specific freshness/access metadata.
- Implement the existing SEC and GLEIF adapters behind that contract; do not let workflow nodes own HTTP behavior.
- Add one new official registry adapter chosen from the researched catalog and actually authorized for the team.
- Add one official event source, preferably a structured sanctions list or regulator source with a documented file/API.
- Store raw observations before parsing; use content hashes, source record keys, retrieval timestamps, and connector versions.
- Choose file ingestion for bulk snapshots and Snowpipe Streaming for event-like input where its complexity is justified. An external connector must still poll or receive a source-side event.

**Exit:** repeated ingestion is idempotent, source errors are persisted, and a changed upstream record creates a new observation without deleting history.

### Phase 3: Entity resolution and event validation

- Normalize legal identifiers with jurisdiction-specific validators and preserve the original spelling/value.
- Use exact IDs as deterministic links; rank name/address candidates only with explicit features and confidence thresholds.
- Keep candidate resolution separate from accepted entity links. Send ambiguous matches to review.
- Extract event candidates with a structured Cortex AI output schema, retaining document/page/span references and model/version metadata.
- Validate identity, source class, dates, event/procedural state, duplicates, and evidence references deterministically.
- Build the comparison board from normalized agent findings; flag corroboration, contradictions, same-event duplicates, missing branches, and stale results.
- Implement versioned dimension scoring and a deterministic route policy. Missing identity evidence requests details; contradictory or incomplete material goes to review; only explicit validated hard-stop rules produce a reject recommendation.
- Add negative fixtures: same-name unrelated entity, stale article, withdrawn enforcement, duplicate syndicated stories, mismatched jurisdiction, allegation mistaken for finding.

**Exit:** every displayed event has source evidence and a match explanation; unverified candidates cannot enter verified-event views.

### Phase 4: Freshness, transformations, and serving views

- Build declarative core/profile/event/coverage transformations with Dynamic Tables where the SQL expression and freshness objective fit.
- Use Streams/Tasks or stored procedures for imperative API calls, notification actions, retries, or logic that Dynamic Tables do not express.
- Track per-source schedule, last success, publication-to-ingestion lag, failure category, and expected freshness.
- Build serving views for entity profile, evidence timeline, source coverage, and assessment explanations.
- Publish Cortex Search services over only the retained/licensed text and evidence excerpts intended for search.

**Exit:** entity profile and event timeline update after new ingestion; source coverage is visible, and raw observations remain append-only.

### Phase 5: Cortex Agent and product UI

- Define Cortex Agent tools for analyst follow-up: Cortex Analyst/serving views for case and event queries, plus Cortex Search for evidence documents.
- Keep the main case orchestration in the explicit TrustSignal LangGraph workflow so each specialist executes and joins as designed. Cortex Agent is the conversational layer over case results, not the system of record for branch completion or scoring.
- Write agent instructions requiring evidence references, procedural labels, freshness disclosure, and abstention when results are incomplete or ambiguous.
- Keep agent access read-only for the demo unless a specific write operation is required and separately authorized.
- Update Streamlit to consume Snowflake serving views and show legal identity, match quality, verified and unverified events, citation links, checked sources, freshness, and review notes.
- Remove claims of worldwide/live coverage where the underlying connector is not available.

**Exit:** a question such as "What changed, and what official evidence supports it?" yields citations that resolve to stored evidence records; the case status, comparison board, score, route, and Snowflake records agree.

### Phase 6: Evaluation, cost, and demo readiness

- Build a labelled evaluation set across jurisdictions, languages, entity types, and event/procedural states.
- Measure identity false-match rate, event citation validity, event classification quality, duplicate rate, and source freshness.
- Test replay, retry, pagination, source outage, rate limiting, malformed payload, and model timeout behavior.
- Capture Snowflake credit and Cortex token use by workflow; set warehouse auto-suspend and practical run limits.
- Prepare the hackathon walkthrough around a real entity, exact source evidence, source coverage, and one clearly shown update. Keep the source/mode/time visible throughout.

**Exit:** the demonstration can be replayed from stored observations; expected behavior and known coverage gaps are documented.

## 3. Recommended build order and boundaries

Keep these responsibilities distinct:

- **CoCo:** coding and Snowflake development assistance for engineers.
- **Cortex Agent:** deployed analyst-facing question answering over governed search and structured query tools.
- **Cortex Search:** retrieval over approved text evidence, not the legal-entity master record.
- **Cortex Analyst:** governed structured questions over profile, event, and coverage views.
- **Cortex AI:** extraction, classification, translation assistance, and concise summaries; output remains a candidate until verified.
- **Snowpipe Streaming / file loading:** ingest data that a connector has received.
- **Dynamic Tables:** declarative relational transformations with freshness goals.
- **Streams and Tasks:** change-driven or scheduled procedural work, external calls, custom retry and notification logic.
- **Source adapters:** jurisdictional HTTP/API/file access, source-specific pagination, terms, rate limits, and checkpoints.
- **TrustSignal application:** entity-resolution workflow, evidence presentation, analyst decisions, and alert subscription experience.

Do not place raw web crawling or uncontrolled external browsing inside the agent. Search tools should retrieve from reviewed source records and curated search indexes; source connectors control where data came from and how it may be reused.

## 4. API and internal event contracts

Prefer JSON contracts with explicit versions. A source observation should at minimum carry:

```json
{
  "schema_version": "1",
  "source_id": "uk_companies_house",
  "jurisdiction": "GB",
  "source_record_id": "company-number-or-record-key",
  "canonical_url": "https://official-source.example/record",
  "published_at": null,
  "modified_at": null,
  "observed_at": "2026-10-01T00:00:00Z",
  "ingested_at": "2026-10-01T00:00:02Z",
  "content_hash": "sha256:...",
  "payload_format": "application/json",
  "payload": {},
  "connector_version": "0.1.0"
}
```

An event response should return `entity_id`, `event_id`, `event_type`, `procedural_status`, `event_date`, `published_at`, `first_seen_at`, `match_confidence`, `verification_status`, `evidence[]`, and `limitations[]`. Citation entries contain `source_id`, `source_name`, `canonical_url`, `source_record_id`, `excerpt_or_document_reference`, `published_at`, `observed_at`, and `source_class`.

Never return an unsupported bare score or an uncited synthesized claim as if it were a registry fact.

## 5. Definition of done for the initial release

- A user can resolve at least one entity in two jurisdictions with stable official identifiers.
- At least one official identity connector and one official event connector run against accessible real sources; any fixture data is marked synthetic.
- Every raw observation has source, time, hash, and connector metadata in Snowflake.
- No event is labeled verified without identity and evidence validation.
- Search and agent answers include source citations that open the underlying record or artifact.
- UI shows source coverage and freshness with accurate unavailable/not-checked states.
- Rerunning the same source page does not create duplicate current events, and a source correction remains visible in history.
- Repository documentation names implemented connectors separately from planned catalog entries.
- CoCo usage is demonstrated as an engineering workflow; product runtime is implemented with Snowflake services and TrustSignal code.

## 6. Deployment plan

### Hackathon deployment

Use one Snowflake account and a dedicated development database/schema for the demo. Deploy the Streamlit app in Snowflake if the current UI dependencies and required Streamlit features are supported by the selected runtime. This keeps the first release close to the Snowflake data and avoids creating an unnecessary application platform. If the current console depends on unsupported components, keep it in a small external Streamlit host and connect to Snowflake using a scoped service identity.

Deploy the UI, source adapters, and Snowflake transformations as separate responsibilities:

1. **UI:** Streamlit in Snowflake, reading serving views and submitting search/review requests. The browser never holds source API credentials.
2. **Orchestrator:** Run the LangGraph case graph in a Python worker/service. For a single-user prototype it may be co-hosted with the Streamlit server; for a shareable demo deploy it separately so a browser refresh cannot lose a long-running case. Use Snowpark Container Services if enabled and practical in the hackathon account; otherwise use a small external container worker with scoped Snowflake authentication.
3. **Connectors:** For a small approved source set, run Python stored procedures on a schedule with narrowly scoped External Access Integrations and Snowflake Secrets. If connector runtime, dependency, or network needs do not fit that execution model, run the adapters as a separately deployed worker and write observations into Snowflake. Do not make a long-running fetch part of a page render.
4. **Ingestion:** Land small API responses through the connector into raw Snowflake tables. Use staged files/Snowpipe for snapshots and consider Snowpipe Streaming only for feeds where the added client/runtime complexity is justified.
5. **Transformations:** Use Dynamic Tables for declarative entity, event, and serving-view transformations. Use Tasks/Streams or procedures for polling, retries, notifications, and other imperative work.
6. **AI retrieval:** Provision Cortex Search and governed semantic views, then create a read-only Cortex Agent for analyst follow-up over completed cases.

### Environment promotion

| Environment | Purpose | Deployment rule |
|---|---|---|
| Local | UI, domain logic, and connector development with mocked or approved sample responses | No production credentials; tests use captured synthetic fixtures. |
| Snowflake DEV | Integration and source contract validation | Dedicated database/warehouse, limited source allowlist, short retention, synthetic and explicitly approved live records. |
| Snowflake DEMO / STAGING | Rehearsal against the exact demo source configuration | Deploy reviewed code and SQL; verify role grants, external access, Cortex services, freshness, and replay. |
| Production (later) | Multi-user monitored service | Separate roles, warehouses, secrets, source licenses, data retention, alert delivery, and operational ownership. Not required to claim a hackathon demo is production-ready. |

### Release sequence

1. Keep application code, `snowflake.yml`, source seeds, and SQL migrations in version control. Store secrets in Snowflake Secrets or the approved deployment secret manager; never in Git or Streamlit source.
2. Use CoCo during development to draft/refine code and SQL, then require a human review for migrations, grants, model prompts, and source-policy changes.
3. Apply database roles and schema migrations to DEV using a deployment role with only the required privileges.
4. Deploy the orchestrator worker, connectors, and Streamlit app from the reviewed commit. Snowflake CLI project definitions can declare Streamlit artifacts, grants, secrets, and external-access integrations.
5. Run connector health checks and a bounded end-to-end check: intake, identity resolution, parallel fan-out, raw landing, comparison board, scoring/routing, Cortex retrieval, and UI citations.
6. Promote the same reviewed commit and migration set to DEMO/STAGING; do not hand-edit a separate demo implementation.
7. Configure warehouse auto-suspend, source-specific schedules, task failure monitoring, connector lag alerts, and Cortex usage/cost checks.
8. Keep a rollback path for app code, SQL migrations, source configuration, and the last known-good Agent/Search definitions.

### Operational deployment notes

- External access integrations should allow only the hostnames and secrets each connector needs. Separate integrations by trust boundary where practical.
- Use separate Snowflake roles for ingestion, transformations, Agent/UI reads, and administration. Grant the Agent access only to serving views and approved Search services.
- Treat Streamlit in Snowflake owner-rights behavior and viewer access deliberately. If user-specific row access is required, use a supported caller-rights or external application pattern instead of assuming the UI automatically runs as the viewer.
- A source is "live" in the UI only when its connector is deployed, access has been approved, and its most recent run is within its stated freshness objective.
- Snowflake Tasks do not turn a registry into a push feed. Schedules must reflect the upstream API's terms and actual update cadence; report observed lag.
- Snowflake account features, network policy, region, edition, compute, and data egress requirements must be confirmed before selecting the exact hosting mode.

Snowflake references: [Streamlit deployment from Workspaces](https://docs.snowflake.com/en/developer-guide/streamlit/streamlit-in-workspaces/streamlit-in-workspaces-create-run), [Streamlit network/security controls](https://docs.snowflake.com/en/developer-guide/streamlit/object-management/security), [external network access](https://docs.snowflake.com/en/developer-guide/external-network-access/creating-using-external-network-access), and [Snowflake Git integration](https://docs.snowflake.com/en/developer-guide/git/git-setting-up).
