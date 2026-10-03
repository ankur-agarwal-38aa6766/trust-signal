"""Load versioned installation resources from the checked-out Snowflake directory."""

from pathlib import Path


def resource_root(resources: Path | None = None) -> Path:
    root = resources if resources is not None else Path(__file__).resolve().parents[3] / "snowflake"
    if not root.is_dir():
        raise FileNotFoundError(
            "Snowflake resources are required; run setup from a repository checkout."
        )
    return root.resolve()


def read_resource(relative: str, resources: Path | None = None) -> str:
    root = resource_root(resources)
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Resource paths must stay inside the Snowflake directory.")
    return path.read_text(encoding="utf-8")


def render_sql(relative: str, *, resources: Path | None = None, **values) -> str:
    return read_resource(relative, resources).format_map(values)
