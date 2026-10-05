# Open-Source Scope And Future Decision Register

Recorded 2026-10-04 from the maintainer's direction and inspected repository designs.
This is the durable entrypoint for retained thoughts; the chat is not a delivery dependency.
It is not a claim that all possible future requirements have been discovered.

## Direction And Authority

The hackathon scope is closed, not declared successfully implemented. Submission,
deadline, demo recording and CoCo-contribution proof are no longer release gates.
TrustSignal continues as a worldwide open-source legal-entity research solution.
The code license still needs maintainer selection (TS-036); public-source access
does not grant redistribution rights. Snowflake remains the first supported
platform in the existing implementation and Cortex Code remains development assistance,
not a required runtime connector. The target architecture is provider-portable.

Scope clarified on 2026-10-05: Streamlit is the sole user-facing application;
approved provider-managed procedures, Python/SQL jobs and DAG workflows execute
research. Hackathon obligations, Snowflake trial/upgrade workarounds and a separately
hosted always-running backend service are excluded. Existing Snowflake code is an
adapter to preserve, not a platform requirement. The unpublished trial-feasibility
draft was withdrawn; it is not an active task. No provider is claimed supported
until its complete profile has passed verification.

Read this register, [project context](project-context.md), [baseline](baseline.md)
and [backlog](development-backlog.md). Code/tests and dated live evidence establish
behavior; published issues own scope and delivery status. Existing 34 tasks remain
valid and are not rebuilt by this expansion. Older hackathon plans and estimates
are historical design context, not current promises or requirements.

## Stable Product And Architecture Constraints

- Worldwide intent, jurisdiction-by-jurisdiction verified coverage; no universal coverage claim.
- Intake -> identity confirmation -> parallel specialists -> explicit aggregator ->
  comparison -> evidence validation/assessment -> human review and audited actions.
- Shared refresh/ingestion and per-case research are different workflows. Persist raw
  evidence and verify provenance before releasing normalized findings to agents.
- Independent connectors, storage, runtime, specialists, aggregation, validation,
  policy and review have replaceable interfaces; not every component needs a microservice.
- Streamlit is the sole user-facing surface. UI remains deferred; browser closure
  must not stop durable backend execution or lose case state.
- Distinguish identity candidates, allegations, proceedings, final decisions and
  source contradictions. No unsupported fraud verdict or automatic clean score.
- Treat partial/stale/blocked/failed/not-applicable coverage explicitly; retrieval
  time is not publication time and repeated reporting is not independent corroboration.
- Provider adapters must prove capabilities, retention, isolation, restart/replay
  and cost boundaries. Prior trial/local-worker reports remain historical evidence,
  not active deployment requirements or a prescribed topology.
- Fork-and-install onboarding separates UI, runtime, storage and local commands;
  plans do not mutate accounts, and apply/paid/schedule changes need explicit approval.
- Source and model content are untrusted; AI proposes reviewable grounded candidates,
  not identity authority, authorization context or legal truth.

## Retained Thoughts And Owning Work

| Thought | Owning Tasks | Status / Boundary |
| --- | --- | --- |
| Preserve and publish the existing implementation | TS-001 / TS-030 | Uncommitted baseline is not a remotely reproducible release |
| Live integration and release proof | TS-025 / TS-026 / TS-029 | Verify approved account readiness, two-jurisdiction cases, replay and clean installation; not a hackathon submission gate |
| Durable fan-out, case handoff, normalized evidence and replay | TS-002 / TS-003 / TS-008 / TS-021 | Foundations exist; deployed end-to-end acceptance remains |
| Intake, confirmed identity and multilingual aliases | TS-005 / TS-006 / TS-007 | Names cannot authorize attribution |
| Source expansion, sanctions, ownership, board roles, legal events and news | TS-010 / TS-011 / TS-012 / TS-013 / TS-014 / TS-015 / TS-031 / TS-032 / TS-033 / TS-050 | Choose bounded sources and verify rights, identifiers and live readback |
| Comparison, duplication, corrections and immutable history | TS-016 / TS-017 | Distinct from truth validation and business conflicts |
| Validation, evaluation, versioned scoring and reviewer authority | TS-018 / TS-019 / TS-020 / TS-022 | Policy choices need owner approval; no score from insufficient coverage |
| Cortex extraction, Search, semantic tools and Agent | TS-023 / TS-024 / TS-025 | Account/model/residency/cost and grounded tool verification required |
| Monitoring, refresh, notifications, health and alerts | TS-009 / TS-028 / TS-034 / TS-043 | Source-specific targets; no uniform real-time claim |
| Connected Streamlit UI and accessibility/localization | TS-027 / TS-047 | Later; preserve design without claiming connected completion |
| Open-source scope, decision rationale, license and maintainer responsibilities | TS-035 / TS-036 | Discussion/selection first; no license invented |
| Portable contracts, independent reuse and safe schema upgrades | TS-037 | Implement conformance and old-snapshot compatibility tests |
| Fork setup, diagnostics, capability checks and safe upgrades | TS-029 / TS-038 | Clean-install/readback required; not just environment variables |
| Provider-neutral DAG, Python/SQL execution, storage and optional AI | TS-002 / TS-037 / TS-039 | Active architecture direction; select and implement bounded profiles, no unverified multi-cloud support claim |
| Streamlit workflow trigger, DAG progress, attempts and final results | TS-005 / TS-027 / TS-034 | Durable session-independent runs; execution success differs from coverage and assessment |
| Operational/object/analytical storage and provider migration | TS-003 / TS-021 / TS-039 / TS-041 | Preserve transactions, IDs, hashes and decision history across approved adapters |
| Privacy, retention, correction/deletion and source revocation | TS-040 / TS-050 | Approved policy plus propagation across stored/indexed/exported copies |
| Disaster recovery and restore drills | TS-041 | Choose targets; retries alone do not establish recovery |
| Threat model, secrets, supply chain and operational limits | TS-036 / TS-042 / TS-043 | Extend existing security/CI tasks; measure and verify |
| Financial disclosures and filings | TS-044 | Scope/source decision before connector/specialist child issues |
| Product/safety/cyber operational events | TS-045 | Scope/source decision; don't infer liability from an incident |
| Business conflicts of interest | TS-046 | Optional contextual product feature, not shared directors = wrongdoing |
| Release packaging and possible Snowflake Native App | TS-048 | Select packaging; Native App is optional and unapproved |
| External APIs, signed integrations and portable evidence export | TS-049 | Scope a first consumer; enforce rights and tenant boundaries |
| Tenant/customer lifecycle and BYO-cloud control plane | TS-004 / TS-051 | Self-hosting first; hosted control plane remains optional |

