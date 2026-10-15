# Research aggregation

`src/trust_signal/aggregation/` is the standalone component that combines findings
from specialist branches. The case graph calls it after its parallel completion
barrier and exposes the result as `CaseResult.aggregation`. The existing
`comparison_board` is retained for current consumers.

```text
Verified source ingestion -> Identity resolution -> Specialist branches
                                                      |
                                                      v
                                               EvidenceAggregator
                                                      |
                                                      v
                              Claim groups + comparison board + timeline + coverage
                                                      |
                                                      v
                                             Assessment and human review
```

## Responsibility and contracts

`AggregationService.aggregate(branches, identity=None)` accepts portable domain
objects and returns an `AggregationResult`. It does not fetch sources, connect to
Snowflake, call a language model, validate allegations, or calculate risk scores.
Implement the same protocol to replace it, and inject the replacement through
`run_case(..., aggregator=...)` or `build_case_graph(..., aggregator=...)`.

The result contains:

- Claim groups with original finding IDs, source IDs and observation references.
- Duplicate sets and the count of evidence entries after exact-content clustering.
- Comparison items classifying agreement, potential conflicts or collection members.
- A timeline using explicit event timestamps.
- Branch statuses, checked sources, limitations and failures.

Original findings remain in `CaseResult.branches`; no source assertion is overwritten
or selected as the truth. Aggregation has no storage side effects. Durable case
and aggregation persistence remains a worker/repository integration step.

## Structured findings

Existing free-text findings continue to work. New optional `Finding` fields make
precise comparisons possible:

| Field | Meaning |
|---|---|
| `subject_id` | Explicit subject identifier. Currently use the selected identity candidate ID; it is not an inferred canonical global entity ID. |
| `claim_key` | Stable predicate, such as `registration.status` or `board.director`. |
| `claim_value` | Source-adapter-normalized value, compared exactly. |
| `claim_cardinality` | `single`, `multiple`, or `unknown` (default). |
| `event_id` | Optional shared event identifier supplied upstream. |
| `event_at` | Explicit event occurrence time. |
| `effective_at` | Time at which an assertion takes effect. |

For example, two `registration.status` claims with cardinality `single`, the same
subject/event/time scope, and values `active` and `dissolved` yield
`potential_conflict`. A reviewer must examine the records; the aggregator does not
declare either value false. Two `board.director` claims with cardinality `multiple`
and different person IDs yield `combined_members`, not a contradiction.

## Rules and limits

Groups separate subject, claim type/key, event identifier, event time, effective
time, evidence mode and cardinality. Known different periods and events stay
separate. Unknown times remain unknown. Fixtures cannot corroborate live evidence.

Without a subject ID, normalized-name grouping is provisional. It cannot establish
identity or merge legal entities. `identity_confirmed` requires an explicit subject
ID matching the selected eligible identity candidate. It does not verify every
claim or make findings eligible for scoring.

Repeated finding IDs with identical contents are treated as replay. The same ID
with different contents raises an error. Valid matching SHA-256 response hashes
and the same structured claim value (or exact free text) and procedural status
identify repeated evidence. All finding IDs and observation references are retained.
Missing/invalid hashes prevent content deduplication. Distinct evidence counts
therefore include unclustered findings when content identity is unknown.

Matching normalized values produce `consistent_claims`. Differing values produce
`potential_conflict` only for explicitly single-valued predicates. Free text is
grouped for inspection without natural-language contradiction inference. Separate
source IDs do not prove independent corroboration. Syndicated articles with
different response bodies require a later content/event clustering component.

The timeline uses `event_at`, never retrieval time as a substitute. Timezone-aware
event/effective timestamps are required. Coverage describes the supplied branches;
it does not imply that every relevant source worldwide was searched.

## Standalone usage

```python
from trust_signal.aggregation import EvidenceAggregator

result = EvidenceAggregator().aggregate(branch_results, identity_resolution)
print(result.model_dump_json(indent=2))
```

For the existing workflow, aggregation runs automatically:

```python
case = run_case(request, branches=research_branches)
groups = case.aggregation.groups if case.aggregation else []
```

An identity failure can end the live workflow before aggregation runs, leaving
`case.aggregation` as `None`. This component currently consolidates findings;
source-specific news extraction, event recognition and ownership/director discovery
still belong to the corresponding specialist components.
