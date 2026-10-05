# Development Backlog And Handoff

The [2026-10-04 baseline](baseline.md) is the starting point. Remaining work is
split into issue-ready tasks, not a request to rebuild existing components.
Read the [context and decision index](project-context.md) first to retain the
original vision, constraints, parked scope and unresolved questions.

## Repository Artifacts

- [Machine-readable backlog](backlog/index.json): stable IDs, priorities, areas,
  dependencies, external blockers, acceptance criteria and verification requirements.
- `docs/backlog/TS-*.md`: complete issue bodies with starting paths and guardrails.
- `.github/ISSUE_TEMPLATE`: task and bug forms for future contributors.
- `.github/PULL_REQUEST_TEMPLATE.md`: implementation and verification checklist.

All task IDs are repository identifiers, not GitHub issue numbers. On 2026-10-04,
all 51 tasks were published as [GitHub issues](https://github.com/ankur-agarwal-38aa6766/trust-signal/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement),
with priority and initial Ready/Blocked labels plus linked dependencies. Exact URLs
and issue numbers are recorded in `backlog/index.json` and each task file.
Source links use `master`. Assignees remain unset; no milestones or GitHub Project
have been created. The baseline includes uncommitted work; complete
[TS-001 / issue #2](https://github.com/ankur-agarwal-38aa6766/trust-signal/issues/2)
before presenting a Git commit as the full handoff baseline. New source-file links
may not resolve on GitHub until the baseline files are committed and pushed.

## Backlog

The hackathon scope is closed. The [future scope and decision register](future-scope.md)
captures the open-source direction, retained thoughts, optional expansion and
unresolved decisions. TS-035 through TS-051 supplement rather than replace the
existing seven-stage delivery tasks. Discussion tasks must record a decision;
optional source/provider features need bounded child issues before coding.

Scope clarification on 2026-10-05: provider-portable Streamlit plus managed
procedures, Python/SQL jobs and DAG workflows. Trial-account investigations and
separately hosted backend-service deployment are excluded; Snowflake is an existing
adapter, not a required platform. The unpublished trial-feasibility draft was withdrawn.
The manifest's `scope_coverage` maps 23 conversation/design themes to delivery
owners. Existing tasks were strengthened rather than adding duplicate issues.

| ID | Priority | Area | Work |
| --- | --- | --- | --- |
| [TS-001](backlog/TS-001.md) | P0 | Foundation | Freeze and verify baseline |
| [TS-002](backlog/TS-002.md) | P0 | Orchestration | Durable provider-managed research workflows |
| [TS-003](backlog/TS-003.md) | P0 | Ingestion | Normalized CORE storage and cached providers |
| [TS-004](backlog/TS-004.md) | P0 | Security | Trusted application identity and tenant authorization |
| [TS-005](backlog/TS-005.md) | P1 | Intake | Durable intake/clarification services |
| [TS-006](backlog/TS-006.md) | P1 | Identity | Scoped cross-registry mapping |
| [TS-007](backlog/TS-007.md) | P2 | Identity | Multilingual matching and alias planning |
| [TS-008](backlog/TS-008.md) | P1 | Ingestion | Bounded retries and interrupted-run recovery |
| [TS-009](backlog/TS-009.md) | P1 | Ingestion | Refresh and publication freshness |
| [TS-010](backlog/TS-010.md) | P2 | Sources | Next official national registry adapter |
| [TS-011](backlog/TS-011.md) | P1 | Sanctions | Authoritative sanctions identifiers |
| [TS-012](backlog/TS-012.md) | P2 | Sanctions | Related-party/rule evaluation |
| [TS-013](backlog/TS-013.md) | P1 | Ownership | Independent related-party resolution |
| [TS-014](backlog/TS-014.md) | P1 | Legal | Primary notices and procedural roles |
| [TS-015](backlog/TS-015.md) | P1 | News | Rights and approved official feeds |
| [TS-016](backlog/TS-016.md) | P1 | Aggregation | Event/syndication clustering |
| [TS-017](backlog/TS-017.md) | P1 | Aggregation | Corrections and case-version comparisons |
| [TS-018](backlog/TS-018.md) | P0 | Validation | Evidence-backed claim review/eligibility |
| [TS-019](backlog/TS-019.md) | P0 | Quality | Labeled evaluation and release gates |
| [TS-020](backlog/TS-020.md) | P1 | Scoring | Versioned policies and explanations |
| [TS-021](backlog/TS-021.md) | P1 | Review | Provider-portable review persistence |
| [TS-022](backlog/TS-022.md) | P1 | Review | Authenticated commands and outbox actions |
| [TS-023](backlog/TS-023.md) | P1 | AI | Optional governed model extraction |
| [TS-024](backlog/TS-024.md) | P2 | AI | Provider-independent retrieval, tools and agents |
| [TS-025](backlog/TS-025.md) | P0 | Governance | Security, residency and cost readiness |
| [TS-026](backlog/TS-026.md) | P0 | Integration | Live two-jurisdiction case verification |
| [TS-027](backlog/TS-027.md) | P2 | UI | Connected analyst UI, deliberately later |
| [TS-028](backlog/TS-028.md) | P2 | Monitoring | Incremental refresh and notifications |
| [TS-029](backlog/TS-029.md) | P1 | Delivery | CI and reproducible provider-profile setup |
| [TS-030](backlog/TS-030.md) | P1 | Documentation | Reconcile historical/current status docs |
| [TS-031](backlog/TS-031.md) | P2 | Sources | Companies House activation, access-blocked |
| [TS-032](backlog/TS-032.md) | P2 | Sources | Court permission, externally blocked |
| [TS-033](backlog/TS-033.md) | P2 | Sources | Global official legal/event source expansion |
| [TS-034](backlog/TS-034.md) | P1 | Operations | Worker health, metrics and actionable alerts |
| [TS-035](backlog/TS-035.md) | P1 | Product | Decide open-source release scope and record architecture decisions |
| [TS-036](backlog/TS-036.md) | P1 | Community | Establish open-source licensing, contribution and maintenance policies |
| [TS-037](backlog/TS-037.md) | P1 | Contracts | Version component contracts and verify adapter compatibility |
| [TS-038](backlog/TS-038.md) | P1 | Onboarding | Implement safe fork-and-install onboarding and environment diagnostics |
| [TS-039](backlog/TS-039.md) | P2 | Providers | Implement provider-neutral workflow, storage and model boundaries |
| [TS-040](backlog/TS-040.md) | P1 | Privacy | Implement approved evidence retention, redaction and deletion lifecycle |
| [TS-041](backlog/TS-041.md) | P1 | Recovery | Define disaster recovery targets and verify backup restoration |
| [TS-042](backlog/TS-042.md) | P1 | Security | Threat-model source, agent, plugin and deployment boundaries |
| [TS-043](backlog/TS-043.md) | P1 | Operations | Define service targets, quotas and durable cancellation semantics |
| [TS-044](backlog/TS-044.md) | P2 | Financial | Scope official financial filings and disclosure research |
| [TS-045](backlog/TS-045.md) | P2 | Operational | Scope official product, safety and cyber-event research |
| [TS-046](backlog/TS-046.md) | P2 | Conflicts | Decide and scope contextual business conflict-of-interest research |
| [TS-047](backlog/TS-047.md) | P2 | UI | Specify accessible and localized Streamlit review workflows |
| [TS-048](backlog/TS-048.md) | P2 | Distribution | Decide release packaging and optional Snowflake Native App distribution |
| [TS-049](backlog/TS-049.md) | P2 | Interop | Scope external integrations and portable case evidence exports |
| [TS-050](backlog/TS-050.md) | P1 | Sources | Govern source coverage, licensing changes and connector deprecation |
| [TS-051](backlog/TS-051.md) | P2 | Tenancy | Scope installation and tenant lifecycle administration |

P0 = delivery/safety critical; P1 = core product completion; P2 = later expansion.
Priority is not permission to bypass dependencies or external approvals.

## Suggested GitHub Project

Name: **TrustSignal Delivery**. Use repository Issues as Project items, not only
unassigned draft cards. One named owner per issue; link its PR and dependency issues.

Fields: Status, Priority (P0/P1/P2), Area, Milestone, Baseline, Verification Evidence.
Use GitHub's assignee/linked-PR fields for ownership and implementation.

Statuses: Backlog -> Ready -> In Progress -> In Review -> Done; Blocked is an
explicit alternative. Ready means dependencies are satisfied, scope understood,
required permissions available and acceptance criteria testable. Never mark a
permission-gated source Ready merely because its adapter exists.

Suggested milestones:

1. M0: baseline checkpoint and status reconciliation (TS-001, TS-030).
2. M1: persistent live backend, security and replay (TS-002/003/004/008/025/026).
3. M2: evidence interpretation, evaluation and policy (TS-011/013/014/016/017/018/019/020).
4. M3: authenticated review and governed Cortex (TS-005/021/022/023/024).
5. M4: UI, monitoring and wider sources (TS-007/009/010/012/015/027/028/029/031/032/033).

Operational readiness TS-034 belongs in M1 after its worker/security prerequisites.

Open-source scope/licensing TS-035/036 can be discussed now. Contract, onboarding,
privacy, recovery, security, operations and source stewardship TS-037/038/040/041/042/043/050
support the appropriate backend/pilot release gates. Provider and specialist
expansion, accessibility, distribution, integrations and hosted tenancy
TS-039/044/045/046/047/048/049/051 remain later or decision-gated. These are not
commitments to implement every possible provider or feature in the first release.

Dependencies remain authoritative; milestones are grouping, not execution order.
CI work TS-029 can start earlier after its prerequisites. UI remains deferred.
Published issues use `enhancement`, `priority:P0/P1/P2`, and initial
`status:ready/status:blocked` labels. Areas are recorded in each issue body; dedicated
area labels and the Project/milestones remain optional setup. Templates do not assume
those labels already exist. Link every additional published issue URL in `backlog/index.json`.

## Contributor Workflow

1. Read baseline and the task body; confirm dependencies, external permissions and
   live versus fixture boundaries. Split broad source/provider work into bounded
   child issues before implementation; research rights for each new jurisdiction.
2. Assign yourself in GitHub and move a Ready issue to In Progress. Use a focused
   branch such as `feat/TS-002-durable-worker`.
3. Preserve existing user changes and baseline safety contracts. Implement only the
   issue scope; add focused tests and broader tests for shared changes.
4. Open a PR linking `Closes #<actual-issue-number>` and `TS-xxx`. Include exact test
   commands/results, migrations, live evidence, skipped checks and approval needs.
5. Close only when acceptance criteria are demonstrated and reviewed. Missing cloud
   verification means Blocked/In Review, not Done. Fixtures do not replace live proof.
6. Update affected current-status docs and baseline revision references as appropriate.
   Preserve dated historical reports and immutable evidence/decision versions.

Before publication, the repository is the backlog source. After publication, GitHub
Issues/Project own delivery status and assignments; repository task files retain
scope/acceptance details. Keep changed scope synchronized between both, and update
the manifest's issue URL. `initial_status` is import-time planning, not live status.

No contributor should need chat history to determine scope, prerequisites or completion.

## Tracking Rules

Use GitHub issues as the single source of delivery status. Task files and
`backlog/index.json` own stable scope, acceptance criteria, dependencies and issue
links; do not rewrite `initial_status` or manifest `owner` to mirror daily progress.
Current ownership is the GitHub assignee. A Project is optional, not another backlog.

1. Before starting, read the task and dependencies, assign the issue and record
   `In Progress` in an issue comment (and Project status if a Project exists).
   Remove stale `status:ready`/`status:blocked` labels when they no longer apply.
2. Link the working branch/PR to the actual GitHub issue number, not the TS ID.
   Keep acceptance checkboxes in the issue current; check only criteria supported
   by evidence, not criteria merely implemented without their required verification.
3. At a work-session checkpoint, comment with: implemented changes, exact test
   commands/results, unit/fixture/replay/live boundaries, remaining work and next
   action. Never attach credentials or restricted raw evidence.
4. When blocked, record the specific reason, dependency/approval, responsible owner
   and unblock condition; use `status:blocked`. When unblocked, explain the evidence
   and remove that label. Do not silently close unfinished work.
5. On scope changes, update the task file, manifest and remote issue together.
   Split independently testable additions into linked child issues; reuse existing
   tasks rather than create duplicate implementation ownership.
6. Before marking `Done`, demonstrate every required acceptance criterion, link
   the reviewed implementation commit/PR and verification evidence, and update
   affected current-status docs. Missing required live verification stays open.
   Closure is the authoritative Done state; a merged PR alone is not completion.

Issue checkpoint format:

```text
Status: In Progress | In Review | Blocked
Implemented: <changes and branch/PR>
Verified: <exact commands/results; unit/fixture/replay/live>
Remaining: <unchecked acceptance criteria>
Blocker: <reason, owner and unblock condition, or none>
Next: <one concrete action>
```

This process tracks implementation, not just document creation. No hosted-service
operation or multi-tenant rollout is implied by self-hosted setup tasks.
