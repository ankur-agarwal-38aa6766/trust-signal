# Human Review Backend

`ReviewService` records explicit human `review`, `request_details`, `reject` and
supervisor-only `reopen` commands. Decisions do not mutate source evidence, assign
scores, assert legal guilt or execute downstream business actions.

Each receipt includes the reviewer, role, rationale, evidence references, immutable
case snapshot hash, version and UTC timestamp. Request-details requires questions;
rejection requires referenced structurally valid evidence plus acknowledgment of
limitations. Pending source identity/claims remain pending even after a human decision.

The replaceable `ReviewStore` boundary currently has a development SQLite adapter:
transactional version checks, idempotency, tenant-scoped keys and append-only API
history. It survives restarts. Conflicting concurrent commands cannot overwrite a
decision. Changed research requires a new case/version rather than overwriting history.
Local database files are restricted to owner access when created. Direct database
administrators can alter SQLite data; this is not a tamper-proof compliance archive.

```python
service = ReviewService(SqliteReviewStore(Path("outputs/review.sqlite")))
digest = service.register(trusted_reviewer_context, persisted_case_result)
receipt = service.decide(trusted_reviewer_context, ReviewCommand(
    request_id="unique-command", case_id=persisted_case_result.case_id,
    snapshot_hash=digest, expected_version=0, action="request_details",
    rationale="Organization identity needs additional supporting documents.",
    questions=["Provide the official registry identifier and supporting record."],
))
```

**Security boundary:** reviewer context and case snapshots must come from a trusted
server authentication/authorization and case-storage path, never editable client
payloads. This component does not implement login, tenant membership verification,
HTTP endpoints, Streamlit viewer authentication or production Snowflake review storage.
The low-level store is an internal trusted interface, not a public endpoint.

UI and deployment remain unchanged. Production Snowflake adapter/RBAC, authenticated
API wiring, notifications, approval/monitoring actions and scoring policy remain future
work. Tests verify durability, authorization gates, tenant isolation, idempotency,
concurrency, immutable snapshots, evidence requirements and supervisor reopen.
