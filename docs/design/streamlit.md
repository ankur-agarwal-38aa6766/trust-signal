# Streamlit experience specification

This is the single screen/interaction design reference. [ui/app.py](../../ui/app.py)
is the selected application; [UI README](../../ui/README.md) owns launch settings.
[Status](../status.md) owns implemented behavior and
[architecture](../architecture/overview.md) owns application flow.

The native Streamlit implementation now follows the supplied Stitch/Figma HTML
screens: shared header/navigation, identity intake, reviewer dossier, queue, source
cards and operations graph. Widgets and callbacks remain native Streamlit; no page
iframe is used. The supplied screen PNG exports are failed-fetch placeholders, so
the exported HTML is the visual reference.

Current intake calls the existing application-service boundary, which runs the
local graph. Candidate selection, local filters and CSV/JSON downloads are wired;
sample operational and review actions remain explicitly identified previews.
Dossier/queue/source/operations content includes illustrative data. Submitted
results render separately from the sample dossier and its score. Named actors and
sample Cortex health wording do not prove
scoring, authentication, model execution or measured telemetry. The target connects
these same screens to durable provider commands/read projections.

Analysts inspect evidence, reviewers record authorized rationale, requesters supply
clarification, auditors read history, and operators manage privileged recovery/setup.
These are target roles; trusted context types do not implement login/membership.
First configured Google delivery uses one trusted operator; signup/hosted tenancy is
separate. Application screens stay provider-independent.

Mark design dependencies as implemented, illustrative, planned or access-blocked.
Current deterministic specialists and structural validation exist. Claim adjudication,
scoring, authenticated production review, monitoring and cited AI answers remain gates.
Approval/monitoring/close controls are proposed additions beyond current ReviewService.

## Screen specifications

### A. Cases / Work Queue

Default application screen. Use a compact table with legal name, jurisdiction,
identifier, identity state, workflow state, score availability, recommendation,
coverage gaps, last update, and case/run reference. Proposed assignment and review
due-date columns require new backend support.

Provide New case, search, filters, sortable columns, pagination, saved-view design,
and a clear row-to-detail action. Design queued, running, needs information,
completed with gaps, awaiting review, and failed variants. Saved views, assignment,
and several queue states are planned, not existing persisted enums.

Do not hide all queued cases simply because no legacy `CASES` row exists yet.
The queue reader needs authorized request data as well as workflow projections.

### B. New Case / Intake

Use legal name as required, jurisdiction and identifiers as strongly encouraged.
Expose LEI or registration ID + authority, plus optional website, registered
address, and aliases. Support name-first discovery as a distinct route, not proof
of identity. Optional organization type, case purpose, scope, and attachments are
planned extensions, not current `PartyInput` fields.

Show relevant source coverage before submission; unsupported regions do not get
a promise of comprehensive checks. Inline errors follow current lengths:
legal name 2-240; LEI exactly 20; jurisdiction 2-8; registration ID/authority
up to 120; website up to 500; registered address up to 1000 characters.
Trim blank optional fields to null. Alias and URL validation need further backend
rules; do not imply the current contract already verifies them.

### C. Identity Confirmation

Use a comparison table rather than a conversational guess. Columns: official
legal name, aliases, jurisdiction, LEI, registry identifier/authority, address,
source, match status, reason codes, and evidence link. Show submitted input next
to the official record. Offer select candidate, edit details, and inspect source.

Current matches expose name similarity and attribution eligibility, not a
calibrated probability. Never label similarity as "99% verified identity".
Selecting a candidate is a planned durable UI command: the current backend
supports explicit LEI resubmission, not a finished candidate-confirmation API.

### D. Research Progress

Show a stable stage diagram or list with the four parallel branches visibly
sharing the identity gate. Each branch shows status, timing, attempt, sources,
findings, and limitations. Detail expands to an operator-safe run summary.
Do not invent completion percentages or exact remaining time. A source response
can be stored while later attribution/validation is still pending.

