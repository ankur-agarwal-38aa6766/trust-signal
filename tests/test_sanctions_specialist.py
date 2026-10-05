from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from trust_signal.agents.sanctions import SanctionsSpecialist
from trust_signal.connectors.base import SanctionsListing
from trust_signal.domain.identity import IdentityCandidate
from trust_signal.domain.sanctions import SanctionsSourceCoverage, ScreeningEvidence
from trust_signal.ingestion.pipeline import IngestionResult
from trust_signal.models import CaseRequest, SourceMode
from trust_signal.orchestration.case_graph import run_case
from trust_signal.persistence.contracts import ObservationReceipt
from trust_signal.resolution import EntityResolver
from trust_signal.screening.providers import PipelineSanctionsProvider
from trust_signal.screening.sanctions import (
    SanctionsDataset,
    SanctionsMatcher,
    VerifiedSanctionsRecord,
)

SOURCE = "us_ofac_sdn"
NOW = datetime(2026, 10, 4, tzinfo=UTC)
LEI = "INR2EJN1ERAN0W5ZP974"
HASH = "sha256:" + "a" * 64


def identity_pair():
    request = CaseRequest(party={"legal_name": "Microsoft Corporation", "lei": LEI},
                          source_mode=SourceMode.GLEIF_LIVE)
    candidate = IdentityCandidate(candidate_id="microsoft", source_id="gleif_lei_api",
                                  source_record_id=LEI, legal_name=request.party.legal_name,
                                  lei=LEI, observation_ids=["identity_raw"])
    return request, EntityResolver().resolve(request.party, [candidate])


def dataset(*, source=SOURCE, coverage="available", observed_at=NOW, **listing_fields):
    listing = SanctionsListing.model_validate({
        "source_id": source, "source_record_id": "listing_1",
        "legal_name": "Microsoft Corporation", "list_type": "entity", **listing_fields})
    evidence = ScreeningEvidence(observation_id="sanctions_raw", canonical_url="https://example.test/list",
                                 content_hash=HASH, connector_version="test-1", observed_at=observed_at)
    return SanctionsDataset(SanctionsSourceCoverage(source_id=source, coverage=coverage,
                                                   source_run_id="source_run"),
                            [VerifiedSanctionsRecord(listing, (evidence,))])


@pytest.mark.parametrize("fields,status", [
    ({}, "potential"),
    ({"lei": LEI}, "confirmed"),
    ({"lei": "OTHER000000000000000"}, "excluded"),
    ({"list_type": "individual", "lei": LEI}, "excluded"),
    ({"list_type": "vessel"}, "excluded"),
    ({"list_type": "unknown", "lei": LEI}, "potential"),
    ({"legal_name": "Unrelated Organization", "lei": LEI}, "potential"),
    ({"legal_name": "Unrelated Organization", "aliases": ["Microsoft Corporation"]}, "potential"),
    ({"jurisdiction": "US"}, "potential"),
])
def test_match_requires_authoritative_identifier_and_name(fields, status):
    request, resolution = identity_pair()
    result = SanctionsMatcher().screen(request, resolution, [dataset(**fields)], now=NOW)
    assert result.matches[0].status == status
    assert result.complete
    assert result.matches[0].evidence[0].observation_id == "sanctions_raw"


def test_unrelated_name_is_not_candidate():
    request, resolution = identity_pair()
    result = SanctionsMatcher().screen(request, resolution,
                                      [dataset(legal_name="Entirely Different Business")], now=NOW)
    assert result.outcome == "no_candidates"
    assert not result.matches
    assert result.sources[0].records_checked == 1


@pytest.mark.parametrize("age", [timedelta(days=2), -timedelta(minutes=6)])
def test_stale_or_future_evidence_cannot_be_clean_result(age):
    request, resolution = identity_pair()
    result = SanctionsMatcher().screen(request, resolution,
                                      [dataset(observed_at=NOW - age)], now=NOW)
    assert result.outcome == "incomplete"
    assert result.sources[0].coverage == "stale"
    assert not result.matches


def test_partial_snapshot_retains_matches_but_not_complete_coverage():
    request, resolution = identity_pair()
    result = SanctionsMatcher().screen(request, resolution, [dataset(coverage="partial")], now=NOW)
    assert result.outcome == "potential_match"
    assert not result.complete


def test_empty_snapshot_is_failure_not_no_candidates():
    request, resolution = identity_pair()
    empty = dataset()
    empty.records = []
    result = SanctionsMatcher().screen(request, resolution, [empty], now=NOW)
    assert result.sources[0].coverage == "failed"
    assert result.outcome == "incomplete"


