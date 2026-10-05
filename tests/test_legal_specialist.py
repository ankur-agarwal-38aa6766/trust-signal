from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from trust_signal.agents.legal import LEGAL_SOURCES, LegalSpecialist
from trust_signal.connectors.base import SourceEvent
from trust_signal.connectors.registry import default_registry
from trust_signal.domain.identity import IdentityCandidate
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.domain.sanctions import ScreeningEvidence
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import CaseRequest
from trust_signal.research.provider import PipelineResearchProvider, ResearchDataset
from trust_signal.resolution import EntityResolver

NOW = datetime(2026, 10, 4, tzinfo=UTC)
LEI = "INR2EJN1ERAN0W5ZP974"
WORLD_BANK = "worldbank_debarment"
FCA = "uk_fca_newsroom"
GAZETTE = "uk_gazette_insolvency"
COURT = "uk_find_case_law"


def identity_pair():
    request = CaseRequest(party={"legal_name": "Microsoft Corporation", "lei": LEI}, source_mode="gleif_live")
    candidate = IdentityCandidate(candidate_id="subject", source_id="gleif_lei_api", source_record_id=LEI,
                                  lei=LEI, legal_name=request.party.legal_name, observation_ids=["identity_raw"])
    return request, EntityResolver().resolve(request.party, [candidate])


def dataset(source=WORLD_BANK, **changes):
    operation, event_type, host = LEGAL_SOURCES[source]
    event = SourceEvent.model_validate({
        "source_id": source, "source_record_id": "event_1", "title": "Microsoft Corporation",
        "subject_name": "Microsoft Corporation" if source == WORLD_BANK else None,
        "event_type": event_type, "canonical_url": f"https://{host}/notice/1",
        "procedural_status": "debarment_listing" if source == WORLD_BANK else "unknown",
        **changes})
    proof = ScreeningEvidence(observation_id="raw", canonical_url=f"https://{host}/feed",
                              content_hash="sha256:" + "a" * 64, connector_version="test-1", observed_at=NOW)
    return ResearchDataset(ResearchCoverage(source_id=source, operation=operation,
                                            coverage="available", source_run_id="source_run"),
                            records=[{**event.model_dump(mode="json"), "observation_ids": ["raw"]}],
                            evidence={"raw": proof})


def run(data):
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.return_value = data
    specialist = LegalSpecialist(provider, source_ids=[data.coverage.source_id], clock=lambda: NOW)
    return specialist(request, resolution)


def test_named_debarment_candidate_preserves_eligibility_and_does_not_infer_guilt():
    branch = run(dataset(outcome="Conditional eligibility", metadata={
        "INELIG_FLG": "N", "DEBAR_FROM_DATE": "2024-01-01", "DEBAR_TO_DATE": "2025-01-01"}))
    candidate = branch.legal_research.candidates[0]
    assert candidate.status == "potential"
    assert candidate.event["metadata"]["INELIG_FLG"] == "N"
    assert candidate.event["outcome"] == "Conditional eligibility"
    assert branch.findings[0].subject_id is None
    assert branch.findings[0].procedural_status == "debarment_listing"
    assert branch.findings[0].risk_weight == 0
    assert branch.findings[0].event_at is None


@pytest.mark.parametrize("status,finality", [
    ("allegation", "unknown"), ("proceeding", "unknown"), ("decision", "appealable"),
    ("final_decision", "final"), ("judgment_published", "under_appeal"),
])
def test_procedural_status_and_finality_are_never_promoted(status, finality):
    branch = run(dataset(COURT, procedural_status=status, finality=finality,
                         title="Microsoft Corporation v Other Company", published_at="2026-09-01"))
    candidate = branch.legal_research.candidates[0]
    assert candidate.event["procedural_status"] == status
    assert candidate.event["finality"] == finality
    assert candidate.relevance == "title_mention"
    assert "event_party_role_unknown" in candidate.reason_codes
    assert branch.findings[0].procedural_status == status
    assert branch.findings[0].event_at is None


@pytest.mark.parametrize("title,expected", [
    ("FCA fines Microsoft Corporation", True),
    ("Microsoft Corporation seeks injunction", True),
    ("MICROSOFT CORPORATION: petition dismissed", True),
    ("Microsoft CorporationXYZ fined", False),
    ("Other Company sanctioned", False),
])
def test_headline_relevance_uses_bounded_full_name_not_search_result_presence(title, expected):
    branch = run(dataset(FCA, title=title))
    assert bool(branch.findings) == expected
    if expected:
        assert branch.findings[0].subject_id is None


