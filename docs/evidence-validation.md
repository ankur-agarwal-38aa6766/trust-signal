# Evidence Validation

The standalone `EvidenceValidator` runs after aggregation in both the local graph
and durable stage runner. Results are included in `CaseResult.validation` and persisted
with stage outputs for retry reuse. Deployment/task definitions remain unchanged.
Prior cached validation stubs are recomputed when the validation stage executes;
current-policy validation outputs remain reusable without refetching sources.

Checks: live-versus-fixture evidence, completed branch lineage, source run/record/version,
observation IDs, SHA-256 format, source URL, timezone-aware retrieval time, future dating,
aggregation membership, confirmed identity, subject labels and unresolved claim conflicts.

Invalid structures are rejected. Structurally consistent findings still require review.
Pending attribution and conflicts are explicitly flagged. No findings become scoring
eligible: RAW persistence is not independently reread here, source statements are not
fact-checked, and legal applicability/finality are not decided by structural validation.

The earlier pipeline/provider checks remain responsible for verified RAW/OPS ingestion.
This stage does not fetch sources, call an LLM, spend Snowflake credits or assign risk scores.
It also does not enforce a new historical-evidence expiration policy.

Next work: independently verifiable evidence/claim review, source-specific adjudication,
configured scoring policies and human review workflows. A claim verifier must be added
before any structural pass can be promoted to scoring eligibility.
