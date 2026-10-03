"""Portable stage execution; Snowflake owns the production DAG and retries."""

from collections.abc import Callable
from typing import Protocol

from trust_signal.aggregation import AggregationService, EvidenceAggregator
from trust_signal.domain.aggregation import AggregationResult
from trust_signal.domain.identity import IdentityResolution
from trust_signal.domain.workflow import (
    SPECIALIST_STAGES,
    StageAttempt,
    WorkflowInputFailure,
    WorkflowRun,
    WorkflowStage,
)
from trust_signal.models import (
    Assessment,
    BranchResult,
    BranchStatus,
    CaseRequest,
    CaseResult,
    CaseStatus,
    Disposition,
    SourceMode,
)


class WorkflowStore(Protocol):
    def load(self, run_id: str) -> WorkflowRun: ...
    def latest(self, run_id: str, stage: WorkflowStage) -> StageAttempt | None: ...
    def start(self, run_id: str, stage: WorkflowStage) -> StageAttempt: ...
    def complete(self, attempt: StageAttempt, output: dict, status: str) -> None: ...
    def fail(self, attempt: StageAttempt, error_category: str) -> None: ...
    def finish(self, run_id: str, result: CaseResult | WorkflowInputFailure) -> None: ...


IdentityHandler = Callable[[CaseRequest], BranchResult]
SpecialistHandler = Callable[[CaseRequest, IdentityResolution], BranchResult]
CACHED_STATUSES = {"succeeded", "completed_with_gaps", "skipped"}


class ResearchUnavailableError(RuntimeError):
    """A specialist could not collect evidence; record an expected coverage gap."""