def test_unconfirmed_or_wrong_request_never_fetches():
    request, resolution = identity_pair()
    provider = Mock()
    specialist = SanctionsSpecialist(provider, source_ids=[SOURCE])
    request.party.legal_name = "Wrong Corporation"
    with pytest.raises(ValueError, match="confirmed identity"):
        specialist(request, resolution)
    provider.load.assert_not_called()


def ingestion_result():
    item = dataset().records[0]
    return IngestionResult(
        run_id="source_run", source_id=SOURCE, coverage="available",
        records=[{**item.listing.model_dump(), "observation_ids": ["sanctions_raw"]}],
        receipts=[ObservationReceipt("sanctions_raw", SOURCE, "snapshot", HASH, 1, 1)],
        evidence=[{**item.evidence[0].model_dump(mode="json"), "source_id": SOURCE,
                   "source_record_id": "snapshot"}])


def test_pipeline_provider_verifies_lineage_before_release():
    pipeline = Mock()
    pipeline.ingest.return_value = ingestion_result()
    result = PipelineSanctionsProvider(pipeline).load(SOURCE)
    assert len(result.records) == 1
    assert result.coverage.coverage == "available"
    assert pipeline.ingest.call_args.args[0].operation == "snapshot"


@pytest.mark.parametrize("corrupt", ["receipt", "record", "metadata", "empty", "source", "duplicate"])
def test_provider_withholds_corrupted_snapshot(corrupt):
    result = ingestion_result()
    if corrupt == "receipt":
        result.receipts = [ObservationReceipt("sanctions_raw", SOURCE, "snapshot", HASH, 1, 0)]
    elif corrupt == "record":
        result.records[0]["observation_ids"] = ["not_stored"]
    elif corrupt == "metadata":
        result.evidence[0]["content_hash"] = "sha256:" + "b" * 64
    elif corrupt == "empty":
        result.records = []
    elif corrupt == "source":
        result.source_id = "another_source"
    else:
        result.records.append(result.records[0])
    pipeline = Mock()
    pipeline.ingest.return_value = result
    output = PipelineSanctionsProvider(pipeline).load(SOURCE)
    assert output.coverage.coverage == "failed"
    assert output.records == []


def test_storage_or_run_log_failure_is_sanitized():
    pipeline = Mock()
    pipeline.ingest.side_effect = RuntimeError("PRIVATE_KEY secret")
    result = PipelineSanctionsProvider(pipeline).load(SOURCE)
    assert result.coverage.error_category == "RuntimeError"
    assert "PRIVATE_KEY" not in str(result)


def test_name_candidate_is_unattributed_and_unscored():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.return_value = dataset()
    specialist = SanctionsSpecialist(provider, source_ids=[SOURCE], clock=lambda: NOW)
    result = specialist(request, resolution)
    assert result.findings[0].subject_id is None
    assert result.findings[0].verification_status == "sanctions_identity_pending"
    assert result.findings[0].risk_weight == 0
    assert result.findings[0].event_at is None
    assert specialist(request, resolution).findings[0].finding_id == result.findings[0].finding_id


def test_source_failure_does_not_discard_other_source_matches():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.side_effect = [RuntimeError("secret"), dataset(source="uk_fcdo_sanctions", lei=LEI)]
    specialist = SanctionsSpecialist(provider, source_ids=[SOURCE, "uk_fcdo_sanctions"], clock=lambda: NOW)
    result = specialist(request, resolution)
    assert result.status == "completed"
    assert not result.sanctions_screening.complete
    assert result.sanctions_screening.outcome == "confirmed_match"
    assert result.findings[0].subject_id == "microsoft"
    assert "secret" not in result.model_dump_json()


def test_stage_runner_persists_and_reuses_specialist_output():
    from test_workflow_stages import MemoryWorkflowStore, identity

    from trust_signal.domain.workflow import SPECIALIST_STAGES, WorkflowStage
    from trust_signal.orchestration.stages import StageRunner

    provider = Mock()
    provider.load.return_value = dataset()
    specialist = SanctionsSpecialist(provider, source_ids=[SOURCE], clock=lambda: NOW)
    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity, {WorkflowStage.SANCTIONS: specialist})
    runner.execute("run", WorkflowStage.IDENTITY)
    output = runner.execute("run", WorkflowStage.SANCTIONS)
    assert output == runner.execute("run", WorkflowStage.SANCTIONS)
    provider.load.assert_called_once_with(SOURCE)
    assert output["branch"]["sanctions_screening"]["outcome"] == "potential_match"
    for stage in SPECIALIST_STAGES:
        runner.execute("run", stage)
    runner.execute("run", WorkflowStage.AGGREGATE)
    runner.execute("run", WorkflowStage.VALIDATE)
    runner.execute("run", WorkflowStage.ASSESS)
    assert store.results[-1].assessment.risk_score is None
    assert store.results[-1].assessment.disposition == "analyst_review"


