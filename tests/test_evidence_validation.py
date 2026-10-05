from datetime import timedelta

import pytest
from test_legal_specialist import NOW, identity_pair

from trust_signal.aggregation import EvidenceAggregator
from trust_signal.models import BranchResult, Finding
from trust_signal.research.validation import EvidenceValidator


def inputs():
    request, identity = identity_pair()
    finding = Finding(finding_id="finding", branch_id="legal", claim_type="legal_event_candidate",
                      claim="Source-reported metadata", subject=request.party.legal_name, subject_id="subject",
                      source_id="official", source_name="Official", source_record_id="record", source_run_id="run",
                      source_url="https://example.test/notice", connector_version="test-1",
                      content_hash="sha256:" + "a" * 64, observation_ids=["raw"], observed_at=NOW,
                      evidence_mode="live_source")
    branches = [BranchResult(branch_id="legal", status="completed", findings=[finding])]
    return request, identity, branches, EvidenceAggregator().aggregate(branches, identity)


def validate(values):
    request, identity, branches, aggregation = values
    return EvidenceValidator().validate(request, branches, aggregation, identity, now=NOW)


def test_structural_pass_does_not_validate_claim_or_enable_scoring():
    result = validate(inputs())
    assert result.findings[0].structural_checks_passed
    assert result.findings[0].status == "review_required"
    assert result.eligible_finding_ids == []


@pytest.mark.parametrize("field,value,reason", [
    ("observation_ids", [], "missing_observation_lineage"),
    ("observation_ids", ["raw", "raw"], "duplicate_observation_lineage"),
    ("source_run_id", None, "missing_source_lineage"),
    ("content_hash", "incorrect", "invalid_content_hash"),
    ("source_url", "javascript:alert(1)", "invalid_source_url"),
    ("source_url", "https://user:password@example.test", "invalid_source_url"),
    ("observed_at", None, "missing_aware_observation_time"),
    ("observed_at", NOW + timedelta(minutes=6), "future_observation_time"),
    ("subject", "Other Company", "subject_label_conflict"),
    ("branch_id", "news", "invalid_branch_lineage"),
])
def test_invalid_evidence_is_rejected(field, value, reason):
    values = inputs()
    setattr(values[2][0].findings[0], field, value)
    result = validate(values)
    assert result.status == "completed_with_gaps"
    assert result.findings[0].status == "rejected"
    assert reason in result.findings[0].reason_codes
    assert result.eligible_finding_ids == []


def test_pending_attribution_and_conflicts_require_review():
    values = inputs()
    values[2][0].findings[0].subject_id = None
    values[3].groups[0].relation = "potential_conflict"
    result = validate(values)
    assert "finding_attribution_unconfirmed" in result.findings[0].reason_codes
    assert "unresolved_claim_conflict" in result.findings[0].reason_codes


def test_missing_or_unknown_aggregation_references_are_rejected():
    values = inputs()
    values[3].groups[0].finding_ids = ["unknown"]
    result = validate(values)
    assert result.findings[0].status == "rejected"
    assert "invalid_aggregation_membership" in result.findings[0].reason_codes


def test_forged_identity_does_not_confirm_attribution():
    values = inputs()
    values[1].matches[0].eligible_for_attribution = False
    assert "identity_unconfirmed" in validate(values).findings[0].reason_codes


def test_stage_runner_persists_validation_and_reuses_on_retry():
    from test_workflow_stages import MemoryWorkflowStore, identity

    from trust_signal.domain.workflow import SPECIALIST_STAGES, WorkflowStage
    from trust_signal.orchestration.stages import StageRunner

    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity)
    runner.execute("run", WorkflowStage.IDENTITY)
    for stage in SPECIALIST_STAGES:
        runner.execute("run", stage)
    runner.execute("run", WorkflowStage.AGGREGATE)
    output = runner.execute("run", WorkflowStage.VALIDATE)
    assert output == runner.execute("run", WorkflowStage.VALIDATE)
    assert store.latest("run", WorkflowStage.VALIDATE).attempt == 1
    runner.execute("run", WorkflowStage.ASSESS)
    assert store.results[-1].validation is not None
    assert store.results[-1].assessment.risk_score is None


def test_local_graph_includes_validation_result():
    from test_workflow_stages import identity

    from trust_signal.orchestration.case_graph import run_case

    request, _ = identity_pair()
    result = run_case(request, branches={"registry": identity})
    assert result.validation is not None
    assert result.validation.eligible_finding_ids == []


def test_old_validation_stub_is_recomputed_not_reused():
    from test_workflow_stages import MemoryWorkflowStore, identity

    from trust_signal.domain.workflow import SPECIALIST_STAGES, WorkflowStage
    from trust_signal.orchestration.stages import StageRunner

    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity)
    runner.execute("run", WorkflowStage.IDENTITY)
    for stage in SPECIALIST_STAGES:
        runner.execute("run", stage)
    runner.execute("run", WorkflowStage.AGGREGATE)
    runner.execute("run", WorkflowStage.VALIDATE)
    store.attempts[WorkflowStage.VALIDATE].output = {"status": "not_validated", "eligible_finding_ids": []}
    output = runner.execute("run", WorkflowStage.VALIDATE)
    assert output["policy_version"] == "validation-0.1"
    assert store.latest("run", WorkflowStage.VALIDATE).attempt == 2