### E. Case Overview

Persistent compact entity header: official name, jurisdiction, identifiers,
case/run IDs, identity state, last refresh. Below: assessment state, recommendation,
coverage summary, material findings, conflicts, and latest events.

Risk, identity confidence, claim verification, and source coverage are different
dimensions. Do not compress them into one "trust" number. Today show an unscored
assessment with reasons; a future score panel must state scale direction, policy
version, assessment time, factor contributions, and coverage constraints.

### F. Comparison Board

Group rows by subject, claim key, event/effective period, and evidence mode.
Show claim value, branch, source, event date, verification/procedural state,
finding references, duplicate grouping, and relation. Expand side-by-side evidence.

Map current relations exactly:

| Backend value | Display label | Interpretation |
| --- | --- | --- |
| `consistent_claims` | Consistent claims | Matching normalized assertions; not proof of independent corroboration |
| `potential_conflict` | Potential conflict | Different values for an explicitly single-valued claim in the same scope |
| `duplicate_evidence` | Duplicate evidence | Repeated content/claim; retain all references |
| `combined_members` | Combined members | Multiple valid members, such as different directors; not contradiction |
| `unstructured_claims` | Requires inspection | Free text grouped without semantic truth/contradiction inference |

Different event dates and different entities must not collapse into a conflict.
Unknown dates stay unknown. Conflict resolution and reviewer notes need a future
write contract; current aggregation is read-only and preserves original claims.

### G. News & Events

Rows include title, publisher, language, event date if known, publication time,
retrieval time, event/procedural classification, identity-match state, and citation.
Use metadata and links until document rights permit more. Full article text,
publisher images, translations, clustering, and fraud classification are not
automatically licensed or implemented. An official announcement is not necessarily
a final enforcement decision. Syndicated coverage must not inflate evidence counts.

### H. Ownership & Board

Table-first relationships with optional graph: entity/person, role, direct or
ultimate parent, source, effective dates, current/historical flag, identifiers,
and exceptions. Graph nodes open evidence details. Distinguish accounting parent
relationships from legal ownership percentages and beneficial ownership.
Never infer a director, ownership percentage, or sanctions ownership-rule result
from an absent field. Missing public disclosure is not "no owner".

### I. Legal & Sanctions

Separate sanctions, debarment, insolvency, litigation, investigations, and
enforcement. Show authority, jurisdiction, subject identifiers, aliases, measures,
dates, proceeding/reference IDs, and procedural status. Label candidate matches
as candidates pending identity review. Do not brand an entity fraudulent because
it appears in a search result, snapshot, allegation, or unrelated proceeding.

### J. Evidence Explorer

Reusable drawer/full-page inspector linked from every finding. Show claim and
subject, source/canonical URL, source record ID, finding ID, observation IDs,
source-run ID, connector version, response hash, verification scope, procedural
status, event/publication/retrieval/ingestion times where available, and limitations.
Authorized operators may inspect retained raw content or chunks through a future
read interface; do not expose unrestricted RAW SQL or private payloads to analysts.
Render external content as escaped text, not executable HTML.

### K. Review & Decision

Proposed controls: request more information, send for analyst review, approve,
approve with monitoring, reject, close, or override with rationale. Require
permissions, mandatory reasons, current run/policy version, confirmation for
consequential actions, and append-only audit records. Current disposition enums are recommendations. Development SQLite review exists;
production persistence/authentication and connected controls remain pending.

Keep future controls disabled or clearly separated in implementation-preview
designs. A dialog closing or a toast appearing is not a persisted decision.

### L. Monitoring & Alerts

Planned watchlist with source-specific freshness, scope, owner, next expected
check, latest change, and subscription state. Alert detail compares previous and
new evidence, summarizes impact, and links to reassessment. Design snooze,
acknowledge, assign, unsubscribe, delivery failure, and stale-data states with
explicitly planned contracts. Do not promise continuous coverage everywhere.