def test_local_graph_dispatches_confirmed_identity_to_specialist():
    from test_workflow_stages import identity

    request, _ = identity_pair()
    provider = Mock()
    provider.load.return_value = dataset()
    specialist = SanctionsSpecialist(provider, source_ids=[SOURCE], clock=lambda: NOW)
    result = run_case(request, branches={"registry": identity}, specialists={"sanctions": specialist})
    assert len(result.branches) == 2
    assert result.aggregation is not None
    assert result.assessment.risk_score is None
    assert result.assessment.disposition == "analyst_review"
    provider.load.assert_called_once()


def test_local_graph_stops_before_specialist_for_identity_conflict():
    from test_workflow_stages import identity

    request, _ = identity_pair()
    request.party.legal_name = "Wrong Corporation"
    provider = Mock()
    result = run_case(request, branches={"registry": identity}, specialists={
        "sanctions": SanctionsSpecialist(provider, source_ids=[SOURCE])})
    assert result.status == "needs_more_information"
    provider.load.assert_not_called()


@pytest.mark.parametrize("authority,status", [("registry", "confirmed"), ("other", "potential")])
def test_registration_confirmation_requires_matching_issuing_scope(authority, status):
    request = CaseRequest(party={"legal_name": "Example Company", "registration_id": "00123",
                                 "registration_authority": "registry", "jurisdiction": "NO"})
    candidate = IdentityCandidate(candidate_id="example", source_id="registry", source_record_id="00123",
                                  **request.party.model_dump(exclude={"website"}), observation_ids=["raw"])
    resolution = EntityResolver().resolve(request.party, [candidate])
    result = SanctionsMatcher().screen(request, resolution, [dataset(
        legal_name="Example Company", registration_id="00123", registration_authority=authority,
        registration_jurisdiction="NO")], now=NOW)
    assert result.matches[0].status == status


def test_real_ingestion_boundary_with_memory_storage_orders_writes_before_screening():
    from trust_signal.connectors.base import SourceBatch, SourceObservation
    from trust_signal.connectors.registry import SourceDefinition, SourceRegistry
    from trust_signal.ingestion.pipeline import IngestionPipeline

    observation = SourceObservation(
        source_id=SOURCE, source_record_id="snapshot", canonical_url="https://example.test/list",
        observed_at=NOW, content_hash=HASH, connector_version="test-1", raw_payload={"fixture": True})
    batch = SourceBatch(observations=[observation], records=[dataset().records[0].listing.model_dump()])
    registry = SourceRegistry([SourceDefinition(SOURCE, "test-1", ("US",), ("snapshot",),
                                                lambda _: iter([batch]))])
    store, runs, calls = Mock(), Mock(), Mock()
    store.store_observation.return_value = ObservationReceipt("sanctions_raw", SOURCE, "snapshot", HASH, 1, 1)
    calls.attach_mock(store.store_observation, "store")
    calls.attach_mock(runs.finish, "finish")
    pipeline = IngestionPipeline(registry, store, runs)
    request, resolution = identity_pair()
    branch = SanctionsSpecialist(PipelineSanctionsProvider(pipeline), source_ids=[SOURCE],
                                clock=lambda: NOW)(request, resolution)
    assert [call[0] for call in calls.mock_calls] == ["store", "finish"]
    assert branch.sanctions_screening.outcome == "potential_match"
    runs.finish.side_effect = RuntimeError("terminal log failed")
    failed = SanctionsSpecialist(PipelineSanctionsProvider(pipeline), source_ids=[SOURCE],
                                clock=lambda: NOW)(request, resolution)
    assert failed.status == "failed"
    assert failed.findings == []


@pytest.mark.parametrize("args", [
    ["--sanctions"],
    ["--sanctions-source", SOURCE],
    ["--sanctions", "--source-mode", "gleif_live", "--sanctions-source", SOURCE,
     "--sanctions-source", SOURCE],
])
def test_cli_rejects_invalid_screening_configuration_before_connecting(monkeypatch, args):
    from trust_signal import cli

    monkeypatch.setattr("sys.argv", ["trust-signal", "Example Company", *args])
    connection = Mock()
    monkeypatch.setattr(cli, "application_stores", connection)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    connection.assert_not_called()
