# Shared TrustSignal UI

All user-interface source and configuration live in this top-level directory.
Providers own backend connection/runtime code, not copies of the UI.
Their implementations live in root-level snowflake/ and google_cloud/. The shared
src/trust_signal components remain cloud-independent. The first Google integration
is intended to use fixed identity/project configuration directly; product login/signup
and dynamic provider selection are deferred. Google runtime integration is still
planned, not enabled by this UI's existence.

| File | Purpose |
| --- | --- |
| [app.py](app.py) | The selected final Streamlit UI: reviewer dossier, intake, queue, source and operations screens |
| [streamlit/config.toml](streamlit/config.toml) | Shared theme and Streamlit settings, moved from `.streamlit/config.toml` |
| [run.py](run.py) | Local launcher that explicitly applies the relocated settings |

From the repository root, with locked dependencies installed:

```bash
uv run --locked python ui/run.py
```

Override a setting through an additional Streamlit CLI flag:

```bash
uv run --locked python ui/run.py --server.port=8502
```

The underlying direct command is `uv run --locked streamlit run ui/app.py`, but
that command does not apply `ui/streamlit/config.toml`. The launcher uses the public
Streamlit CLI to pass the relocated defaults; it does not create another `.streamlit`
directory. Keep the working directory at the repository root for current relative
backend configuration such as `.env`.

The old Snowflake UI and its deployment manifest have been removed at the maintainer's
request. `app.py` is the single selected UI. Its intake currently runs the local
graph; some dossier/queue/telemetry content is illustrative. Selecting this UI does
not complete provider-independent durable backend wiring or production review.
Future hosting must deploy this same UI with the selected provider backend.

Private UI secrets, if used, belong in ignored `ui/streamlit/secrets.toml` and require
explicit runtime configuration; the current launcher loads only `config.toml` and
does not imply that secrets are automatically discovered at this custom location.
