"""Build reviewable Snowflake workflow artifacts without connecting to an account."""

import argparse
import hashlib
import io
import json
import re
from functools import partial
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from trust_signal.domain.workflow import SPECIALIST_STAGES
from trust_signal.persistence.sql_resources import read_resource
from trust_signal.persistence.sql_resources import render_sql as render_template


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
        raise ValueError("Use uppercase unquoted Snowflake identifiers.")
    return value


def source_bundle(source: Path) -> bytes:
    files = sorted((source / "trust_signal").rglob("*.py"))
    if not files or not (source / "trust_signal" / "__init__.py").is_file():
        raise ValueError("Source root must contain the trust_signal package.")
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            if "__pycache__" in path.parts or path.is_symlink():
                continue
            item = ZipInfo(path.relative_to(source).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = ZIP_DEFLATED
            archive.writestr(item, path.read_bytes())
    return buffer.getvalue()


def render(
    database: str,
    warehouse: str,
    role: str,
    eai: str,
    bundle_name: str,
    pydantic_version: str = "2.11.7",
    external_access: bool = True,
    resources: Path | None = None,
) -> dict[str, str]:
    render_sql = partial(render_template, resources=resources)
    for value in (database, warehouse, role, eai):
        identifier(value)
    if not re.fullmatch(r"trust_signal_[0-9a-f]{16}\.zip", bundle_name):
        raise ValueError("Invalid code bundle filename.")
    if not re.fullmatch(r"2\.(?:1[0-9]|[2-9][0-9])\.[0-9]+", pydantic_version):
        raise ValueError("A pinned Pydantic 2.10+ release is required.")
    ops = f"{database}.TRUST_SIGNAL_OPS"
    raw = f"{database}.TRUST_SIGNAL_RAW"
    core = f"{database}.TRUST_SIGNAL_CORE"
    prefix = render_sql("bootstrap/WORKFLOW_CONTEXT.sql.template", role=role, database=database)
    grants = render_sql(
        "security/WORKFLOW_GRANTS.sql.template",
        role=role,
        database=database,
        warehouse=warehouse,
        ops=ops,
        raw=raw,
        core=core,
    )
    if external_access:
        grants += render_sql("security/EXTERNAL_ACCESS_GRANT.sql.template", eai=eai, role=role)
    packages = (
        "'snowflake-snowpark-python', " + f"'pydantic=={pydantic_version}', "
        "'httpx', 'python-dotenv', 'openpyxl', 'beautifulsoup4'"
    )

    def procedure(name, arguments, handler, parameter_names, network=False):
        network_clause = (
            render_sql("procedures/EXTERNAL_ACCESS.sql.template", eai=eai) if network else ""
        )
        return render_sql(
            "procedures/WORKFLOW_PROCEDURE.sql.template",
            ops=ops,
            name=name,
            arguments=arguments,
            packages=packages,
            bundle_name=bundle_name,
            network_clause=network_clause,
            parameter_names=parameter_names,
            handler=handler,
        )

    procedures = prefix + render_sql("tasks/SUSPEND_ROOT.sql.template", ops=ops)
    definitions = json.loads(read_resource("procedures/WORKFLOW.json", resources))
    for definition in definitions:
        network = definition.get("network", False)
        handler = definition["handler"]
        if network and not external_access:
            handler = definition["restricted_handler"]
        procedures += procedure(
            definition["name"],
            definition["arguments"],
            handler,
            definition["parameters"],
            network and external_access,
        )
    tasks = prefix + render_sql("tasks/ROOT.sql.template", ops=ops, warehouse=warehouse)

    def child(name, parents, predecessor, call):
        return render_sql(
            "tasks/CHILD.sql.template",
            ops=ops,
            name=name,
            warehouse=warehouse,
            parents=", ".join(ops + "." + p for p in parents),
            predecessor=predecessor,
            call=call,
        )

    graph = json.loads(read_resource("tasks/WORKFLOW_GRAPH.json", resources))
    if graph["root"] != "TS_CLAIM" or graph["finalizer"] != "TS_FINALIZE":
        raise ValueError("Graph root/finalizer must match the SQL templates.")
    seen = {graph["root"]}
    for node in graph["children"]:
        if node["name"] in seen or not node["parents"] or not set(node["parents"]) <= seen:
            raise ValueError("Graph children must be unique and follow their parents.")
        if node["predecessor"] not in node["parents"]:
            raise ValueError("Task return-value predecessor must be a direct parent.")
        seen.add(node["name"])
    specialist_names = {"TS_" + stage.value.upper() for stage in SPECIALIST_STAGES}
    if not specialist_names <= {node["name"] for node in graph["children"]}:
        raise ValueError("Workflow graph must include every specialist stage.")
    for node in graph["children"]:
        stage = node.get("stage")
        if stage is not None and not re.fullmatch(r"[a-z_]+", stage):
            raise ValueError("Invalid stage name in workflow graph.")
        for name in (node["name"], node["predecessor"], node["procedure"], *node["parents"]):
            identifier(name)
        arguments = ":run_id" + (f", '{stage}'" if stage else "")
        tasks += child(
            node["name"],
            node["parents"],
            node["predecessor"],
            f"{ops}.{node['procedure']}({arguments})",
        )
    tasks += render_sql("tasks/FINALIZER.sql.template", ops=ops, warehouse=warehouse)
    names = [node["name"] for node in graph["children"]] + ["TS_FINALIZE"]
    enable = (
        prefix
        + "\n".join(
            render_sql("tasks/RESUME_CHILD.sql.template", ops=ops, name=name) for name in names
        )
        + "\n"
    )
    preflight = render_sql(
        "verification/PREFLIGHT.sql.template",
        database=database,
        warehouse=warehouse,
        eai=eai,
        role=role,
    )
    return {
        "grants.sql": grants,
        "preflight.sql": preflight,
        "procedures.sql": procedures,
        "tasks.sql": tasks,
        "enable_children.sql": enable,
        "start_schedule.sql": prefix + render_sql("tasks/START_SCHEDULE.sql.template", ops=ops),
        "stop_schedule.sql": prefix + render_sql("tasks/STOP_SCHEDULE.sql.template", ops=ops),
        "execute_once.sql": prefix + render_sql("tasks/EXECUTE_ONCE.sql.template", ops=ops),
    }


def build(
    source: Path,
    output: Path,
    database: str,
    warehouse: str,
    role: str,
    eai: str,
    pydantic_version: str = "2.11.7",
    external_access: bool = True,
    resources: Path | None = None,
) -> dict:
    bundle = source_bundle(source)
    digest = hashlib.sha256(bundle).hexdigest()
    name = f"trust_signal_{digest[:16]}.zip"
    artifacts = render(
        database, warehouse, role, eai, name, pydantic_version, external_access, resources
    )
    path = (output / name).resolve().as_uri().replace("'", "''")
    artifacts["upload.sql"] = render_template(
        "bootstrap/UPLOAD_CODE.sql.template",
        resources=resources,
        role=role,
        path=path,
        database=database,
    )
    manifest = {
        "status": "plan_only",
        "database": database,
        "warehouse": warehouse,
        "role": role,
        "code_bundle": name,
        "sha256": digest,
        "pydantic_version": pydantic_version,
        "deployed": False,
        "external_access": external_access,
        "tasks_enabled": False,
    }
    artifacts["manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    files = {key: value.encode() for key, value in artifacts.items()}
    files[name] = bundle
    for filename, data in files.items():
        target = output / filename
        if target.exists() and target.read_bytes() != data:
            raise FileExistsError("Use a fresh release directory; existing artifacts differ.")
    output.mkdir(parents=True, exist_ok=True)
    for filename, data in files.items():
        (output / filename).write_bytes(data)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path("src"))
    parser.add_argument("--output-dir", type=Path, default=Path("snowflake/build/workflow"))
    parser.add_argument("--snowflake-dir", type=Path, default=Path("snowflake"))
    parser.add_argument("--database", default="TRUST_SIGNAL_DEV")
    parser.add_argument("--warehouse", default="TRUST_SIGNAL_PIPELINE_WH")
    parser.add_argument("--role", default="TRUST_SIGNAL_ORCHESTRATOR")
    parser.add_argument("--gleif-eai", default="TRUST_SIGNAL_GLEIF_EAI")
    parser.add_argument("--pydantic-version", default="2.11.7")
    parser.add_argument(
        "--without-external-access",
        action="store_true",
        help="Deploy fail-closed identity handling; never performs live research.",
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                build(
                    args.source_dir,
                    args.output_dir,
                    args.database,
                    args.warehouse,
                    args.role,
                    args.gleif_eai,
                    args.pydantic_version,
                    not args.without_external_access,
                    args.snowflake_dir,
                ),
                indent=2,
            )
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Workflow artifact generation failed: {type(exc).__name__}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
