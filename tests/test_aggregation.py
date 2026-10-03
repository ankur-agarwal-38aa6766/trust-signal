from datetime import UTC, datetime

import pytest

from trust_signal.aggregation import EvidenceAggregator
from trust_signal.domain.aggregation import AggregationResult
from trust_signal.domain.identity import IdentityCandidate
from trust_signal.models import BranchResult, CaseRequest, Finding, PartyInput
from trust_signal.orchestration.case_graph import run_case
from trust_signal.resolution import EntityResolver


def finding(finding_id, **changes):
    return Finding(**{
        "finding_id": finding_id, "branch_id": "registry", "claim_type": "registered_status",
        "claim": "Company is active.", "subject": "Example Company", "source_id": "registry_a",
        "source_name": "Registry A", "source_record_id": "123", "evidence_mode": "live_source",
        "observed_at": datetime(2026, 10, 3, tzinfo=UTC),
        "claim_key": "registration.status", "claim_value": "active", "claim_cardinality": "single",
        **changes,
    })


def branch(*items, **changes):
    return BranchResult(**{"branch_id": "registry", "status": "completed",
                           "findings": list(items), **changes})


def test_duplicate_content_is_retained_and_counted_once():
    first = finding("a", content_hash="sha256:" + "a" * 64, observation_ids=["raw_a"])
    second = finding("b", content_hash=first.content_hash, source_id="publisher_b",
                     claim="Active company.", observation_ids=["raw_b"])
    result = EvidenceAggregator().aggregate([branch(first, second)])
    group = result.groups[0]
    assert group.finding_ids == ["a", "b"]
    assert group.observation_ids == ["raw_a", "raw_b"]
    assert group.source_ids == ["publisher_b", "registry_a"]
    assert group.duplicate_sets == [["a", "b"]]
    assert group.distinct_evidence_count == 1
    assert group.relation == "duplicate_evidence"
    assert first.claim == "Company is active."


def test_different_structured_values_flag_potential_conflict():
    result = EvidenceAggregator().aggregate([branch(finding("a"),
                                                   finding("b", claim_value="dissolved"))])
    assert result.groups[0].relation == "potential_conflict"
    assert result.comparison_board[0].finding_ids == ["a", "b"]


def test_multiple_directors_are_combined_without_conflict():
    result = EvidenceAggregator().aggregate([branch(
        finding("a", claim_key="board.director", claim_value="Person A", claim_cardinality="multiple"),
        finding("b", claim_key="board.director", claim_value="Person B", claim_cardinality="multiple"))])
    assert result.groups[0].relation == "combined_members"
    assert result.groups[0].values == ["Person A", "Person B"]


def test_unknown_cardinality_and_free_text_do_not_infer_contradictions():
    for changes in ({"claim_cardinality": "unknown"}, {"claim_key": None, "claim_value": None}):
        result = EvidenceAggregator().aggregate([branch(
            finding("a", **changes), finding("b", claim="Dissolved company.", **changes))])
        assert result.groups[0].relation != "potential_conflict"


def test_matching_values_are_consistent_but_not_independent_corroboration():
    result = EvidenceAggregator().aggregate([branch(finding("a"), finding("b", source_id="other"))])
    assert result.groups[0].relation == "consistent_claims"
    assert not result.groups[0].identity_confirmed
    assert any("independent corroboration" in limitation for limitation in result.limitations)


def test_empty_results_and_missing_hashes_do_not_imply_clean_risk_or_deduplication():
    empty = EvidenceAggregator().aggregate([])
    assert empty.groups == [] and empty.timeline == []
    assert any("Identity is not resolved" in limitation for limitation in empty.limitations)
    group = EvidenceAggregator().aggregate([branch(finding("a"), finding("b"))]).groups[0]
    assert group.distinct_evidence_count == 2
    assert group.duplicate_sets == []


def test_identity_and_mode_boundaries_are_preserved():
    result = EvidenceAggregator().aggregate([branch(
        finding("a", subject_id="party_a"), finding("b", subject_id="party_b"),
        finding("c", subject_id="party_a", evidence_mode="demo_fixture"))])
    assert len(result.groups) == 3


def test_different_periods_and_events_are_separate_and_timeline_uses_event_time():
    old = datetime(2025, 1, 1, tzinfo=UTC)
    recent = datetime(2026, 1, 1, tzinfo=UTC)
    result = EvidenceAggregator().aggregate([branch(
        finding("a", event_at=recent, effective_at=recent),
        finding("b", event_at=old, effective_at=old, claim_value="pending"), finding("c"))])
    assert len(result.groups) == 3
    assert [entry.event_at for entry in result.timeline] == [old, recent]
    assert all("c" not in entry.finding_ids for entry in result.timeline)


def test_naive_event_timestamps_are_rejected():
    with pytest.raises(ValueError, match="timezone"):
        finding("a", event_at=datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None))


def test_replayed_finding_id_is_deduplicated_but_conflicting_id_is_rejected():
    item = finding("a")
    assert EvidenceAggregator().aggregate([branch(item, item)]).groups[0].finding_ids == ["a"]
    with pytest.raises(ValueError, match="conflicting finding"):
        EvidenceAggregator().aggregate([branch(item, finding("a", claim_value="other"))])


def test_order_independence_and_coverage_gaps():
    first = branch(finding("a"))
    second = branch(finding("b", branch_id="news"), branch_id="news", status="failed",
                    limitations=["Timeout"], error="Fetch failed")
    aggregator = EvidenceAggregator()
    result = aggregator.aggregate([first, second])
    assert result == aggregator.aggregate([second, first])
    assert result.coverage[0].status == "failed"
    assert result.coverage[0].limitations == ["Timeout"]
    assert any("coverage is incomplete" in item for item in result.limitations)
    assert result.groups[0].finding_ids == ["a", "b"]


def test_identity_confirmation_requires_explicit_selected_subject():
    lei = "INR2EJN1ERAN0W5ZP974"
    resolution = EntityResolver().resolve(PartyInput(legal_name="Example Company", lei=lei), [
        IdentityCandidate(candidate_id="party_a", source_id="registry", source_record_id=lei,
                          legal_name="Example Company", lei=lei)])
    result = EvidenceAggregator().aggregate([branch(finding("a", subject_id="party_a"),
                                                   finding("b"))], resolution)
    assert next(g for g in result.groups if g.subject_key == "id:party_a").identity_confirmed
    assert not next(g for g in result.groups if g.subject_key.startswith("name:")).identity_confirmed


def test_workflow_exposes_aggregation_and_supports_replacement():
    request = CaseRequest(party={"legal_name": "Example Company", "jurisdiction": "GB",
                                 "registration_id": "123"})
    result = run_case(request, {"registry": lambda _: branch(finding("a"))})
    assert result.aggregation.groups[0].finding_ids == ["a"]
    assert result.comparison_board == result.aggregation.comparison_board

    class Replacement:
        def aggregate(self, branches, identity=None):
            return AggregationResult(policy_version="custom-test", limitations=["Custom aggregator"])

    result = run_case(request, {"registry": lambda _: branch(finding("a"))}, aggregator=Replacement())
    assert result.aggregation.policy_version == "custom-test"
    assert result.branches[0].findings[0].finding_id == "a"
