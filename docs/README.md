# Documentation

This is the entrypoint for the complete application. Each subject has one owning
document; update that document instead of adding another plan or status report.

## Start here

| Need | Authoritative document |
| --- | --- |
| Product scope, constraints and unresolved decisions | [Scope](product/scope.md) |
| Implemented behavior and remaining integration gaps | [Status](status.md) |
| Application flow, data and responsibilities | [Architecture](architecture/overview.md) |
| Dependency boundaries and provider ownership | [Component layout](architecture/components.md) |
| Remaining work, dependencies and issue mapping | [Backlog](backlog/README.md) |
| Accepted checkpoint and dated evidence | [Verification history](verification/history.md) |

## Components and sources

| Subject | Guide |
| --- | --- |
| Identity, candidates and attribution | [Identity](components/identity.md) |
| Fetch, retain, verify and release | [Ingestion](components/ingestion.md) |
| Sanctions, ownership, legal and news | [Research](components/research.md) |
| Comparison, duplicates, conflicts and timeline | [Aggregation](components/aggregation.md) |
| Structural evidence checks | [Validation](components/validation.md) |
| Human commands and development storage | [Review](components/review.md) |
| Implemented source operations and access gates | [Connectors](sources/connectors.md) |
| Candidate authorities and jurisdiction coverage | [Catalog](sources/catalog.md) |
| Screens, field mappings and interaction acceptance | [Streamlit experience](design/streamlit.md) |

## Deployment and operations

| Subject | Guide |
| --- | --- |
| Installation configuration and profile boundaries | [Portable deployment](deployment/portable.md) |
| Existing Snowflake implementation and setup paths | [Snowflake profile](deployment/snowflake.md) |
| Proposed Google services and execution flow | [Google profile](deployment/google-cloud.md) |
| First GLEIF/UI delivery on Google | [Google implementation plan](../google_cloud/implementation-plan.md) |
| Release and operational gates | [Readiness](deployment/readiness.md) |
| Snowflake plan, migrations and apply lifecycle | [Initialization](operations/snowflake-initialization.md) |
| Stage execution, deployment and recovery | [Workflow operations](operations/snowflake-workflows.md) |
| Key-pair sessions, live commands and rotation | [Application connection](operations/application-connection.md) |
| Budget configuration and spend limits | [Cost controls](operations/cost-controls.md) |
| Effective service access and hardening | [Ingestion security](operations/ingestion-security.md) |

The root [README](../README.md) owns the local quickstart. Directory READMEs under
[ui](../ui/README.md), [snowflake](../snowflake/README.md) and
[google_cloud](../google_cloud/README.md) own their entrypoints and link to these guides.

## Documentation rules

Code and tests establish implemented behavior. Scope owns direction and open
decisions; the manifest owns task definitions and GitHub owns live assignments and
delivery status. Design documents describe targets. Verification history records
dated observations with limitations; it is not a deployment instruction.

Use one topic owner and link to it. Keep commands in the guide owning the operation.
Update status when behavior changes; append dated evidence to the existing history.
Keep task IDs stable and scope synchronized with the manifest. Group work in the
backlog instead of maintaining another roadmap. Superseded plans are removed;
committed versions remain in Git.

Run documentation-link and backlog checks after moves. Do not maintain copied
specifications, old-path redirects, parallel design prompts or trial plans as active
requirements.