### M. Sources and Coverage

Table: source, authority/provider, jurisdiction, operations, source class,
configured/access state, last fetch, last success, expected cadence, checked scope,
coverage, failure category, connector version, rights restrictions. Filters by
jurisdiction, purpose, capability, and availability. Show both catalog capability
and actual case-specific checked coverage; they are not interchangeable.

### N. Operations and Account Readiness

Privileged views for request/run IDs, latest stage attempts, retry history,
sanitized errors, task-root/schedule state, queue backlog, source failures, and
storage verification. Current backend supports operator recovery, not an analyst
"retry all" button. Requeue requires quiescence and creates a new run.

Setup design: prerequisites -> private configuration -> keys -> reviewed plan ->
administrator apply -> read-only checks -> bounded real-source smoke -> readiness
report. Keep secret entry out of general application screens; show masked status
and credential references only. Scheduling, spending, account-wide AI residency,
and external access require administrator approval, never automatic UI activation.
## Status and failure vocabulary

Keep display labels separate from persisted values. Do not write a proposed
UI state into an existing enum without changing the contract.

| Domain | Current values / behavior | Display rule |
| --- | --- | --- |
| Case result | `needs_more_information`, `completed`, `completed_with_gaps` | A completed run can still be unscored and require review |
| Branch result | `completed`, `failed`, `skipped` | Skipped is not a clean result |
| Stage attempts | `running`, `succeeded`, `completed_with_gaps`, `skipped`, `failed` | Show latest attempt and retain history |
| Source coverage | `available`, `no_matches`, `partial`, `blocked`, `failed` | No matches only describes checked source scope |
| Identity resolution | `resolved`, `ambiguous`, `needs_review`, `no_match` | Show reasons and retained candidates |
| Candidate match | `confirmed`, `candidate`, `conflict`, `no_match` | Avoid certainty inflation |
| Evidence mode | `live_source`, `demo_fixture` | Prominent, unambiguous mode separation |
| Disposition | `request_details`, `analyst_review`, `monitor_recommendation`, `reject_recommendation` | Recommendation, not saved final decision |
| Score | Null plus explicit `score_status` | "Not scored" with reasons; never substitute zero |

Required prototype variants: empty installation; no cases; submission queued;
malformed input; multiple candidates; exact-match conflict; no record; identity
source unavailable; skipped specialist; partial paging; HTTP 429; blocked license;
stale snapshot; storage outcome unknown; interrupted attempt; unconfigured scoring;
permission denied; stale review version; failed export; monitoring delivery failure.

For an unknown storage outcome, direct an operator to reconciliation. Do not
offer an unconditional automatic retry that could duplicate writes. One branch
failure remains visible while other branches finish. Previously reviewed evidence
remains accessible when a new run fails.
## Backend binding

No product REST API is implemented. Current contracts live in
[models](../../src/trust_signal/models.py), [identity](../../src/trust_signal/domain/identity.py),
[workflow](../../src/trust_signal/domain/workflow.py) and
[review](../../src/trust_signal/domain/review.py). A provider application binding must
authorize submit/confirm/read/review commands and supply persisted case versions.

Snowflake's workflow result/progress projections are
`TRUST_SIGNAL_SERVE.V_WORKFLOW_RESULTS` and `V_WORKFLOW_PROGRESS`.
Legacy `V_CASE_SUMMARY`/`V_CASE_FINDINGS` are not populated from workflow JSON
automatically. Source capability differs from case-specific checked coverage;
configuration presence differs from actual access. A tenant filter alone is not
authorization. See [workflow operations](../operations/snowflake-workflows.md).

Use code-owned tool events/citations, not fabricated agent-thinking transcripts or
hidden reasoning. External content renders as escaped text. Source/claim identity,
procedural status, coverage and assessment remain separate visual dimensions.

