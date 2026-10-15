# Delivery backlog

This is the single human-readable backlog entrypoint. The machine-readable
[manifest](index.json) owns task scope, dependencies, priorities, acceptance
criteria, verification requirements and GitHub issue mapping. Individual task
files are implementation handoffs. GitHub owns current assignment and delivery
state; `initial_status` in the manifest is historical publication metadata.

The manifest contains 51 stable tasks. As checked on 2026-10-14, TS-001 / issue
#2 is closed and the other 50 issues are open. Recheck GitHub before reporting
current state. A passing test, document, generated plan or adapter stub does not
complete a task whose acceptance criteria require live or operational evidence.

## Delivery workstreams

Workstreams make the backlog navigable; task dependencies remain authoritative.
They replace the previous roadmaps, work-package plan and milestone suggestions.

### Product and contracts

| Task | Priority | Area | Deliverable |
| --- | --- | --- | --- |
| [TS-001](TS-001.md) — closed | P0 | Foundation | Freeze and verify the implementation baseline |
| [TS-030](TS-030.md) | P1 | Documentation | Reconcile current README and implementation status documents |
| [TS-035](TS-035.md) | P1 | Product | Decide open-source release scope and record architecture decisions |
| [TS-036](TS-036.md) | P1 | Community | Establish open-source licensing, contribution and maintenance policies |
| [TS-037](TS-037.md) | P1 | Contracts | Version component contracts and verify adapter compatibility |

### Durable runtime and provider delivery

| Task | Priority | Area | Deliverable |
| --- | --- | --- | --- |
| [TS-002](TS-002.md) | P0 | Orchestration | Connect research stages to durable provider-managed workflows |
| [TS-003](TS-003.md) | P0 | Ingestion | Persist normalized evidence and add a cached research provider |
| [TS-004](TS-004.md) | P0 | Security | Implement trusted application identity and tenant authorization |
| [TS-005](TS-005.md) | P1 | Intake | Implement durable intake and clarification services |
| [TS-008](TS-008.md) | P1 | Ingestion | Add bounded source retries and interrupted-run recovery |
| [TS-021](TS-021.md) | P1 | Review | Implement provider-portable review persistence and versioned snapshots |
| [TS-022](TS-022.md) | P1 | Review | Expose authenticated review commands and operational actions |
| [TS-029](TS-029.md) | P1 | Delivery | Automate CI and reproducible provider-profile installation checks |
| [TS-038](TS-038.md) | P1 | Onboarding | Implement safe fork-and-install onboarding and environment diagnostics |
| [TS-039](TS-039.md) | P2 | Providers | Implement provider-neutral workflow, storage and model adapter boundaries |

### Evidence research and assessment

| Task | Priority | Area | Deliverable |
| --- | --- | --- | --- |
| [TS-006](TS-006.md) | P1 | Identity | Implement scoped cross-registry identifier mapping |
| [TS-007](TS-007.md) | P2 | Identity | Evaluate multilingual names and alias query planning |
| [TS-010](TS-010.md) | P2 | Sources | Implement the next official national registry adapter |
| [TS-011](TS-011.md) | P1 | Sanctions | Extract authoritative sanctions identifiers with locators |
| [TS-012](TS-012.md) | P2 | Sanctions | Implement bounded related-party sanctions evaluation |
| [TS-013](TS-013.md) | P1 | Ownership | Resolve related organizations and role holders independently |
| [TS-014](TS-014.md) | P1 | Legal | Retrieve permitted primary notices and verify procedural roles |
| [TS-015](TS-015.md) | P1 | News | Document news rights and extend approved newsroom coverage |
| [TS-016](TS-016.md) | P1 | Aggregation | Implement event clustering and syndication-aware comparisons |
| [TS-017](TS-017.md) | P1 | Aggregation | Implement corrections and immutable case-version comparison |
| [TS-018](TS-018.md) | P0 | Validation | Implement evidence-backed claim review and eligibility |
| [TS-019](TS-019.md) | P0 | Quality | Create labeled identity/event evaluation and release gates |
| [TS-020](TS-020.md) | P1 | Scoring | Implement reviewed versioned scoring and routing policies |
| [TS-031](TS-031.md) | P2 | Sources | Activate Companies House only after approved API access |
| [TS-032](TS-032.md) | P2 | Sources | Resolve court computational-analysis permission |
| [TS-033](TS-033.md) | P2 | Sources | Expand official legal/adverse-event sources by jurisdiction |

### Operations and release assurance

| Task | Priority | Area | Deliverable |
| --- | --- | --- | --- |
| [TS-009](TS-009.md) | P1 | Ingestion | Implement source snapshot refresh and publication freshness |
| [TS-025](TS-025.md) | P0 | Governance | Complete approved security, residency and cost readiness |
| [TS-026](TS-026.md) | P0 | Integration | Verify full live cases across two jurisdictions |
| [TS-028](TS-028.md) | P2 | Monitoring | Implement incremental monitoring and idempotent notifications |
| [TS-034](TS-034.md) | P1 | Operations | Implement worker health, metrics and actionable alerts |
| [TS-040](TS-040.md) | P1 | Privacy | Implement approved evidence retention, redaction and deletion lifecycle |
| [TS-041](TS-041.md) | P1 | Recovery | Define disaster recovery targets and verify backup restoration |
| [TS-042](TS-042.md) | P1 | Security | Threat-model source, agent, plugin and deployment boundaries |
| [TS-043](TS-043.md) | P1 | Operations | Define service targets, quotas and durable cancellation semantics |
| [TS-050](TS-050.md) | P1 | Sources | Govern source coverage, licensing changes and connector deprecation |

