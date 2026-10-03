# Optional Bootstrap Integrations

The canonical database/warehouse/schema/table/user setup comes from
`python -m trust_signal.persistence.setup --env-file .env ...`.
It combines reviewed migrations with configured account names and validates that
the public key matches the private key used by the application. It generates SQL
for administrator review; it never executes cloud provisioning.

The former `ACCOUNT_SETUP.sql.template` and hardcoded
`APPLICATION_IDENTITY.sql.template` duplicated that path and have been removed.
Do not use old copies to provision a new account.

`EXTERNAL_ACCESS.sql.template` remains an optional future integration example,
not part of the currently validated raw-ingestion setup. It needs account-specific
network permissions and credentials and must not be executed unchanged.
