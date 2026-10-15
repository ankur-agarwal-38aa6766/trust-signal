# Research specialists

Four deterministic specialists implement bounded research over confirmed identity.
They accept replaceable providers, return typed findings/coverage, and are explicitly
enabled in the local live CLI. Snowflake's native handlers do not inject them.
[Status](../status.md) owns readiness; [connectors](../sources/connectors.md) owns
source operations, access gates and retention implementation.

## Shared flow and contracts

Confirmed persisted identity -> explicit source requests -> RAW byte/hash readback
and OPS terminal-run verification -> validated provider dataset -> specialist
findings and limitations -> aggregation -> structural validation -> unscored review.

`resolution/confirmed.py` enforces the shared specialist identity gate.
`PipelineResearchProvider` supplies ownership/legal/news datasets;
`PipelineSanctionsProvider` supplies screening datasets. A cached implementation
must preserve the same source, receipt, hash and run-lineage guarantees. Constructing
an in-memory contract is not proof of verified storage. Normalized cache/replay
providers are still pending.

Providers withhold malformed, stale, unverified or failed datasets. Retrieval older
than 24 hours or over five minutes in the future is withheld; this is retrieval
freshness, not verification of publication freshness or current legal state.
Failed/blocked/partial/empty requests cannot imply clean risk. Valid other-source
results remain visible with gaps.

The shared pipeline serializes complete source runs on one session; local specialist
branches may execute in parallel without overlapping those ingestion operations.
Separate pipeline instances sharing that session do not share this protection.

## Sanctions

Implementation: [specialist](../../src/trust_signal/agents/sanctions.py),
[matcher](../../src/trust_signal/screening/sanctions.py),
[contracts](../../src/trust_signal/domain/sanctions.py).

Default lists are UN entity entries, OFAC SDN, UK FCDO and EU financial sanctions.
Australia is separately selectable. These scopes do not cover every designation,
non-SDN list or ownership/control rule; see the connector guide.

- Exact names/aliases or fuzzy similarity of at least 0.8 discover candidates.
  Similarity is a heuristic, not a calibrated probability.
- Confirmation needs exact name/alias and exact LEI, or exact registration ID under
  the same issuing authority/jurisdiction. Comparable identifier conflicts exclude
  candidates; identifier-only name conflicts require review.
- Source adapters do not currently populate authoritative identifier fields for
  this matching policy, so their name matches normally remain pending.
- Direct organization matching excludes individuals/vessels/aircraft. Unknown
  subject types stay reviewable. Country/address text does not establish registry scope.
- Potential findings have no confirmed subject ID. Identity matching alone never
  establishes legal applicability, a conviction, scoring eligibility or rejection.
- Keep exclusions and source designation strings in the audit; do not invent dates.

Remaining capabilities are owned by TS-011/012/019: authoritative identifiers with
locators, related-party screening, approved ownership/control rules, multilingual
evaluation and calibrated benchmarks.

## Ownership and leadership

Implementation: [specialist](../../src/trust_signal/agents/ownership.py) and
[contracts](../../src/trust_signal/domain/ownership.py).

GLEIF accounting-consolidating parents/children are directional relationships,
not beneficial ownership or inferred share percentages. Preserve relationship type,
status, periods, corroboration and reporting exceptions. Exceptions do not mean
there is no parent or indicate fraud. Malformed direction/type fails the dataset.

Norway lookup precedes role retrieval. An exact scoped identifier, authority,
jurisdiction and name/alias can confirm linkage. A supplied nine-digit organization
number plus matching name is a hint and leaves attribution pending. Lookup and
role observations both remain referenced; jurisdiction conflicts block linkage.

Preserve person/organization holders, role/group codes, board flags and deregistration
state. Snapshot-index role IDs are not stable person identifiers. Raw role payloads
may contain personal data even when normalized fields omit it. Role holders/related
parties are not independently resolved or screened today. Missing scope is explicit
not-applicable coverage, not universal absence of directors or owners.

TS-006/013 own cross-registry mapping and independent party resolution. Recursive
traversal, authorized beneficial ownership and wider leadership need bounded follow-up.

## Legal and adverse events

