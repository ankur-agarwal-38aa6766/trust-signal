# Product scope and decisions

Current direction, reconciled on 2026-10-14. TrustSignal supports evidence-led
legal-organization research and human review for analysts, procurement/onboarding
teams, reviewers and installation operators. Global intent is delivered through
verified jurisdiction/source coverage, not universal completeness.

## Accepted direction

Streamlit is the sole user-facing application. Durable provider-managed procedures,
Python/SQL jobs and DAGs execute independently of browser sessions. Snowflake is an
existing adapter; Google Cloud is the requested next profile. Complete supported
profiles still require implementation and verification.

All UI/settings belong in top-level `ui/`. Shared backend components stay in
`src/trust_signal`; cloud-specific setup, command bindings and concrete integrations
belong inside each root provider folder. The selected UI is `ui/app.py`.
Backend/provider code moves remain pending; see [component layout](../architecture/components.md).

First Google delivery uses configured cloud identity/project/location and a trusted
single operator directly. Product signup, customer OAuth, provider selection and
hosted tenancy remain later scope. Credentials alone do not enable a provider.
The target of setup in a few minutes is unmeasured.

## Excluded scope

The hackathon scope is closed. Submission/deadlines and CoCo proof are removed
requirements. Snowflake trial/upgrade investigations and a mandatory separately
hosted always-running backend are also excluded. Cortex Code is development
assistance; application AI is optional and provider-portable. The code license is
still undecided, separately from source-data rights.

## Stable constraints


- Worldwide intent, jurisdiction-by-jurisdiction verified coverage; no universal coverage claim.
- Intake -> identity confirmation -> parallel specialists -> explicit aggregator ->
  comparison -> evidence validation/assessment -> human review and audited actions.
- Shared refresh/ingestion and per-case research are different workflows. Persist raw
  evidence and verify provenance before releasing normalized findings to agents.
- Independent connectors, storage, runtime, specialists, aggregation, validation,
  policy and review have replaceable interfaces; not every component needs a microservice.
- Streamlit is the sole user-facing surface. Durable UI integration remains pending; browser closure
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

## Retained scope and ownership

The [backlog manifest](../backlog/index.json) owns the complete `scope_coverage`
thought-to-task map; [backlog](../backlog/README.md) groups all 51 stable delivery
tasks. Existing acceptance criteria remain the delivery contract. Optional financial,
product/safety/cyber and business-conflict research have decision owners; they are
not enabled features. Business conflicts differ from contradictory source claims.
Optional transactions require a separately bounded extension before implementation.

## Decisions Still To Discuss


No final answer is assumed below. Each owning task must record decision, rationale,
alternatives, named owner, date, evidence and superseded decisions before implementation.

| Decision | Owner Task | Current Position |
| --- | --- | --- |
| First users/use case, entity types, first-release jurisdictions and non-goals | TS-035 | First users/entity types/jurisdictions undecided; worldwide is the long-term target |
| Code license, governance, release/support and disclosure responsibilities | TS-036 | Maintainer approval needed; source-data licensing separate |
| Product identity provider, membership, case/reviewer authority | TS-004 / TS-018 / TS-022 / TS-051 | Trusted context objects are not authentication |
| Scoring dimensions, thresholds, eligibility and human override | TS-018 / TS-019 / TS-020 | No approved score inferred from metadata |
| News provider, publisher rights and official-feed selection | TS-015 / TS-050 | Discovery metadata is not article-body permission |
| Next registries, legal sources and each jurisdiction's rights | TS-010 / TS-031 / TS-032 / TS-033 / TS-050 | Companies House/court gates stay intact |
| Optional models, retrieval/tools, region and per-installation budget | TS-023 / TS-024 / TS-025 | Verify capabilities; no assumed entitlement |
| Source refresh targets, notifications, quotas and cancellation | TS-009 / TS-028 / TS-043 | Define measurable bounded behavior |
| Personal-data purpose, retention, erasure and lawful audit | TS-040 | Operator/legal-policy review required; no generic legal default |
| Recovery objectives, edition/region support and restore procedures | TS-041 | Targets first; no replication enabled automatically |
| Supported provider profiles and first end-to-end portable runtime | TS-038 / TS-039 | Provider-neutral target; profile selection and implementations still require verification |
| Financial/operational/conflict specialist applicability | TS-044 / TS-045 / TS-046 | Choose scope; child issues before implementation |
| Supported UI locales and accessibility acceptance | TS-047 | Connected accessibility/localization acceptance remains |
| Public integration consumer, export rights and distribution format | TS-048 / TS-049 | No broad integration or marketplace commitment |
| Hosted tenants, BYO cloud, offboarding and billing | TS-051 | Optional; billing/control-plane requirements not approved |

Google profile selection is decided; service capabilities, implementation and
operational acceptance remain pending. Replace open decisions only with a dated,
named decision including rationale, alternatives, evidence and owning issue.
New decisions belong here; technical details belong in their component/profile guide.
Do not revive removed plans or invent policy defaults to make a preview look complete.