### Connected Streamlit experience

| Task | Priority | Area | Deliverable |
| --- | --- | --- | --- |
| [TS-027](TS-027.md) | P2 | UI | Build the connected analyst intake-to-review UI |
| [TS-047](TS-047.md) | P2 | UI | Specify accessible and localized Streamlit review workflows |

### Optional capabilities and distribution

| Task | Priority | Area | Deliverable |
| --- | --- | --- | --- |
| [TS-023](TS-023.md) | P1 | AI | Integrate governed model extraction as reviewable candidates |
| [TS-024](TS-024.md) | P2 | AI | Implement case-scoped retrieval, semantic tools and research agents |
| [TS-044](TS-044.md) | P2 | Financial | Scope official financial filings and disclosure research |
| [TS-045](TS-045.md) | P2 | Operational | Scope official product, safety and cyber-event research |
| [TS-046](TS-046.md) | P2 | Conflicts | Decide and scope contextual business conflict-of-interest research |
| [TS-048](TS-048.md) | P2 | Distribution | Decide release packaging and optional Snowflake Native App distribution |
| [TS-049](TS-049.md) | P2 | Interop | Scope external integrations and portable case evidence exports |
| [TS-051](TS-051.md) | P2 | Tenancy | Scope installation and tenant lifecycle administration |

P0 is delivery or safety critical, P1 is core completion, and P2 is later or
decision-gated work. Priority never bypasses dependencies, permissions, source
rights or verification requirements.

## Current execution order

1. Use the accepted TS-001 checkpoint and keep TS-030 documentation synchronized.
2. Complete bounded contract cleanup and provider construction boundaries under
   TS-037/038/039 while preserving current Snowflake behavior.
3. Close durable execution, normalized evidence/cache, authorization and recovery
   foundations through TS-002/003/004/005/008/021.
4. Wire and verify the existing specialists in one approved provider profile, then
   complete claim review/evaluation before any scoring policy is enabled.
5. Connect the shared Streamlit UI to durable submit/read/review operations and
   satisfy operational, privacy, security, restore and release gates.
6. Add optional models, documents, monitoring, sources, integrations and hosted
   tenancy only through their existing decision and acceptance owners.

This order is a practical path through existing dependencies, not a new task list.
Google Cloud is the requested next profile, but its service design does not replace
shared TS acceptance criteria or imply provider support.

## Contributor workflow

1. Read the task, dependency tasks, [status](../status.md), and relevant component
   guide. Confirm the GitHub issue state, assignment, external permissions and
   fixture/replay/live evidence needed.
2. Assign the GitHub issue and record In Progress. Use a focused branch and link
   the actual GitHub issue number; TS IDs are repository identifiers.
3. Preserve identity, provenance, coverage, tenant and unscored-default contracts.
   Implement the bounded acceptance criteria and meaningful failure/replay tests.
4. Open a PR with exact commands/results and the verification boundary. Update
   task scope, manifest, remote issue and current docs together when scope changes.
5. Close only after every criterion has reviewed evidence. A merged PR, passing
   fixtures or successful resource creation may still leave live gates open.

Use this issue checkpoint format:

```text
Status: In Progress | In Review | Blocked
Implemented: <change and branch/PR>
Verified: <commands/results; fixture/replay/live/deployed boundary>
Remaining: <unchecked acceptance criteria>
Blocker: <owner and unblock condition, or none>
Next: <one concrete action and completion check>
```

## Shared guardrails

- Never commit secrets, private keys, raw personal data or ignored evidence.
- Cloud/account/schedule changes, paid access and recurring spend require explicit
  approval and profile-specific readiness checks.
- Preserve unknown, partial, stale, failed and blocked coverage. Never label
  fixtures or captured replay as fresh live evidence.
- Confirm trusted actor, installation and tenant context for exposed reads/writes.
- Keep source rights, provenance, structural validation, claim adjudication,
  scoring and business decisions as separate gates.
- Do not infer legal guilt, beneficial ownership, clean risk or universal coverage
  from a name match, headline, empty query or unsupported source.
- Preserve stable IDs, hashes, input/policy versions and reviewer history across
  retries, upgrades and provider migration.

## Backlog maintenance

Reuse an existing owner whenever scope is already covered. Split independently
testable provider/source extensions into linked child issues only after recording
capability, rights, dependencies and acceptance evidence. New stable TS IDs require
manifest, task file, publication mapping and scope-coverage updates.

The [scope register](../product/scope.md) owns decisions; its detailed thought-to-task
coverage is stored once in `index.json`. The [documentation index](../README.md)
defines topic ownership. Do not create a second roadmap, plan or status ledger.