@pytest.mark.parametrize("identifier,status", [(LEI, "confirmed"), ("OTHER0000000000000000", "excluded")])
def test_authoritative_identifier_can_confirm_or_exclude_identity_not_adverse_outcome(identifier, status):
    branch = run(dataset(subject_lei=identifier))
    assert branch.legal_research.candidates[0].status == status
    if status == "confirmed":
        assert branch.findings[0].subject_id == "subject"
    else:
        assert branch.findings == []


def test_identifier_only_name_conflict_remains_review_candidate():
    branch = run(dataset(subject_name="Entirely Different Company", subject_lei=LEI))
    assert branch.legal_research.candidates[0].status == "potential"
    assert branch.findings[0].subject_id is None


@pytest.mark.parametrize("corruption", ["source", "type", "url", "duplicate", "lineage", "empty_id", "status"])
def test_invalid_dataset_is_withheld_not_silently_partial(corruption):
    data = dataset()
    if corruption == "source":
        data.records[0]["source_id"] = FCA
    elif corruption == "type":
        data.records[0]["event_type"] = "news"
    elif corruption == "url":
        data.records[0]["canonical_url"] = "https://untrusted.example/notice"
    elif corruption == "duplicate":
        data.records.append(data.records[0].copy())
    elif corruption == "lineage":
        data.records[0]["observation_ids"] = ["not_persisted"]
    elif corruption == "empty_id":
        data.records[0]["source_record_id"] = ""
    else:
        data.records[0]["procedural_status"] = "convicted_from_title"
    branch = run(data)
    assert branch.findings == []
    assert branch.legal_research.candidates == []
    assert branch.legal_research.coverage[0].coverage == "failed"


@pytest.mark.parametrize("source,expected", [(WORLD_BANK, "failed"), (FCA, "no_matches")])
def test_empty_debarment_snapshot_and_verified_empty_feed_differ(source, expected):
    data = dataset(source)
    data.records = []
    data.coverage.coverage = "no_matches"
    branch = run(data)
    assert branch.legal_research.coverage[0].coverage == expected
    assert branch.findings == []


@pytest.mark.parametrize("age", [timedelta(days=2), -timedelta(minutes=6)])
def test_stale_and_future_evidence_are_withheld(age):
    data = dataset()
    data.evidence["raw"].observed_at = NOW - age
    branch = run(data)
    assert branch.legal_research.coverage[0].coverage == "stale"
    assert branch.findings == []


def test_partial_feed_retains_candidate_with_explicit_gap():
    data = dataset(FCA)
    data.coverage.coverage = "partial"
    branch = run(data)
    assert len(branch.findings) == 1
    assert any("coverage partial" in text for text in branch.limitations)


def test_source_failure_keeps_other_source_candidates_and_sanitizes_error():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.side_effect = [RuntimeError("private token"), dataset(FCA)]
    branch = LegalSpecialist(provider, source_ids=[WORLD_BANK, FCA], clock=lambda: NOW)(request, resolution)
    assert branch.status == "completed"
    assert len(branch.findings) == 1
    assert "private token" not in branch.model_dump_json()


def test_court_gate_blocks_fetch_without_permission_and_logs_gap():
    request, resolution = identity_pair()
    observations, runs = Mock(), Mock()
    pipeline = IngestionPipeline(default_registry({}), observations, runs)
    branch = LegalSpecialist(PipelineResearchProvider(pipeline), source_ids=[COURT],
                             clock=lambda: NOW)(request, resolution)
    assert branch.legal_research.coverage[0].coverage == "blocked"
    assert branch.status == "failed"
    assert branch.findings == []
    observations.store_observation.assert_not_called()
    runs.finish.assert_called_once()


