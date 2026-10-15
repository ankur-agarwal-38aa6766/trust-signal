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
| [views.py](views.py) | Native Streamlit screen layouts, application-service calls and widget callbacks |
| [components.py](components.py) | Shared visual helpers for headings, badges, cards and navigation |
| [design_data.py](design_data.py) | Explicit illustrative data from the supplied design, separate from research results |
| [diagrams.py](diagrams.py) | Task graph rendered through Streamlit's native Graphviz chart |
| [styles.css](styles.css) | Precision Blue typography, surface tokens, spacing and responsive widget styling |
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
request. `app.py` is the single selected UI. Every page, input, candidate-selection
button, filter, download and action uses native Streamlit widgets. No HTML-page
iframe or custom JavaScript component is used. Static HTML fragments only style
presentational elements such as headings and badges.

The screen layouts follow the supplied Stitch/Figma HTML export. The five screen
PNG files in that export contain failed-fetch placeholders, so those HTML files
are the visual reference. Review opens on the illustrative ABC Trading dossier;
the header identifies sample data. Sample scores and telemetry never populate a
newly submitted research result. Queue and source filters work locally, schema
panels expand, and CSV/JSON downloads contain their displayed sample or case data.

Intake uses the existing `TrustSignalApplication` boundary. Name changes request
candidates; explicit selection fills name, LEI and jurisdiction. Submission and
result retrieval use the injected application instance. Backend construction and
cloud provisioning do not occur as a side effect of page navigation. The current
local application is synchronous and session-scoped; managed durable execution,
authenticated review and live operational controls remain integration work.
Future hosting must deploy this same UI with the selected provider backend.

Private UI secrets, if used, belong in ignored `ui/streamlit/secrets.toml` and require
explicit runtime configuration; the current launcher loads only `config.toml` and
does not imply that secrets are automatically discovered at this custom location.
