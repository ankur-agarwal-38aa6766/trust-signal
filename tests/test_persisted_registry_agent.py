from unittest.mock import Mock

from test_ingestion_pipeline import setup_pipeline

from trust_signal.agents.registry import gleif_registry_branch
from trust_signal.models import BranchStatus, CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case


def request_for_batch(batch):
    raw = batch.observations[0].raw_payload["data"]["attributes"]
    batch.records = [{"source_id": "gleif_lei_api", "source_record_id": raw["lei"],
                      "lei": raw["lei"], "legal_name": raw["entity"]["legalName"]["name"]}]
    return CaseRequest(source_mode=SourceMode.GLEIF_LIVE,
                       party={"legal_name": batch.records[0]["legal_name"], "lei": raw["lei"]})


def test_agent_finding_has_verified_snowflake_lineage():
    pipeline, _, store, runs, batch = setup_pipeline()
    request = request_for_batch(batch)
    branch = gleif_registry_branch(request, pipeline)
    store.store_observation.assert_called_once()
    runs.finish.assert_called_once()
    assert branch.status == BranchStatus.COMPLETED
    assert branch.findings[0].observation_ids == ["obs_1"]
    assert branch.findings[0].source_run_id.startswith("run_")
    assert branch.findings[0].verification_status == "source_record_persisted_and_verified"
    assert branch.identity_resolution.status == "resolved"
    assert branch.identity_resolution.matches[0].candidate.observation_ids == ["obs_1"]


def test_storage_failure_never_produces_identity_or_findings():
    pipeline, _, store, _, batch = setup_pipeline()
    request = request_for_batch(batch)
    store.store_observation.side_effect = RuntimeError("private auth data")
    branch = gleif_registry_branch(request, pipeline)
    assert branch.status == BranchStatus.FAILED
    assert branch.findings == [] and branch.identity_resolution is None
    assert "private auth data" not in branch.model_dump_json()


def test_case_graph_uses_injected_ingestion_boundary():
    pipeline, _, _, _, batch = setup_pipeline()
    result = run_case(request_for_batch(batch), ingestion_pipeline=pipeline)
    assert result.identity_status == "resolved_by_exact_lei_and_name"
    assert result.branches[0].findings[0].observation_ids == ["obs_1"]


def test_missing_local_config_never_fetches(monkeypatch):
    monkeypatch.setattr("trust_signal.agents.registry.Path.is_file", Mock(return_value=False))
    result = run_case(CaseRequest(source_mode=SourceMode.GLEIF_LIVE,
                                 party={"legal_name": "Example", "lei": "0" * 20}))
    assert result.branches[0].status == BranchStatus.FAILED
    assert not result.branches[0].findings
