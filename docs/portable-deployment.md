# Portable Deployment and Account Configuration

## Configuration Contract

Share `.env.example` as the configuration template. Each installation maintains
its own private `.env`, service identity, keys and source credentials. Never share
a populated `.env`, private key, passphrase or source API token. Keep constants
and secrets outside code; rotate credentials without changing domain logic.

The implemented Snowflake path accepts `--env-file .env`. The connection health
check also discovers `.env` in the current directory when no config is specified.
Explicit environment variables override dotenv values. Config loading does not
execute shell commands, expand variables, or mutate process-global environment.
Relative credential paths resolve against the dotenv file's directory.

```bash
.venv/bin/python -m trust_signal.persistence.connection --env-file .env

.venv/bin/python -m trust_signal.ingestion.raw_export \
  --env-file .env \
  --lei INR2EJN1ERAN0W5ZP974 \
  --expected-name "MICROSOFT CORPORATION" \
  --output-dir outputs/live/microsoft
```

The multi-source pipeline loads source API credentials from the same dotenv
configuration and injects them into the registry, rather than changing global
environment. Legacy CLI connections and TOML files remain supported.

## Another Snowflake Account

This is a separate installation, not a data migration or automatic tenant switch:

1. The account owner supplies their account, service user, runtime role, warehouse
   and dedicated application database names in their private `.env`.
2. Generate a separate encrypted RSA key pair for that installation with
   `python -m trust_signal.persistence.keys --env-file .env --public-key-file .secrets/snowflake_key.pub`.
   The command creates private directories/files and refuses to overwrite any
   existing credentials. Retain the public PEM file for provisioning. The setup
   generator verifies that it matches the application's private key.
3. Generate a setup plan locally:

```bash
.venv/bin/python -m trust_signal.persistence.setup \
  --env-file .env \
  --public-key-file .secrets/snowflake_key.pub \
  --output snowflake/build/setup.sql
```

4. An authorized administrator reviews the SQL, target account, costs and current
   objects, then executes it through Snowsight or their administrator connection.
   Never use the runtime service credentials for account administration.
5. Run the connection health check and real-source ingestion against that account.
6. Deploy optional worker/UI/AI components only after confirming their account
   capabilities, required permissions, network access, region and budget.

The generator is **plan-only**: it opens no cloud connection and provisions nothing.
It creates reviewed SQL for the database, initially suspended XSMALL pipeline
warehouse, migrations in version order, service identity and restricted ingestion
grants. It uses the configured database/user/role names; schema names remain the
stable `TRUST_SIGNAL_RAW/CORE/OPS/SERVE` application contract. Account bootstrap is
not executed on startup. [Warehouse settings](https://docs.snowflake.com/en/sql-reference/sql/create-warehouse)

Existing user keys and warehouse settings are not overwritten. Before reusing
existing names, verify that the user belongs to this installation and its
registered public key matches the intended key. `IF NOT EXISTS` does not reconcile
schema drift or upgrade existing objects. DDL can partially commit; review the
failed statement before continuing. Checksummed migration history and automated
upgrade/rollback handling remain future work. Fresh-account SQL execution has not
been live-validated against a second account.

The setup grants only evidence and source-run access. It does **not** configure
multi-user authorization, CORE writing, reviewer permissions, Cortex, external
access, Git integration, Tasks, dbt, SPCS or Streamlit. Separate deployment identities
and grants are required for those components. The Streamlit deployment manifest
already exposes database, application/schema and warehouse settings, but `.env`
is not automatically consumed by Snowflake CLI. A deployment adapter must map
reviewed application settings into its deployment parameters; UI work is deferred.

## Cross-Platform Design

Changing a Snowflake account is configuration. Changing the platform requires
provider implementations, not just different credentials.

| Layer | Portable contract | Provider-specific implementation |
|---|---|---|
| Source connections | Source requests and raw observations | Official API adapters, credential injection |
| Evidence storage | `ObservationStore` and receipts | Snowflake adapter today; another data backend later |
| Run tracking | `SourceRunStore` | Tables/transactions/concurrency for the chosen backend |
| Case identity | `IdentityResearchStore` | Platform persistence adapter |
| Workflow | Case states, specialist results, aggregator, review rules | Worker hosting and durable checkpoint backend |
| AI | Extract/classify/retrieve/query contracts | Cortex today in the plan; alternate model/retrieval services later |
| Scheduling | Refresh job definitions | Snowflake Tasks or another platform's scheduler |
| Deployment | Install/validate/deploy/upgrade lifecycle | Snowflake resources or another cloud's infrastructure |
| UI | Intake, comparison and review experience | Snowflake-hosted UI or independently hosted application |

The domain and source connectors should not know which cloud stores their results.
Provider-specific SQL belongs inside persistence/deployment adapters. Required
capabilities should be validated before launch; unavailable AI or hosting services
must be reported rather than silently replaced.

`TRUST_SIGNAL_PLATFORM=snowflake` is currently the only supported platform.
Other values fail explicitly before connecting. A future Google Cloud backend
would need its own storage, identity, secret, deployment, scheduling and AI adapters.
It cannot deploy Snowflake-native objects or reuse Snowflake credentials there.
No Google Cloud, AWS or Azure adapter has been implemented in this change.

## Bring-Your-Own-Cloud Security

Private dotenv files work for local development and independent deployments.
For a hosted service with customer-owned cloud accounts, use an authenticated
onboarding/control plane, encrypted per-customer secret references, scoped service
identities, tenant-bound connection pools and audit logs. Never place every
customer's credentials in one shared `.env`, accept arbitrary cloud credentials
from a public endpoint, or let an agent choose account/role/tenant context.

Production hosting also requires network restrictions, isolation, credential
rotation, retention policies, source licensing checks, budgets and failure recovery.
This change establishes local configuration and setup planning, not a production
multi-tenant control plane.