@pytest.mark.parametrize("code,status,outcome", [
    ("2450", "proceeding", None),
    ("2452", "decision", "winding_up_order_published"),
    ("2461", "decision", "petition_dismissal_published"),
])
def test_gazette_adapter_ingestion_and_specialist_preserve_petition_order_dismissal(code, status, outcome):
    import httpx

    from trust_signal.connectors.feeds import GazetteInsolvencyAdapter
    from trust_signal.connectors.registry import SourceDefinition, SourceRegistry
    from trust_signal.persistence.contracts import ObservationReceipt

    raw = (f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:f="https://www.thegazette.co.uk/facets">'
           f'<entry><id>notice-1</id><title>Microsoft Corporation</title>'
           f'<link href="https://www.thegazette.co.uk/notice/1"/>'
           f'<f:notice-code>{code}</f:notice-code></entry></feed>').encode()

    def fetch(query):
        with GazetteInsolvencyAdapter(transport=httpx.MockTransport(
                lambda _: httpx.Response(200, content=raw))) as adapter:
            yield from adapter.search(query.value, query.max_pages)

    registry = SourceRegistry([SourceDefinition(GAZETTE, "test-1", ("GB",), ("search",), fetch)])
    observations, runs = Mock(), Mock()
    observations.store_observation.side_effect = lambda observation: ObservationReceipt(
        "gazette_raw", observation.source_id, observation.source_record_id, observation.content_hash, 1, 1)
    pipeline = IngestionPipeline(registry, observations, runs)
    request, resolution = identity_pair()
    branch = LegalSpecialist(PipelineResearchProvider(pipeline), source_ids=[GAZETTE])(request, resolution)
    event = branch.legal_research.candidates[0].event
    assert event["procedural_status"] == status
    assert event["outcome"] == outcome
    assert event["finality"] == "unknown"
    assert branch.findings[0].observation_ids == ["gazette_raw"]
    observations.store_observation.assert_called_once()
    runs.finish.assert_called_once()


def test_unresolved_identity_blocks_all_provider_calls():
    request, resolution = identity_pair()
    resolution.matches[0].eligible_for_attribution = False
    provider = Mock()
    with pytest.raises(ValueError, match="confirmed identity"):
        LegalSpecialist(provider)(request, resolution)
    provider.load.assert_not_called()


def test_search_name_is_not_silently_truncated():
    request, resolution = identity_pair()
    long_name = "Example " * 28
    request.party.legal_name = long_name
    resolution.matches[0].candidate.legal_name = long_name
    provider = Mock()
    branch = LegalSpecialist(provider, source_ids=[GAZETTE], clock=lambda: NOW)(request, resolution)
    provider.load.assert_not_called()
    assert branch.legal_research.coverage[0].error_category == "QueryNameTooLong"


def test_graph_aggregation_stage_persistence_and_retry_without_fake_scoring():
    from test_workflow_stages import MemoryWorkflowStore, identity

    from trust_signal.domain.workflow import SPECIALIST_STAGES, WorkflowStage
    from trust_signal.orchestration.case_graph import run_case
    from trust_signal.orchestration.stages import StageRunner

    request, _ = identity_pair()
    provider = Mock()
    provider.load.side_effect = lambda _: dataset()
    handler = LegalSpecialist(provider, source_ids=[WORLD_BANK], clock=lambda: NOW)
    result = run_case(request, branches={"registry": identity}, specialists={"legal": handler})
    assert result.aggregation is not None
    assert result.assessment.risk_score is None
    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity, {WorkflowStage.LEGAL: handler})
    runner.execute("run", WorkflowStage.IDENTITY)
    output = runner.execute("run", WorkflowStage.LEGAL)
    assert output == runner.execute("run", WorkflowStage.LEGAL)
    assert provider.load.call_count == 2
    for stage in SPECIALIST_STAGES:
        runner.execute("run", stage)
    runner.execute("run", WorkflowStage.AGGREGATE)
    runner.execute("run", WorkflowStage.VALIDATE)
    runner.execute("run", WorkflowStage.ASSESS)
    assert store.results[-1].assessment.disposition == "analyst_review"


@pytest.mark.parametrize("args", [["--legal"], ["--legal-source", WORLD_BANK],
                                  ["--legal", "--source-mode", "gleif_live", "--legal-source", FCA,
                                   "--legal-source", FCA]])
def test_cli_rejects_invalid_legal_options_before_connecting(monkeypatch, args):
    from trust_signal import cli

    monkeypatch.setattr("sys.argv", ["trust-signal", "Example Company", *args])
    connection = Mock()
    monkeypatch.setattr(cli, "application_stores", connection)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    connection.assert_not_called()
