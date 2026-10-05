# Figma Design Prompt: TrustSignal

Use this brief with the full
[product/workflow/backend handoff](figma-design-handoff.md). Deliver a Figma
design and clickable prototype, not an implemented application or a landing page.

## Product

Design **TrustSignal**, a global legal-entity research and monitoring workspace
for analysts, reviewers, requesters, operators, and auditors. Users submit a
company/organization, confirm its exact legal identity, inspect source-backed
research, compare conflicting claims, understand missing coverage, and eventually
make a documented review decision. The product is being built for a Snowflake
Cortex Code hackathon and uses portable Python components with Snowflake storage
and workflow infrastructure.

The design must communicate provenance and uncertainty, not imply that AI can
declare a company trusted or fraudulent. Global coverage is selective and visible.

## Main Flow

Intake -> input checks -> registry discovery/exact lookup -> identity confirmation
-> parallel sanctions / ownership & board / news & events / legal & regulatory
specialists -> join -> aggregation and comparison -> claim validation -> policy
assessment -> human review -> clarification, approval, monitoring, rejection, or
closure -> optional future monitoring and reassessment.

Unresolved identity stops specialist attribution. One failed branch becomes a
coverage gap. No match is not "all clear". Preserve case/run/version history.

## Current Backend Reality

- Built: source adapters/registry, verified raw-evidence retention, source-run
  logs, identity contracts/resolution, local LangGraph workflow, standalone
  aggregator, durable stage/run repositories, Snowflake procedures/task scaffolding.
- Four deployed specialist stages currently return skipped coverage outputs.
- Claim validation and risk scoring are not configured. Current scores are null.
- Hosted Streamlit is a scaffold; its legacy summary views are not automatically
  populated by the durable workflow. Use workflow result/progress projections.
- No implemented HTTP product API, durable reviewer-action service, monitoring,
  alert service, production tenancy, or deployed Cortex research assistant.
- Current trial-account approach fetches sources manually outside Snowflake and
  stores verified evidence inside it; durable task-graph integration is pending.
- CoCo supports development; it is not the application's current source crawler.

Annotate every design dependency as Built, Recorded DEV verification, Scaffold,
Planned, or Blocked. These annotations belong in Figma, not verbose product UI.
Create both **current-backend MVP** and **future complete product** prototype paths.

## Screens

1. Cases/work queue: compact searchable/filterable table, state, jurisdiction,
   identifiers, coverage gaps, recommendation, score availability, last update.
2. New case: legal name, jurisdiction, LEI or registration ID/authority, optional
   website, address, aliases; inline validation and name-first discovery.
3. Identity confirmation: official candidate comparison, match reasons,
   identifiers, source links, conflicts, resubmission/correction.
4. Research progress: identity gate and four parallel stage rows; attempts,
   sources checked, timing, findings, coverage limitations.
5. Case overview: compact entity header, assessment, coverage, important findings,
   conflicts, events; current mode shows "Not scored" with reasons.
6. Comparison board: claim/value/source matrix with consistent claims, potential
   conflicts, duplicate evidence, combined members, and unstructured claims.
7. News/events: publisher, language, dates, source link, identity attribution,
   procedural status; metadata/links unless full content rights are approved.
8. Ownership/board: relationship table and optional inspectable graph, parent
   types, role dates, exceptions, source evidence. Unknown is not zero ownership.
9. Legal/sanctions: separate listings, candidate matches, measures, notices,
   allegations, proceedings, judgments, debarment, and final decisions.
10. Evidence explorer: claim, citation, observation/source-run IDs, response hash,
    connector version, timestamps, verification scope, limitations.
11. Review: planned permission-gated actions with rationale, confirmation,
    version checks, and audit receipt. Recommendations are not final decisions.
12. Monitoring/alerts: future subscriptions, source cadence, changes, before/after
    evidence, reassessment, delivery failures.
13. Sources: capabilities, jurisdictions, actual coverage, access/rights gates,
    last success, freshness, errors, connector version.
14. Operations/setup: privileged attempts/recovery, connection readiness,
    migration/runtime state, cost/residency gates; no credentials in analyst UI.

## Backend Mapping

Current integration is Python/CLI and Snowflake SQL/Snowpark, not REST.
Canonical objects: `CaseRequest`, `IdentityResolution`, `BranchResult`, `Finding`,
`AggregationResult`, `Assessment`, `CaseResult`, `WorkflowInputFailure`.

Submission scaffold: `TRUST_SIGNAL_CORE.CASE_REQUESTS`.
Read results: `TRUST_SIGNAL_SERVE.V_WORKFLOW_RESULTS` (`RESULT` JSON).
Read progress: `TRUST_SIGNAL_SERVE.V_WORKFLOW_PROGRESS`.
Read source health: `TRUST_SIGNAL_SERVE.V_SOURCE_HEALTH`.
Legacy `V_CASE_SUMMARY`/`V_CASE_FINDINGS` need normalized publication before they
can represent durable workflow reports. Tenant filtering alone is not sufficient
authorization; server-side identity and access policies are required.

Design proposed API/action dependencies only as future contracts. Never put
Snowflake keys, passwords, or admin privileges in a browser integration.

## Sources and Trust Rules

Current adapters include GLEIF, Norway registry, UN/OFAC/UK/EU/Australia sanctions,
World Bank debarment, FCA newsroom, Gazette, gated Find Case Law, and GDELT.
Companies House is paused; SEC and broader national registries remain planned.
Adapters/list snapshots are not completed entity-specific screening specialists.
Source coverage and verification boundaries must remain visible.

Every claim opens evidence. Keep event, publication, retrieval, and ingestion
times separate. Do not fabricate missing dates, scores, matches, directors,
ownership percentages, source results, independent corroboration, or AI reasoning.
Source text is untrusted. Do not show hidden chain-of-thought.

## Visual Direction

Quiet professional operational UI. Table-first, organized density, restrained
neutral surfaces with teal/blue actions, amber gaps, red conflicts, limited green
confirmed states. No hero, stock-photo decoration, gradient orbs, nested cards,
dominant purple theme, or oversized dashboard typography. Use icons with accessible
names/tooltips, familiar controls, small radii, and stable layout dimensions.

Build reusable Auto Layout components and token variables. Design 1440, 1024,
and 390-width frames, keyboard/focus states, non-color status indicators, and
WCAG 2.2 AA contrast. Preserve entity/case context when opening evidence drawers.
Use real product structures; label any prototype-only data visibly.

## Required States and Prototype Journeys

Empty/queued/running; multiple candidates; name conflict; missing record; source
unavailable; partial paging; rate limit; license blocked; skipped branch; stale
data; unknown storage outcome; interrupted retry; not scored; permission denied;
stale review version; future monitoring/export failure.

Click through exact identity to unscored report/evidence; name-first clarification;
source-gap completion; comparison to conflicting evidence; future reasoned review;
future monitored change; privileged reconciliation; account readiness with gates.
No invented completion percentage, automatic clean result, or unsupported live API.

## Deliverables

Figma pages: Brief & Readiness, Foundations, Components, Analyst MVP, Review &
Monitoring, Operations & Setup, Responsive & Edge States, Engineering Contracts.
Include screen inventory, reusable component variants, linked prototype journeys,
data/command annotations, built-vs-planned labels, permission matrix, and unresolved
product decisions. The full handoff defines field mappings and acceptance criteria.
