# Initialization Resources

The complete backend initialization entrypoint is
`python -m trust_signal.persistence.initialize`. See
[the onboarding guide](../../docs/snowflake-initialization.md). It assembles
all versioned migrations and workflow artifacts into one ordered installation
bundle with separately reviewed activation. `MIGRATION_HISTORY.sql` defines the
checksum ledger used by this flow.

The canonical database/warehouse/schema/table/user setup comes from
`python -m trust_signal.persistence.setup --env-file .env ...`.
It combines reviewed migrations with configured account names and validates that
the public key matches the private key used by the application. It generates SQL
for administrator review; it never executes cloud provisioning.

The former `ACCOUNT_SETUP.sql.template` and hardcoded
`APPLICATION_IDENTITY.sql.template` duplicated that path and have been removed.
Do not use old copies to provision a new account.

The canonical GLEIF SQL is now `../integrations/GLEIF.sql.template`; the old
duplicate external-access reference has been removed. Full initialization
generates target-specific integration SQL from that template; use
`--without-external-access` when the account disallows it. The DEV trial account
rejected external access. Templates must be rendered before execution.
