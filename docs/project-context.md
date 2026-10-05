# Project Context And Decision Index

Recorded on 2026-10-04. This preserves the project's intent and engineering
decisions without requiring the chat transcript. It is a curated context record,
not a verbatim archive or a guarantee that every historical thought is captured.

## Original Intent

TrustSignal began with a Snowflake Cortex Code hackathon goal. On 2026-10-04 the
maintainer closed that scope and redirected the project toward a maintained,
open-source, worldwide evidence-led trust/review solution for legal parties,
companies and organizations. Hackathon submission, deadlines and CoCo proof are
not active release obligations. Snowflake remains the first supported integration;
open source does not imply an approved code license or unrestricted source-data rights.
On 2026-10-05 the maintainer clarified that the target is provider-portable:
Streamlit triggers and monitors durable provider-managed procedures/jobs and DAGs.
Snowflake trial investigations and separately hosted backend-service deployment
are excluded. Existing Snowflake integration remains reusable, not mandatory.
See the [future scope and decision register](future-scope.md) for the complete
retained thought-to-task map and explicit deferred decisions.
The earlier US-oriented implementation is a starting point, not the market boundary.

A user supplies party information. Identity is resolved before independent specialist
research runs in parallel. Results cover news, sanctions/fraud-related evidence,
legal events, ownership, board/organizational roles and other supported dimensions.
An explicit aggregator produces comparison, conflicts, duplicates, chronology and
coverage. Validation precedes a versioned assessment; a human can review, request
more information or reject with an audit trail. Refresh/monitoring is part of the
target product, not a completed real-time service today.

## Preserved Decisions

| Thought Or Decision | Current Interpretation | Where To Continue |
| --- | --- | --- |
| Worldwide rather than US-only | Roll out official sources jurisdiction by jurisdiction; expose coverage gaps instead of claiming universal coverage | [Catalog](official-source-catalog.md), TS-010/033 |
| Legal party information as input | Names discover candidates; authoritative scoped identifiers confirm identity before attribution | [Identity](entity-resolution-and-evidence.md), TS-005/006/007 |
| Independent, portable components | Provider/store protocols separate fetching, persistence, specialists, aggregation, validation, assessment and review | [System design](system-design.md), baseline component docs |
| Aggregator must be explicit | Standalone comparison service, not hidden scoring logic inside the orchestrator | [Aggregation](aggregation.md), TS-016/017 |
| Parallel multi-agent research | Local branch fan-out exists; shared ingestion is serialized per session; current specialists are deterministic, not deployed LLM agents | [Orchestration](snowflake-orchestration.md), TS-002/023/024 |
| Board, parent relationships and conflicts | Keep role holders and related parties independent; consolidation is not beneficial ownership; distinguish business conflicts from conflicting source claims | [Ownership](ownership-specialist.md), TS-012/013/016 |
| Fraud/risk evidence | Allegations and headlines cannot become fraud verdicts; preserve procedural state, party role and source confidence | [Legal](legal-specialist.md), TS-014/018/020 |
| News and actual updates | GDELT discovery is bounded metadata; licensed content, publisher policy and additional official feeds remain separate work | [News](news-specialist.md), TS-009/015/028 |
| Scoring followed by human review | No current score; structural validation is not claim truth; future policy consumes explicitly eligible evidence | [Validation](evidence-validation.md), [review](human-review.md), TS-018/020/021/022 |
| Provider-portable solution | Preserve current Snowflake adapters; workflow, storage, SQL/Python runtime and model choices are independent supported-profile capabilities | TS-002/003/021/023/024/037/038/039 |
| CoCo usage | Cortex Code is development assistance, not a production source connector or the application's research engine | [Technical design](product-and-technical-design.md), TS-023/024 |
| UI later | Backend first; preserve the analyst/reviewer design, but do not mistake a prototype/design for connected UI | [Figma handoff](figma-design-handoff.md), TS-027 |
| Simpler source layout | The question about using only src/ was considered; the documented current choice is src/trust_signal as an importable package, with independent component boundaries | [Technical design](product-and-technical-design.md), current source tree |
| Baseline must survive handoff | Existing implementation is the accepted starting point; do not rebuild it or silently remove safety behavior | [Baseline](baseline.md), TS-001 |

TS identifiers link through the [backlog index](development-backlog.md); published
GitHub issue numbers are different and recorded in [the manifest](backlog/index.json).

## Source And Operational Decisions

- Companies House verification is deliberately paused until approved API access.
- GLEIF supports name discovery, exact lookup and accounting relationships/exceptions.
- Norway supports organization identity and roles; personal data in raw responses
  requires restricted access and retention, even when normalization omits it.
- UN, OFAC SDN, UK, EU financial sanctions and Australia have distinct adapters/scopes.
  Direct matching does not implement every sanctions list or ownership/control rule.
- World Bank, FCA, Gazette and court metadata retain procedural/eligibility distinctions.
  Court computational-use permission is an external gate, not a toggle to bypass.
- News discovery does not grant article-body rights or publisher credibility.
- Australia capture replay and GDELT rate-limit boundaries are distinct from successful
  live adapter operation. Preserve dated [verification reports](source-integration-status.md).
- Trial deployment uses an external source worker with Snowflake persistence; the
  worker-to-case handoff is still incomplete. Root schedules remain inactive until
  readiness approval. See [deployment decisions](deployment-readiness.md).
  This is historical account context only, not active trial-workaround scope.
- Budget, account-wide changes, inference geography, source rights and schedule
  activation need explicit approval. Existing DEV controls are not production readiness.
- ReviewService's trusted actor contract is not login or tenant-membership verification.
  SQLite is a development adapter, not the planned production Snowflake review store.

## Wider Scope Retained, Not Silently Dropped

The [technical design](product-and-technical-design.md) also discusses filings,
financial disclosures and operational events. The [system design](system-design.md)
retains policy dimensions, onboarding/monitoring use cases, privacy, data residency,
retention, recovery, evaluation and release requirements.

Not every broad design topic is a ready-to-build adapter or approved product feature.
When taking these topics forward, create bounded child issues under the appropriate
source, specialist or platform task, with source rights, jurisdiction, acceptance
criteria and evaluation. Do not infer implementation completion from a design heading.

## Open Decisions To Keep Visible

1. Primary buyer/use case and which organization/entity types to support first.
2. First jurisdictions beyond the current sources and their approved source rights.
3. Production news provider and permitted storage/display/full-text access.
4. Claim-review authority, evidence requirements and independently reviewed scoring policy.
5. Production identity provider, tenant membership, reviewer permissions and case ownership.
6. Approved Cortex features/models, residency, account capability and inference budget.
7. Source-specific update SLAs, retention, disaster-recovery targets and notification channels.
8. Open-source release boundaries, licensing, maintainership and supported deployment profiles.

Open questions are not silently resolved by implementing a convenient default.
Record each decision's rationale, owner, date and affected issue before changing policy.

## Document Authority And Preservation

- Code/tests establish implemented behavior; [baseline](baseline.md) states its boundaries.
- [Backlog](development-backlog.md) and published issues define remaining delivery work.
- Product/system/implementation designs preserve target architecture and wider scope.
- Dated source/deployment reports establish historical observations, not current availability.
- GitHub Issues/Project, once configured, own assignments and delivery status.
- Update this index when requirements or important decisions change; use a new linked
  issue for scope not already covered. Preserve superseded decisions with dates/reasons.

The delivery issue bodies are published remotely, but the complete code/design baseline
and this context record still need the TS-001 commit/push checkpoint. Remote issues
are not a backup of uncommitted source files. No tag, commit or push is implied here.
