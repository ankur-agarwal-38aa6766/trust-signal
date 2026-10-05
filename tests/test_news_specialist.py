from datetime import timedelta
from unittest.mock import Mock

import pytest
from test_legal_specialist import FCA, NOW, dataset, identity_pair

from trust_signal.agents.news import NewsSpecialist

GDELT = "gdelt_doc_news"


def news_dataset(*, title="Microsoft Corporation announces results"):
    data = dataset(FCA, title=title)
    data.coverage.source_id, data.coverage.operation = GDELT, "search"
    data.coverage.coverage = "partial"
    data.records[0].update(source_id=GDELT, event_type="news_report", canonical_url="https://publisher.test/article",
                           metadata={"provider_seen_at": "20261004T010000Z", "language": "English",
                                     "publisher_trust": "not_assessed", "content_rights": "metadata_and_links_only"})
    return data


def run(data):
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.return_value = data
    return NewsSpecialist(provider, source_ids=[data.coverage.source_id], clock=lambda: NOW)(request, resolution)


def test_metadata_mentions_stay_pending_and_seen_time_is_not_event_time():
    branch = run(news_dataset())
    candidate = branch.news_research.candidates[0]
    assert candidate.publisher_trust == "not_assessed"
    assert candidate.event["metadata"]["language"] == "English"
    assert candidate.event["metadata"]["content_rights"] == "metadata_and_links_only"
    assert branch.findings[0].subject_id is None
    assert branch.findings[0].event_at is None
    assert branch.findings[0].risk_weight == 0
    assert branch.news_research.coverage[0].coverage == "partial"


def test_official_feed_trust_is_separate_from_claim_verification():
    branch = run(dataset(FCA))
    assert branch.news_research.candidates[0].publisher_trust == "official_newsroom"
    assert branch.findings[0].verification_status == "news_identity_pending"


@pytest.mark.parametrize("title,match", [("Microsoft CorporationXYZ update", False),
                                        ("Other Company update", False),
                                        ("MICROSOFT CORPORATION update", True)])
def test_bounded_name_relevance(title, match):
    assert bool(run(news_dataset(title=title)).findings) == match


def test_same_title_groups_are_candidates_not_corroboration():
    data = news_dataset()
    another = data.records[0].copy()
    another.update(source_record_id="event_2", canonical_url="https://second.test/article")
    data.records.append(another)
    branch = run(data)
    first, second = branch.news_research.candidates
    assert first.possible_duplicate_group == second.possible_duplicate_group
    assert len(branch.findings) == 2


def test_exact_url_repeats_are_deduplicated():
    data = news_dataset()
    data.records.append({**data.records[0], "source_record_id": "event_2"})
    assert len(run(data).findings) == 1


@pytest.mark.parametrize("corruption", ["source", "url", "lineage", "duplicate", "type"])
def test_corrupted_source_withholds_candidates(corruption):
    data = news_dataset()
    if corruption == "source":
        data.records[0]["source_id"] = FCA
    elif corruption == "url":
        data.records[0]["canonical_url"] = "javascript:alert(1)"
    elif corruption == "lineage":
        data.records[0]["observation_ids"] = ["missing"]
    elif corruption == "duplicate":
        data.records.append(data.records[0].copy())
    else:
        data.records[0]["event_type"] = "conviction"
    branch = run(data)
    assert branch.findings == []
    assert branch.news_research.coverage[0].coverage == "failed"


@pytest.mark.parametrize("age", [timedelta(days=2), -timedelta(minutes=6)])
def test_stale_or_future_retrieval_is_withheld(age):
    data = news_dataset()
    data.evidence["raw"].observed_at = NOW - age
    assert run(data).news_research.coverage[0].coverage == "stale"


def test_unconfirmed_identity_never_fetches():
    request, resolution = identity_pair()
    resolution.matches[0].eligible_for_attribution = False
    provider = Mock()
    with pytest.raises(ValueError, match="confirmed identity"):
        NewsSpecialist(provider)(request, resolution)
    provider.load.assert_not_called()


def test_unsupported_search_syntax_blocks_gdelt_without_rewriting_name():
    request, resolution = identity_pair()
    request.party.legal_name = resolution.matches[0].candidate.legal_name = "Example (Holdings) Ltd"
    provider = Mock()
    branch = NewsSpecialist(provider, source_ids=[GDELT], clock=lambda: NOW)(request, resolution)
    assert branch.news_research.coverage[0].coverage == "blocked"
    provider.load.assert_not_called()


def test_source_outage_preserves_official_feed_without_secret_leak():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.side_effect = [RuntimeError("private token"), dataset(FCA)]
    branch = NewsSpecialist(provider, clock=lambda: NOW)(request, resolution)
    assert branch.status == "completed"
    assert len(branch.findings) == 1
    assert "private token" not in branch.model_dump_json()


def test_verified_empty_search_is_not_source_failure():
    data = news_dataset()
    data.records = []
    data.coverage.coverage = "no_matches"
    branch = run(data)
    assert branch.status == "completed"
    assert not branch.findings


def test_graph_and_stage_runner_persist_news_and_reuse_on_retry():
    from test_workflow_stages import MemoryWorkflowStore, identity

    from trust_signal.domain.workflow import SPECIALIST_STAGES, WorkflowStage
    from trust_signal.orchestration.case_graph import run_case
    from trust_signal.orchestration.stages import StageRunner

    request, _ = identity_pair()
    provider = Mock()
    provider.load.side_effect = lambda _: news_dataset()
    handler = NewsSpecialist(provider, source_ids=[GDELT], clock=lambda: NOW)
    result = run_case(request, branches={"registry": identity}, specialists={"news": handler})
    assert result.aggregation is not None
    assert result.assessment.risk_score is None
    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity, {WorkflowStage.NEWS: handler})
    runner.execute("run", WorkflowStage.IDENTITY)
    output = runner.execute("run", WorkflowStage.NEWS)
    assert output == runner.execute("run", WorkflowStage.NEWS)
    assert provider.load.call_count == 2
    for stage in SPECIALIST_STAGES:
        runner.execute("run", stage)
    runner.execute("run", WorkflowStage.AGGREGATE)
    runner.execute("run", WorkflowStage.VALIDATE)
    runner.execute("run", WorkflowStage.ASSESS)
    assert store.results[-1].assessment.disposition == "analyst_review"


@pytest.mark.parametrize("args", [["--news"], ["--news-source", GDELT],
                                  ["--news", "--source-mode", "gleif_live", "--news-source", GDELT,
                                   "--news-source", GDELT]])
def test_cli_validates_before_connecting(monkeypatch, args):
    from trust_signal import cli

    monkeypatch.setattr("sys.argv", ["trust-signal", "Example Company", *args])
    connection = Mock()
    monkeypatch.setattr(cli, "application_stores", connection)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    connection.assert_not_called()
