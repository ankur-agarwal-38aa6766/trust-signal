from copy import deepcopy
from datetime import UTC, datetime

import pytest

from trust_signal.domain.identity import IdentityCandidate
from trust_signal.domain.workflow import SPECIALIST_STAGES, StageAttempt, WorkflowRun, WorkflowStage
from trust_signal.models import BranchResult, Finding
from trust_signal.orchestration.stages import ResearchUnavailableError, StageRunner
from trust_signal.resolution import EntityResolver

LEI = "INR2EJN1ERAN0W5ZP974"


class MemoryWorkflowStore:
    def __init__(self):
        self.run = WorkflowRun(run_id="run", graph_run_id="graph", request_id="request",
                               case_id="case", tenant_id="demo", request_payload={
                                   "party": {"legal_name": "Microsoft Corporation", "lei": LEI},
                                   "source_mode": "configured_sources"})
        self.attempts = {}
        self.results = []

    def load(self, run_id):
        assert run_id == self.run.run_id
        return self.run

    def latest(self, run_id, stage):
        return deepcopy(self.attempts.get(stage))

    def start(self, run_id, stage):
        old = self.attempts.get(stage)
        number = old.attempt + 1 if old else 1
        attempt = StageAttempt(attempt_id=f"{stage}_{number}", run_id=run_id, stage=stage,
                               attempt=number, status="running")
        self.attempts[stage] = deepcopy(attempt)
        return attempt

    def complete(self, attempt, output, status):
        self.attempts[attempt.stage] = attempt.model_copy(update={"output": output, "status": status})

    def fail(self, attempt, error_category):
        if self.attempts[attempt.stage].status == "running":
            self.attempts[attempt.stage].status = "failed"
            self.attempts[attempt.stage].error_category = error_category

    def finish(self, run_id, result):
        self.run.status = str(result.status)
        self.results.append(result)


def identity(request):
    candidate = IdentityCandidate(candidate_id="microsoft", source_id="gleif_lei_api",
                                  source_record_id=LEI, legal_name="Microsoft Corporation",
                                  lei=LEI, observation_ids=["raw_1"])
    resolution = EntityResolver().resolve(request.party, [candidate])
    return BranchResult(branch_id="registry", status="completed", identity_resolution=resolution,
                        findings=[Finding(branch_id="registry", claim_type="legal_identity_record",
                                          claim="Retrieved official record", subject=candidate.legal_name,
                                          subject_id="microsoft", source_id=candidate.source_id,
                                          source_name="GLEIF", source_record_id=LEI,
                                          observation_ids=["raw_1"], evidence_mode="live_source",
                                          observed_at=datetime(2026, 10, 3, tzinfo=UTC))])


def test_identity_fanout_aggregation_validation_and_review_without_fake_scoring():
    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity)
    assert runner.execute("run", WorkflowStage.IDENTITY)["confirmed"]
    for stage in SPECIALIST_STAGES:
        assert runner.execute("run", stage)["branch"]["status"] == "skipped"
    aggregation = runner.execute("run", WorkflowStage.AGGREGATE)["aggregation"]
    assert len(aggregation["coverage"]) == 5
    assert runner.execute("run", WorkflowStage.VALIDATE)["eligible_finding_ids"] == []
    runner.execute("run", WorkflowStage.ASSESS)
    result = store.results[-1]
    assert result.assessment.risk_score is None
    assert result.assessment.disposition == "analyst_review"
    assert store.run.status == "completed_with_gaps"


def test_unresolved_identity_finishes_for_clarification_and_cannot_fanout():
    store = MemoryWorkflowStore()
    store.run.request_payload["party"]["legal_name"] = "Other Company"
    runner = StageRunner(store, identity)
    assert not runner.execute("run", WorkflowStage.IDENTITY)["confirmed"]
    assert store.results[-1].status == "needs_more_information"
    with pytest.raises(RuntimeError, match="reconcile"):
        runner.execute("run", WorkflowStage.SANCTIONS)
    assert store.latest("run", WorkflowStage.SANCTIONS).error_category == "ValueError"


def test_confirmation_without_persisted_provenance_is_blocked():
    def unpersisted(request):
        branch = identity(request)
        branch.findings[0].observation_ids = []
        return branch

    store = MemoryWorkflowStore()
    assert not StageRunner(store, unpersisted).execute("run", WorkflowStage.IDENTITY)["confirmed"]


def test_completed_stage_retry_reuses_output_without_research():
    calls = []

    def counted(request):
        calls.append(request.case_id)
        return identity(request)

    store = MemoryWorkflowStore()
    runner = StageRunner(store, counted)
    first = runner.execute("run", WorkflowStage.IDENTITY)
    assert first == runner.execute("run", WorkflowStage.IDENTITY)
    assert calls == ["case"]
    assert store.latest("run", WorkflowStage.IDENTITY).attempt == 1


def test_expected_source_outage_is_gap_but_programming_failure_is_retryable():
    def unavailable(_request, _identity):
        raise ResearchUnavailableError("private provider details")

    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity, {WorkflowStage.SANCTIONS: unavailable})
    runner.execute("run", WorkflowStage.IDENTITY)
    output = runner.execute("run", WorkflowStage.SANCTIONS)
    assert output["branch"]["status"] == "failed"
    assert "private provider details" not in str(output)

    def broken(_request, _identity):
        raise RuntimeError("secret data")

    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity, {WorkflowStage.NEWS: broken})
    runner.execute("run", WorkflowStage.IDENTITY)
    with pytest.raises(RuntimeError, match="reconcile") as caught:
        runner.execute("run", WorkflowStage.NEWS)
    assert "secret data" not in str(caught.value)
    assert store.latest("run", WorkflowStage.NEWS).status == "failed"
    runner.specialists[WorkflowStage.NEWS] = lambda request, resolution: BranchResult(
        branch_id="news", status="completed")
    runner.execute("run", WorkflowStage.NEWS)
    assert store.latest("run", WorkflowStage.NEWS).attempt == 2


def test_missing_branch_output_prevents_aggregation_and_bad_input_is_not_researched():
    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity)
    runner.execute("run", WorkflowStage.IDENTITY)
    with pytest.raises(RuntimeError):
        runner.execute("run", WorkflowStage.AGGREGATE)
    store = MemoryWorkflowStore()
    store.run.request_payload["case_id"] = "other_case"
    output = StageRunner(store, lambda _: pytest.fail("Must not fetch")).execute("run", WorkflowStage.IDENTITY)
    assert not output["confirmed"]
    assert output["input_failure"]["error_category"] == "InvalidCaseRequest"
    assert store.run.status == "needs_more_information"


def test_terminal_write_retry_reconciles_cached_output():
    store = MemoryWorkflowStore()
    store.run.request_payload["party"]["legal_name"] = "Other Company"
    original = store.finish
    store.finish = lambda *args: (_ for _ in ()).throw(RuntimeError("Unknown write outcome"))
    runner = StageRunner(store, identity)
    with pytest.raises(RuntimeError):
        runner.execute("run", WorkflowStage.IDENTITY)
    store.finish = original
    runner.execute("run", WorkflowStage.IDENTITY)
    assert store.latest("run", WorkflowStage.IDENTITY).attempt == 1
    assert store.run.status == "needs_more_information"