Implementation: [specialist](../../src/trust_signal/agents/legal.py) and
[contracts](../../src/trust_signal/domain/legal.py).

Defaults: World Bank debarment, FCA announcements and corporate Gazette search.
Find Case Law metadata is opt-in and remains permission-gated by the existing source
configuration. Do not enable its approval flag to bypass project permission.

- Source subjects and identifiers drive attribution; name-only hits stay potential.
  Headlines cannot establish whether the party is a defendant, claimant, namesake
  or merely mentioned; `event_party_role_unknown` remains visible.
- Bounded complete-name/long-alias title mentions are discovery. No fuzzy title
  attribution, inferred translation or legal conclusion is implemented.
- Allegation, proceeding, decision, final decision, judgment publication, debarment
  and unknown state differ. Preserve dismissal, eligibility/expiry and finality.
  A filing/publication is not a verdict or exhausted appeal.
- Publication is not event time. Empty World Bank snapshots fail closed; empty
  verified searches remain request-specific absence. Searches over the supported
  200-character limit are blocked rather than silently truncated.
- UK-source queries are not skipped merely because a party is incorporated elsewhere,
  and an empty UK query does not establish absence of proceedings globally.

TS-014/018/032/033 own permitted primary-document retrieval, party roles, procedural
adjudication, court permission and wider source coverage.

## News

Implementation: [specialist](../../src/trust_signal/agents/news.py) and
[contracts](../../src/trust_signal/domain/news.py).

GDELT provides bounded last-24-hour metadata discovery, at most 50 results per
request; FCA supplements official announcements. No article bodies are fetched or
licensed by this code. GDELT publisher trust remains `not_assessed`.

Full-name/long-alias title mentions show relevance, not resolved event identity;
findings stay identity-pending without confirmed subject IDs. No sentiment, fraud
inference, short-alias translation or guessed event date is used. Provider-seen time
is not publication time. Exact URL repeats within a source are suppressed; normalized
title groups are duplicate hints, not proven syndication or independent corroboration.
Invalid URLs/schema, duplicate IDs or missing lineage withhold the dataset.
Unsupported provider query syntax is blocked rather than rewritten.

TS-007/015/016/050 own alias planning, multilingual relevance, licensed content,
publisher policy, publication dates, wider official feeds and syndication analysis.

## CLI usage

Enable flags require `--source-mode gleif_live`; selection flags require their enable
flag and reject duplicates. Without an LEI, discovery requests confirmation and no
specialist fan-out. Without enable flags, the default live CLI runs identity only.

| Enable | Selection |
| --- | --- |
| `--sanctions` | Repeat `--sanctions-source` |
| `--ownership` | Optional `--norway-organization-number` hint |
| `--legal` | Repeat `--legal-source` |
| `--news` | Repeat `--news-source` |

```bash
uv run --locked --extra snowflake trust-signal --help

uv run --locked --extra snowflake trust-signal "Microsoft Corporation" \
  --lei INR2EJN1ERAN0W5ZP974 --source-mode gleif_live --env-file .env \
  --sanctions --sanctions-source un_security_council_consolidated_list
```

The second command performs source requests and warehouse writes using approved
configuration/access/budget. It is not an offline check or infrastructure deployment.
Add other enable flags to run more branches; global snapshots can be large.

## Component injection

```python
from trust_signal.agents.legal import LegalSpecialist
from trust_signal.research.provider import PipelineResearchProvider
from trust_signal.orchestration.case_graph import run_case
from trust_signal.orchestration.stages import StageRunner
from trust_signal.domain.workflow import WorkflowStage

specialist = LegalSpecialist(PipelineResearchProvider(pipeline))
result = run_case(request, ingestion_pipeline=pipeline,
                  specialists={"legal": specialist})
runner = StageRunner(workflow_store, identity_handler,
                     {WorkflowStage.LEGAL: specialist})
```

Other specialists use the same two-argument callable boundary. Injection does not
deploy a cloud handler or authorize network access. Fixture/provenance/failure,
identity, CLI and stage-retry tests are offline evidence; complete persisted live
multi-specialist cases remain TS-002/026 integration work.
