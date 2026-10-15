# Google Cloud Provider

This root-level directory owns the Google-specific backend integration and
deployment lifecycle. The UI remains in [ui/](../ui/README.md), and reusable backend
components remain in [src/trust_signal/](../src/trust_signal). Provider code and UI
copies do not belong under src/trust_signal.

**Status: architecture only.** The Google runtime,
installation commands and adapters are not implemented. The shared configuration
still rejects non-Snowflake platforms; this directory does not change that guard.

The [Google Cloud profile](../docs/deployment/google-cloud.md) owns service choices,
evidence flow, delivery boundaries and acceptance gates. [TS-039](../docs/backlog/TS-039.md)
owns implementation; create bounded child issues only when work can be accepted
independently without duplicating that backlog.

The [GLEIF, Streamlit and Google Cloud plan](implementation-plan.md) defines the
bounded implementation sequence and acceptance gates for the first connected
identity slice. It complements the owning profile/backlog above.

## First delivery: direct configured Google identity

Use the operator's configured cloud identity and explicitly selected project and
region. No product login, signup, customer OAuth or interactive provider-selection
flow is part of this delivery. Cloud credentials authorize access; a Google email
or principal ID alone is not credentials or a project ID.

Google client libraries can use Application Default Credentials from configured
local credentials or an attached workload identity. CLI credentials and application
credentials are separate configurations. See
[ADC](https://docs.cloud.google.com/docs/authentication/application-default-credentials)
and [gcloud authentication](https://docs.cloud.google.com/docs/authentication/gcloud).
No account identity, project, region or access was inspected in this change.

## Planned ownership

```text
google_cloud/
  README.md       provider status and directory ownership
  implementation-plan.md  GLEIF/UI integration sequence and acceptance gates
  bootstrap/       capability checks, reviewed resource setup, runtime wiring
  application/     provider-backed case commands and read projections for the UI
  adapters/        PostgreSQL, Storage, Workflows, Vertex, retrieval and secrets
  infrastructure/  provider resource definitions
  workflows/       native case execution definitions
  deployment/      build/install/upgrade/recovery entry points and manifests
```

Only planning documents exist at this point. Add executable packages when implemented,
using a distinct import namespace such as trust_signal_google_cloud and its own
provider dependencies. Packaging and job code uploads must keep the shared backend
independently installable.

## Setup and runtime flow

1. Read fixed installation configuration: identity/credential method, project,
   region, resource names and source-access settings.
2. Verify credentials, project access, required APIs/billing/quotas and capabilities.
3. Generate the setup plan; create/reconcile the approved database, evidence
   storage, workload identities, images and native workflow/jobs.
4. Wire the shared identity/specialist/aggregation/validation/review components
   into the provider's executable stage handlers.
5. Verify retained evidence/readback, a bounded live case, restart and replay.
6. Expose the provider application interface to the same ui/app.py.

Setup and runtime are separate: UI rerenders must not repeatedly create resources.
Partial installation needs reconciliation. Resource creation alone does not prove
executable agents or a completed research case.

## Future signup journey

Later, the common UI may let a user sign up, select a provider and grant cloud
access. The selected provider performs its setup and returns installation progress
and readiness. That flow is deferred. Setup in a few minutes is a target to measure,
not a verified installation duration.

Service choices, evidence flows and bounded delivery work remain in the
[Google Cloud profile](../docs/deployment/google-cloud.md). Root provider
ownership and component interfaces are defined in the
[architecture review](../docs/architecture/components.md).