class StageRunner:
    def __init__(self, store: WorkflowStore, identity: IdentityHandler,
                 specialists: dict[WorkflowStage, SpecialistHandler] | None = None,
                 aggregator: AggregationService | None = None):
        self.store = store
        self.identity = identity
        self.specialists = specialists or {}
        self.aggregator = aggregator or EvidenceAggregator()

    def execute(self, run_id: str, stage: WorkflowStage) -> dict:
        run = self.store.load(run_id)
        previous = self.store.latest(run_id, stage)
        if previous and previous.status in CACHED_STATUSES:
            if previous.output is None:
                raise ValueError("Completed stage has no durable output.")
            output = previous.output
        else:
            attempt = self.store.start(run_id, stage)
            try:
                output = self._compute(run, stage)
                branch_status = output.get("branch", {}).get("status")
                status = ("skipped" if branch_status == "skipped" else
                          "completed_with_gaps" if branch_status == "failed" else "succeeded")
                self.store.complete(attempt, output, status)
            except Exception as exc:  # noqa: BLE001 - persist categories without provider secrets
                self.store.fail(attempt, type(exc).__name__)
                raise RuntimeError(f"Workflow stage {stage.value} failed; reconcile its attempt.") from None
        # Reconcile a prior finish whose write/readback outcome was unknown.
        if output.get("case_result"):
            self.store.finish(run_id, CaseResult.model_validate(output["case_result"]))
        elif output.get("input_failure"):
            self.store.finish(run_id, WorkflowInputFailure.model_validate(output["input_failure"]))
        return output

    def _request(self, run: WorkflowRun) -> CaseRequest:
        payload = dict(run.request_payload)
        if payload.get("case_id") not in (None, run.case_id):
            raise ValueError("Request payload belongs to a different case.")
        payload["case_id"] = run.case_id
        # V002's Snowflake intake already emits this source-mode name.
        if payload.get("source_mode") == "configured_sources":
            payload["source_mode"] = SourceMode.GLEIF_LIVE.value
        request = CaseRequest.model_validate(payload)
        if request.source_mode != SourceMode.GLEIF_LIVE:
            raise ValueError("Production task graph requires live sources.")
        return request

    def _output(self, run_id: str, stage: WorkflowStage) -> dict:
        attempt = self.store.latest(run_id, stage)
        if not attempt or attempt.status not in CACHED_STATUSES or attempt.output is None:
            raise ValueError(f"Required stage {stage.value} has not completed.")
        return attempt.output

    def _branches(self, run_id: str) -> list[BranchResult]:
        return [BranchResult.model_validate(self._output(run_id, stage)["branch"])
                for stage in (WorkflowStage.IDENTITY, *SPECIALIST_STAGES)]

    def _identity_result(self, run: WorkflowRun, request: CaseRequest,
                         branch: BranchResult) -> dict:
        resolution = branch.identity_resolution
        confirmed = bool(branch.status == BranchStatus.COMPLETED and resolution
                         and resolution.status == "resolved" and
                         any(m.candidate.candidate_id == resolution.selected_candidate_id
                             and m.eligible_for_attribution and m.candidate.observation_ids
                             and any(f.source_id == m.candidate.source_id
                                     and f.source_record_id == m.candidate.source_record_id
                                     and set(f.observation_ids) & set(m.candidate.observation_ids)
                                     for f in branch.findings)
                             for m in resolution.matches))
        output = {"branch": branch.model_dump(mode="json"), "confirmed": confirmed}
        if confirmed:
            return output
        failed = branch.status == BranchStatus.FAILED
        result = CaseResult(
            case_id=run.case_id, party=request.party,
            status=CaseStatus.COMPLETED_WITH_GAPS if failed else CaseStatus.NEEDS_MORE_INFORMATION,
            identity_status="identity_lookup_failed" if failed else "identity_confirmation_required",
            identity_resolution=resolution, branches=[branch],
            assessment=Assessment(
                score_status="not_scored_identity_lookup_failed" if failed else "not_scored_identity_unresolved",
                reasons=["Identity must be confirmed before specialist research.", *branch.limitations],
                disposition=Disposition.ANALYST_REVIEW if failed else Disposition.REQUEST_DETAILS,
            ),
        )
        output["case_result"] = result.model_dump(mode="json")
        return output

    def _compute(self, run: WorkflowRun, stage: WorkflowStage) -> dict:
        try:
            request = self._request(run)
        except ValueError:
            if stage != WorkflowStage.IDENTITY:
                raise
            return {"confirmed": False,
                    "input_failure": WorkflowInputFailure(case_id=run.case_id).model_dump(mode="json")}
        if stage == WorkflowStage.IDENTITY:
            branch = self.identity(request)
            branch.branch_id = "registry"
            if any(f.evidence_mode.value != "live_source" for f in branch.findings):
                raise ValueError("Live identity handler returned fixture evidence.")
            return self._identity_result(run, request, branch)

        identity_output = self._output(run.run_id, WorkflowStage.IDENTITY)
        if not identity_output["confirmed"]:
            raise ValueError("Identity is unresolved; downstream stages cannot run.")
        identity_branch = BranchResult.model_validate(identity_output["branch"])
        resolution = identity_branch.identity_resolution
        if resolution is None:
            raise ValueError("Confirmed identity has no decision.")
        if stage in SPECIALIST_STAGES:
            handler = self.specialists.get(stage)
            if handler is None:
                branch = BranchResult(branch_id=stage.value, status=BranchStatus.SKIPPED,
                                      limitations=[f"{stage.value} specialist is not implemented."])
            else:
                try:
                    branch = handler(request, resolution)
                except ResearchUnavailableError as exc:
                    branch = BranchResult(branch_id=stage.value, status=BranchStatus.FAILED,
                                          error=type(exc).__name__,
                                          limitations=["Specialist research failed; coverage is incomplete."])
                if any(f.evidence_mode.value != "live_source" for f in branch.findings):
                    raise ValueError("Live specialist returned fixture evidence.")
            branch.branch_id = stage.value
            return {"branch": branch.model_dump(mode="json")}
        if stage == WorkflowStage.AGGREGATE:
            result = self.aggregator.aggregate(self._branches(run.run_id), resolution)
            return {"aggregation": result.model_dump(mode="json")}
        if stage == WorkflowStage.VALIDATE:
            self._output(run.run_id, WorkflowStage.AGGREGATE)
            return {"status": "not_validated", "eligible_finding_ids": [],
                    "limitations": ["Claim/event validation is not configured; findings cannot be scored."]}
        if stage == WorkflowStage.ASSESS:
            aggregation = AggregationResult.model_validate(
                self._output(run.run_id, WorkflowStage.AGGREGATE)["aggregation"])
            validation = self._output(run.run_id, WorkflowStage.VALIDATE)
            branches = self._branches(run.run_id)
            limitations = [limitation for b in branches for limitation in b.limitations]
            result = CaseResult(
                case_id=run.case_id, party=request.party, status=CaseStatus.COMPLETED_WITH_GAPS,
                identity_status="resolved", identity_resolution=resolution, branches=branches,
                aggregation=aggregation, comparison_board=aggregation.comparison_board,
                assessment=Assessment(score_status="not_scored_policy_not_configured",
                                      reasons=["A validated scoring policy is not configured.",
                                               *validation["limitations"], *limitations],
                                      disposition=Disposition.ANALYST_REVIEW),
            )
            return {"case_result": result.model_dump(mode="json")}
        raise ValueError("Unknown workflow stage.")
