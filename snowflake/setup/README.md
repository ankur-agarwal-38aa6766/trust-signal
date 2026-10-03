# Complete setup

From the repository root:

```bash
sh snowflake/setup/initialize.sh \
  --database YOUR_TRUST_SIGNAL_DEV \
  --warehouse YOUR_PIPELINE_WH \
  --workflow-role YOUR_WORKFLOW_ROLE \
  --operator-user YOUR_ADMIN_USER \
  --without-external-access
```

This generates, but does not execute, `snowflake/build/installation/` using the
versioned SQL templates and graph definitions in this directory's parent.
Review the SQL and manifest, then explicitly apply it:

```bash
sh snowflake/build/installation/apply.sh YOUR_ADMIN_CONNECTION
```

Generation requires `uv`; applying requires Snowflake CLI and an authorized
administrator connection. All tasks remain suspended. Use a fresh
`--output-dir snowflake/build/<release-name>` for each new release.

Omit `--without-external-access` only if the account permits the approved GLEIF
integration. Optionally include application identity provisioning with
`--ingestion-env-file .env --public-key-file .secrets/snowflake_key.pub`.

See [the full initialization guide](../../docs/snowflake-initialization.md)
for prerequisites, credentials, re-runs and activation. Do not place credentials
or account-specific generated SQL in the versioned source directories.
