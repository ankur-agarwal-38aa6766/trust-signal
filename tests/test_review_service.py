from concurrent.futures import ThreadPoolExecutor

import pytest
from test_evidence_validation import inputs, validate

from trust_signal.domain.review import ReviewCommand, ReviewerContext
from trust_signal.models import Assessment, CaseResult
from trust_signal.research.review import ReviewConflict, ReviewService, SqliteReviewStore


def setup(tmp_path):
    values = inputs()
    request, resolution, branches, aggregation = values
    case = CaseResult(case_id="case", party=request.party, status="completed_with_gaps",
                      identity_status="resolved", identity_resolution=resolution, branches=branches,
                      aggregation=aggregation, validation=validate(values),
                      assessment=Assessment(score_status="not_scored", disposition="analyst_review"))
    service = ReviewService(SqliteReviewStore(tmp_path / "reviews.sqlite"))
    actor = ReviewerContext(tenant_id="tenant", user_id="reviewer", role="reviewer")
    digest = service.register(actor, case)
    command = ReviewCommand(request_id="request", case_id="case", snapshot_hash=digest,
                            expected_version=0, action="review", rationale="Evidence needs further analyst review.")
    return service, actor, case, command


def test_decision_is_durable_idempotent_and_does_not_change_assessment(tmp_path):
    service, actor, case, command = setup(tmp_path)
    receipt = service.decide(actor, command)
    assert receipt == service.decide(actor, command)
    restarted = ReviewService(SqliteReviewStore(tmp_path / "reviews.sqlite"))
    assert restarted.history(actor, "case") == [receipt]
    assert case.assessment.risk_score is None
    assert receipt.version == 1


def test_request_details_requires_questions(tmp_path):
    service, actor, _, command = setup(tmp_path)
    command.action = "request_details"
    with pytest.raises(ValueError, match="questions"):
        service.decide(actor, command)
    command.questions = ["Provide the official registry identifier."]
    assert service.decide(actor, command).state == "details_requested"


@pytest.mark.parametrize("change", ["version", "snapshot", "idempotency", "reviewer"])
def test_stale_or_changed_command_conflicts(tmp_path, change):
    service, actor, _, command = setup(tmp_path)
    service.decide(actor, command)
    if change == "version":
        command.request_id = "new"
    elif change == "snapshot":
        command.request_id = "new"
        command.expected_version = 1
        command.snapshot_hash = "sha256:" + "b" * 64
    elif change == "idempotency":
        command.rationale = "A different rationale for the same key."
    else:
        actor.user_id = "other_reviewer"
    with pytest.raises(ReviewConflict):
        service.decide(actor, command)
    assert len(service.history(actor, "case")) == 1


def test_tenant_and_viewer_boundaries(tmp_path):
    service, actor, _, command = setup(tmp_path)
    actor.tenant_id = "other_tenant"
    with pytest.raises(LookupError):
        service.decide(actor, command)
    assert service.history(actor, "case") == []
    actor.role = "viewer"
    with pytest.raises(PermissionError):
        service.decide(actor, command)
    with pytest.raises(PermissionError):
        service.history(actor, "case")


def test_rejection_needs_acknowledgment_evidence_and_supervisor_reopen(tmp_path):
    service, actor, _, command = setup(tmp_path)
    command.action = "reject"
    with pytest.raises(ValueError, match="acknowledgment"):
        service.decide(actor, command)
    command.finding_ids, command.acknowledge_limitations = ["finding"], True
    assert service.decide(actor, command).state == "rejected"
    command.request_id, command.expected_version, command.action = "next", 1, "review"
    with pytest.raises(ReviewConflict, match="reopen"):
        service.decide(actor, command)
    command.action = "reopen"
    with pytest.raises(PermissionError):
        service.decide(actor, command)
    actor.role = "supervisor"
    assert service.decide(actor, command).state == "awaiting_review"
    assert [event.version for event in service.history(actor, "case")] == [1, 2]


@pytest.mark.parametrize("ids", [["unknown"], ["finding", "finding"]])
def test_unknown_or_duplicate_evidence_references_are_blocked(tmp_path, ids):
    service, actor, _, command = setup(tmp_path)
    command.finding_ids = ids
    with pytest.raises(ValueError, match="findings"):
        service.decide(actor, command)
    assert service.history(actor, "case") == []


def test_research_snapshot_is_immutable(tmp_path):
    service, actor, case, _ = setup(tmp_path)
    case.branches[0].findings[0].claim = "Modified source claim"
    with pytest.raises(ReviewConflict, match="immutable"):
        service.register(actor, case)


def test_parallel_reviewers_cannot_overwrite_same_version(tmp_path):
    service, actor, _, command = setup(tmp_path)

    def submit(identifier):
        try:
            return service.decide(actor, command.model_copy(update={"request_id": identifier})).version
        except ReviewConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, ["one", "two"]))
    assert sorted(str(value) for value in results) == ["1", "conflict"]
    assert len(service.history(actor, "case")) == 1


def test_rejection_without_validation_is_blocked(tmp_path):
    service, actor, case, _ = setup(tmp_path)
    case.case_id = "unvalidated"
    case.validation = None
    digest = service.register(actor, case)
    command = ReviewCommand(request_id="reject", case_id=case.case_id, snapshot_hash=digest,
                            expected_version=0, action="reject", rationale="Documented reviewer business decision.",
                            finding_ids=["finding"], acknowledge_limitations=True)
    with pytest.raises(ValueError, match="validation"):
        service.decide(actor, command)