All TS IDs resolve through the [backlog index](development-backlog.md). Their GitHub
numbers differ; the machine-readable manifest maps exact URLs and dependencies.

## Decisions Still To Discuss

No final answer is assumed below. Each owning task must record decision, rationale,
alternatives, named owner, date, evidence and superseded decisions before implementation.

| Decision | Owner Task | Current Position |
| --- | --- | --- |
| First users/use case, entity types, first-release jurisdictions and non-goals | TS-035 | Undecided; worldwide is the target, not first-release coverage |
| Code license, governance, release/support and disclosure responsibilities | TS-036 | Maintainer approval needed; source-data licensing separate |
| API identity provider, membership, case/reviewer authority | TS-004 / TS-018 / TS-022 / TS-051 | Trusted context objects are not authentication |
| Scoring dimensions, thresholds, eligibility and human override | TS-018 / TS-019 / TS-020 | No approved score inferred from metadata |
| News provider, publisher rights and official-feed selection | TS-015 / TS-050 | Discovery metadata is not article-body permission |
| Next registries, legal sources and each jurisdiction's rights | TS-010 / TS-031 / TS-032 / TS-033 / TS-050 | Companies House/court gates stay intact |
| Cortex models, retrieval/tools, region and per-installation budget | TS-023 / TS-024 / TS-025 | Verify capabilities; no assumed entitlement |
| Source refresh targets, notifications, quotas and cancellation | TS-009 / TS-028 / TS-043 | Define measurable bounded behavior |
| Personal-data purpose, retention, erasure and lawful audit | TS-040 | Operator/legal-policy review required; no generic legal default |
| Recovery objectives, edition/region support and restore procedures | TS-041 | Targets first; no replication enabled automatically |
| Supported provider profiles and first end-to-end portable runtime | TS-038 / TS-039 | Provider-neutral target; profile selection and implementations still require verification |
| Financial/operational/conflict specialist applicability | TS-044 / TS-045 / TS-046 | Choose scope; child issues before implementation |
| Supported UI locales and accessibility acceptance | TS-047 | UI deferred; original evidence remains available |
| Public integration consumer, export rights and distribution format | TS-048 / TS-049 | No broad integration or marketplace commitment |
| Hosted tenants, BYO cloud, offboarding and billing | TS-051 | Optional; billing/control-plane requirements not approved |

## Picking Work Without This Chat

1. Read the owning task, dependencies and baseline. Determine whether it is a
   decision, implementation or verification task; Ready is not cloud permission.
2. Assign an owner and capture a decision before coding where selection is open.
3. Split optional provider/source features into bounded child issues with contracts,
   rights, applicability, tests and live-readback requirements. Deferred is not forgotten.
4. Link PRs, commands/results and approvals; keep local issue bodies, manifest and
   remote issue scope synchronized. Fixtures, replay and live account evidence differ.
5. Update this map and affected decision records. No task is complete merely because
   a document, adapter stub, SQL template or issue exists.

No commit, publication of source files, production approval or license grant is
implied by this register. TS-001 still owns the reviewed baseline commit/push.

The 2026-10-05 coverage audit maps 23 retained themes to owning tasks in
`docs/backlog/index.json` under `scope_coverage`. Tests verify ownership references
and the excluded scope. This covers the visible conversation and inspected plans,
not unseen discussions or requirements that have not yet been supplied.