## Visual and accessibility rules

- Quiet operational design: compact navigation, scanning-friendly tables,
  constrained typography, and unframed page sections. No marketing hero.
- Neutral white/gray surfaces; restrained teal/blue actions; amber gaps;
  red conflicts/failures; green only for a specifically completed/confirmed state.
  No dominant single-hue theme or decorative gradients/orbs.
- Use Auto Layout, component variants, constraints, and variables/tokens.
  Standard frame targets: 1440 desktop, 1024 compact/tablet, 390 mobile.
- Keep table density useful; use a drawer for evidence and a full-page view
  where comparison requires width. Mobile keeps priority columns and explicit
  expansion rather than crushing every table column into tiny text.
- Icons for familiar tools with accessible names/tooltips; tabs for views;
  checkboxes/toggles for binary settings; menus for option sets. Radius <= 8px
  unless a future established design system dictates otherwise.
- Persistent context, stable stage rows, explicit timestamps/time zones,
  keyboard navigation, visible focus, non-color status cues, WCAG 2.2 AA target.
- Never obscure a source gap behind a generic success notification.
- Use text such as "Identity confirmed", "Potential match", "Partial coverage",
  "Source unavailable", "Not scored", "Analyst review recommended".
- Avoid "Trusted company", "Fraud detected", "All clear", or "Globally verified"
  unless a reviewed, precisely scoped evidence/policy contract justifies the claim.
- Use actual product tables, evidence, timelines, and sourced assets only where
  rights permit. Avoid decorative stock imagery in the research workspace.
## Prototype acceptance

### Required Journeys

1. Exact company identifier -> confirmed identity -> source coverage -> unscored
   result -> evidence inspection. Microsoft/GLEIF is the reference real-source path.
2. Name-first search -> multiple candidates -> inspect identifiers -> resubmit
   explicit identity -> research. Preserve original request/run history.
3. Name/identifier conflict -> no specialist fan-out -> request correction.
4. Confirmed identity -> one blocked/failed source -> other branches finish ->
   completed-with-gaps view with an explicit unscored assessment.
5. Comparison -> potential conflict -> side-by-side evidence -> reviewer note;
   note persistence is a planned capability.
6. Review recommendation -> reasoned decision -> audit receipt; clearly future.
7. Watched entity -> new official event -> version comparison -> reassessment;
   clearly future.
8. Operator failure -> inspect attempts -> quiesce/reconcile -> authorized requeue;
   not an unrestricted analyst retry.
9. New account -> generated reviewed plan -> smoke check -> partial/full readiness;
   never silently turn on recurring compute.

### Acceptance Checklist

- Every actionable finding opens its provenance and original source reference.
- Identity cannot be implied by name similarity or the existence of a raw response.
- All prototype screens identify built/scaffold/planned/blocked dependencies in
  designer annotations; product screens avoid explanatory architecture essays.
- Risk score is null/"Not scored" throughout current-backend journeys.
- No clean outcome is inferred from skipped, failed, blocked, or partial checks.
- Candidate confirmation, decisions, exports, and monitoring have explicit
  pending write/query contracts rather than invented existing APIs.
- Queue/progress/results use request/workflow projections, not exclusively legacy
  normalized tables that the current runtime does not publish.
- Read-only analysts do not see credentials, RAW payloads by default, or recovery
  controls. Multi-tenant sharing is blocked until policies/auth are implemented.
- Dates distinguish occurrence, publication, retrieval, ingestion, and decision;
  absent timestamps are not invented.
- Desktop/mobile, loading/empty/error, permissions, stale versions, and partial
  completion states are all represented and reachable in the prototype.

This specification includes future screens. A clickable prototype or toast does not
prove persisted actions. TS-027/047 own connected UI and accessibility acceptance;
use [scope decisions](../product/scope.md#decisions-still-to-discuss) for unresolved
roles, jurisdictions, policies, locales and export rights.
