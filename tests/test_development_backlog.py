import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backlog_tasks_are_actionable_and_dependencies_are_acyclic():
    manifest = json.loads((ROOT / "docs/backlog/index.json").read_text())
    tasks = manifest["tasks"]
    by_id = {task["id"]: task for task in tasks}
    assert len(by_id) == len(tasks)
    assert len(tasks) >= 32
    visiting, visited = set(), set()

    def visit(identifier):
        assert identifier not in visiting, "Backlog dependency cycle"
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in by_id[identifier]["dependencies"]:
            assert dependency in by_id
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for task in tasks:
        assert task["priority"] in {"P0", "P1", "P2"}
        assert task["acceptance_criteria"] and task["test_requirements"]
        body = (ROOT / task["issue_file"]).read_text()
        assert f"# {task['id']}: {task['title']}" in body
        assert all(criterion in body for criterion in task["acceptance_criteria"])
        assert task["test_requirements"] in body
        assert all((ROOT / path).exists() for path in task["paths"])
        visit(task["id"])


def test_handoff_index_links_every_task():
    manifest = json.loads((ROOT / "docs/backlog/index.json").read_text())
    guide = (ROOT / "docs/backlog/README.md").read_text()
    assert all(f"{task['id']}.md" in guide for task in manifest["tasks"])
    assert (ROOT / ".github/ISSUE_TEMPLATE/development-task.yml").is_file()
    assert (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").is_file()


def test_published_issue_mapping_is_complete_and_matches_task_files():
    manifest = json.loads((ROOT / "docs/backlog/index.json").read_text())
    publication = manifest["github_publication"]
    assert publication["source_branch"] == "master"
    assert publication["issue_count"] == len(manifest["tasks"])
    urls = set()
    for task in manifest["tasks"]:
        url = task["github_issue_url"]
        assert url == f"https://github.com/{publication['repository']}/issues/{task['github_issue_number']}"
        assert url not in urls
        urls.add(url)
        assert url in (ROOT / task["issue_file"]).read_text()


def test_open_source_direction_and_future_decisions_have_delivery_owners():
    manifest = json.loads((ROOT / "docs/backlog/index.json").read_text())
    by_id = {task["id"]: task for task in manifest["tasks"]}
    scope = (ROOT / "docs/product/scope.md").read_text()
    assert "The hackathon scope is closed" in scope
    assert "## Decisions Still To Discuss" in scope
    assert "## Retained scope and ownership" in scope
    for identifier in set(re.findall(r"TS-\d{3}", scope)):
        assert identifier in by_id, f"Untracked scope reference: {identifier}"
    grouped_ids = [
        identifier
        for group in manifest["delivery_groups"]
        for identifier in group["task_ids"]
    ]
    assert len(grouped_ids) == len(set(grouped_ids))
    assert set(grouped_ids) == by_id.keys()
    for identifier, task in by_id.items():
        if int(identifier.split("-")[1]) >= 35:
            assert task["context"]
            assert "product/scope.md" in (ROOT / task["issue_file"]).read_text()
    assert "docs/product/scope.md" in (ROOT / "README.md").read_text()
    assert "product/scope.md" in (ROOT / "docs/README.md").read_text()
    assert "product/scope.md" in (ROOT / "docs/backlog/README.md").read_text()


def test_provider_portable_scope_has_traceable_owners_and_no_trial_task():
    manifest = json.loads((ROOT / "docs/backlog/index.json").read_text())
    by_id = {task["id"]: task for task in manifest["tasks"]}
    coverage = manifest["scope_coverage"]
    themes = {topic["thought"] for topic in coverage["topics"]}
    assert len(themes) == len(coverage["topics"])
    assert {
        "provider_neutral_dag_python_sql_runtime",
        "streamlit_trigger_monitor_reconnect_and_results",
        "fork_install_credentials_permissions_and_upgrades",
        "restore_and_provider_migration",
        "shared_refresh_vs_per_case_research",
        "optional_models_retrieval_and_agent_tools",
    } <= themes
    for topic in coverage["topics"]:
        assert topic["task_ids"]
        assert set(topic["task_ids"]) <= by_id.keys()
    assert "TS-052" not in by_id
    assert not (ROOT / "docs/backlog/TS-052.md").exists()
    assert "TS-052" not in json.dumps(manifest)
    assert manifest["direction"]["scope_updated_date"] == "2026-10-14"
    assert len(manifest["direction"]["excluded_scope"]) == 3
    assert "provider-managed" in by_id["TS-002"]["title"]
    assert "provider-neutral" in by_id["TS-039"]["title"]


def test_canonical_documentation_map_exists_and_old_duplicates_are_removed():
    manifest = json.loads((ROOT / "docs/backlog/index.json").read_text())
    assert all((ROOT / path).is_file() for path in manifest["documentation"].values())
    assert not any(
        (ROOT / path).exists()
        for path in (
            "docs/complete-implementation-plan.md",
            "docs/implementation-roadmap.md",
            "docs/future-scope.md",
            "docs/project-context.md",
            "docs/system-design.md",
            "docs/product-design.md",
            "docs/development-backlog.md",
        )
    )
