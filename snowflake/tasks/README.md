# Workflow task graph

Generate account-specific task/procedure SQL and an immutable source bundle:

```bash
.venv/bin/python -m trust_signal.orchestration.deployment \
  --output-dir snowflake/build/workflow-v1
```

Apply migrations through V007 before deploying. Generated tasks are suspended;
child activation, one-off execution and scheduled activation are separate files.
Nothing is deployed by the generator.

See [the orchestration guide](../../docs/snowflake-orchestration.md) for account
preflight, runtime requirements, role/EAI setup, deployment order and recovery.
