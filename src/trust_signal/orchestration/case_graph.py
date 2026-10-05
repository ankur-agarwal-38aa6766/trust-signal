"""Explicit identity gate, parallel specialist fan-out, comparison, and routing."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from trust_signal.agents.fixtures import Branch
from trust_signal.agents.registry import branches_for_mode
from trust_signal.aggregation import AggregationService, EvidenceAggregator
from trust_signal.domain.aggregation import AggregationResult
from trust_signal.domain.identity import IdentityCandidate, IdentityResolution, ResolutionStatus
from trust_signal.domain.validation import ValidationResult
from trust_signal.models import (
    Assessment,
    BranchResult,
    BranchStatus,
    CaseRequest,
    CaseResult,
    CaseStatus,
    ComparisonItem,
    Disposition,
    SourceMode,
)
from trust_signal.research.validation import EvidenceValidator
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import EntityResolver


class WorkflowState(TypedDict, total=False):
    request: CaseRequest
    identity_status: str
    identity_reasons: list[str]
    identity_resolution: IdentityResolution
    branches: Annotated[list[BranchResult], add]
    comparison_board: list[ComparisonItem]
    aggregation: AggregationResult
    validation: ValidationResult
    assessment: Assessment
    status: CaseStatus


def identity_gate(state: WorkflowState) -> dict:
    party = state["request"].party
    has_identifier = bool(party.registration_id or party.lei)
    has_jurisdiction = bool(party.jurisdiction)
    gleif_lookup = state["request"].source_mode == SourceMode.GLEIF_LIVE
    if gleif_lookup or (has_identifier and has_jurisdiction):
        return {"identity_status": "input_sufficient_for_lookup", "identity_reasons": []}
    missing = []
    if not has_jurisdiction:
        missing.append("jurisdiction")
    if not has_identifier:
        missing.append("registration_id_or_lei")
    return {"identity_status": "needs_more_information", "identity_reasons": missing}


Specialist = Callable[[CaseRequest, IdentityResolution], BranchResult]


def _branch_node(branch_id: str, branch, *, requires_identity: bool = False):
    def run(state: WorkflowState) -> dict:
        started_at = datetime.now(UTC)
        try:
            result = (branch(state["request"], state["identity_resolution"])
                      if requires_identity else branch(state["request"]))
            result.branch_id = branch_id
        except Exception as exc:  # noqa: BLE001 - isolate failures at the specialist boundary
            result = BranchResult(
                branch_id=branch_id,
                status=BranchStatus.FAILED,
                error=f"{type(exc).__name__}: specialist branch failed",
                limitations=["This branch did not return research results."],
            )
        result.started_at = started_at
        result.completed_at = datetime.now(UTC)
        return {"branches": [result]}

    run.__name__ = f"run_{branch_id}"
    return run


def compare_branches(state: WorkflowState, aggregator: AggregationService | None = None) -> dict:
    result = (aggregator or EvidenceAggregator()).aggregate(
        state.get("branches", []), state.get("identity_resolution"))
    return {"comparison_board": result.comparison_board, "aggregation": result}


def assess_case(state: WorkflowState) -> dict:
    if state["identity_status"] not in (
        "input_sufficient_for_lookup", "resolved_by_exact_lei_and_name"
    ):
        assessment = Assessment(
            risk_score=None,
            score_status="not_scored_identity_incomplete",
            reasons=state.get("identity_reasons", []),
            disposition=Disposition.REQUEST_DETAILS,
        )
        return {"assessment": assessment, "status": CaseStatus.NEEDS_MORE_INFORMATION}

    branch_results = state.get("branches", [])
    limitations = [limitation for branch in branch_results for limitation in branch.limitations]
    failed = [branch.branch_id for branch in branch_results if branch.status == BranchStatus.FAILED]
    identity_status = state["identity_status"]
    identity_resolution = state.get("identity_resolution")
    if state["request"].source_mode == SourceMode.GLEIF_LIVE:
        registry_result = next((branch for branch in branch_results if branch.branch_id == "registry"), None)
        if registry_result is None or registry_result.status == BranchStatus.FAILED:
            identity_status = "identity_lookup_failed"
            assessment = Assessment(
                risk_score=None,
                score_status="not_scored_identity_lookup_failed",
                reasons=["GLEIF could not complete the identity lookup; no entity was confirmed.", *limitations],
                disposition=Disposition.ANALYST_REVIEW,
            )
            return {
                "identity_status": identity_status,
                "assessment": assessment,
                "status": CaseStatus.COMPLETED_WITH_GAPS,
            }

        if not state["request"].party.lei:
            return {"identity_status": "candidates_require_confirmation",
                    "identity_resolution": registry_result.identity_resolution,
                    "assessment": Assessment(risk_score=None, score_status="not_scored_candidate_discovery",
                                             reasons=["Confirm the legal party using a returned LEI.", *limitations],
                                             disposition=Disposition.REQUEST_DETAILS),
                    "status": CaseStatus.NEEDS_MORE_INFORMATION}

        finding = next(
            (item for item in registry_result.findings if item.claim_type == "legal_identity_record"),
            None,
        ) if registry_result else None
        if finding is None:
            identity_status = "lei_record_not_found"
            assessment = Assessment(
                risk_score=None,
                score_status="not_scored_identity_not_found",
                reasons=["GLEIF returned no record for this LEI. Check the identifier and try again."],
                disposition=Disposition.REQUEST_DETAILS,
            )
            return {
                "identity_status": identity_status,
                "assessment": assessment,
                "status": CaseStatus.NEEDS_MORE_INFORMATION,
            }

        resolution = registry_result.identity_resolution
        if resolution is None:
            # Compatibility for injected branches using the original Finding contract.
            resolution = EntityResolver().resolve(state["request"].party, [IdentityCandidate(
                candidate_id=stable_id("candidate", finding.source_id,
                                       finding.source_record_id or finding.finding_id),
                source_id=finding.source_id,
                source_record_id=finding.source_record_id or finding.finding_id,
                legal_name=finding.subject,
                lei=finding.source_record_id if finding.source_id == "gleif_lei_api" else None,
            )])
        if resolution.status != ResolutionStatus.RESOLVED:
            identity_status = "identity_name_conflict"
            assessment = Assessment(
                risk_score=None,
                score_status="not_scored_identity_name_conflict",
                reasons=[(
                    f"Submitted party conflicts with or cannot confirm GLEIF legal name {finding.subject!r}; "
                    "confirm the LEI belongs to this party or correct the submitted name."
                ), *resolution.reason_codes,
                    *[reason for match in resolution.matches for reason in match.reason_codes]],
                disposition=Disposition.REQUEST_DETAILS,
            )
            return {
                "identity_status": identity_status,
                "identity_resolution": resolution,
                "assessment": assessment,
                "status": CaseStatus.NEEDS_MORE_INFORMATION,
            }
        identity_status = "resolved_by_exact_lei_and_name"
        identity_resolution = resolution

    assessment = Assessment(
        risk_score=None,
        score_status="not_scored_policy_not_configured",
        reasons=["A validated scoring policy is not configured.", *[f"Branch failed: {name}." for name in failed],
                 *limitations, *(state["validation"].limitations if state.get("validation") else [])],
        disposition=Disposition.ANALYST_REVIEW,
    )
    status = CaseStatus.COMPLETED_WITH_GAPS if limitations or failed else CaseStatus.COMPLETED
    if state.get("validation") and state["validation"].status == "completed_with_gaps":
        status = CaseStatus.COMPLETED_WITH_GAPS
    result = {"identity_status": identity_status, "assessment": assessment, "status": status}
    if identity_resolution is not None:
        result["identity_resolution"] = identity_resolution
    return result


def _dispatch(branch_ids: list[str]):
    def dispatch(state: WorkflowState):
        if state["identity_status"] != "input_sufficient_for_lookup":
            return "assess_incomplete"
        return [Send(branch_id, {"request": state["request"]}) for branch_id in branch_ids]

    return dispatch


def build_case_graph(branches: dict[str, Branch] | None = None,
                     source_mode: SourceMode = SourceMode.DEMO_FIXTURES, *,
                     aggregator: AggregationService | None = None,
                     specialists: dict[str, Specialist] | None = None):
    branch_map = dict(branches if branches is not None else branches_for_mode(SourceMode.DEMO_FIXTURES))
    injected = specialists or {}
    if injected and (source_mode != SourceMode.GLEIF_LIVE or set(injected) & set(branch_map)):
        raise ValueError("Injected specialists require live identity and distinct branch names.")
    branch_map.update(injected)
    if not branch_map:
        raise ValueError("At least one specialist branch is required.")
    live_identity = source_mode == SourceMode.GLEIF_LIVE
    if live_identity and "registry" not in branch_map:
        raise ValueError("Live identity resolution requires a registry branch.")
    graph = StateGraph(WorkflowState)
    graph.add_node("identity_gate", identity_gate)
    graph.add_node("assess_incomplete", assess_case)
    graph.add_node("compare", lambda state: compare_branches(state, aggregator))
    graph.add_node("validate", lambda state: {"validation": EvidenceValidator().validate(
        state["request"], state.get("branches", []), state["aggregation"], state.get("identity_resolution"))})
    graph.add_node("assess", assess_case)
    for branch_id, branch in branch_map.items():
        graph.add_node(branch_id, _branch_node(branch_id, branch, requires_identity=branch_id in injected))

    graph.add_edge(START, "identity_gate")
    graph.add_conditional_edges(
        "identity_gate",
        _dispatch(["registry"] if live_identity else list(branch_map)),
        ["assess_incomplete", "registry"] if live_identity else ["assess_incomplete", *branch_map],
    )
    graph.add_edge("assess_incomplete", END)
    if live_identity:
        graph.add_node("resolve_identity", assess_case)
        graph.add_edge("registry", "resolve_identity")
        specialist_ids = [name for name in branch_map if name != "registry"]

        def dispatch_resolved(state: WorkflowState):
            if state["identity_status"] != "resolved_by_exact_lei_and_name":
                return END
            if not specialist_ids:
                return "compare"
            return [Send(name, {"request": state["request"],
                                "identity_resolution": state["identity_resolution"]})
                    for name in specialist_ids]

        graph.add_conditional_edges("resolve_identity", dispatch_resolved,
                                    [END, "compare", *specialist_ids])
        if specialist_ids:
            graph.add_edge(specialist_ids, "compare")
    else:
        graph.add_edge(list(branch_map), "compare")
    graph.add_edge("compare", "validate")
    graph.add_edge("validate", "assess")
    graph.add_edge("assess", END)
    return graph.compile()


def run_case(request: CaseRequest, branches: dict[str, Branch] | None = None, *,
             ingestion_pipeline=None, aggregator: AggregationService | None = None,
             specialists: dict[str, Specialist] | None = None) -> CaseResult:
    branch_map = branches if branches is not None else branches_for_mode(request.source_mode, ingestion_pipeline)
    state = build_case_graph(branch_map, request.source_mode, aggregator=aggregator,
                             specialists=specialists).invoke({"request": request})
    return CaseResult(
        case_id=request.case_id,
        party=request.party,
        status=state["status"],
        identity_status=state["identity_status"],
        identity_resolution=state.get("identity_resolution"),
        branches=state.get("branches", []),
        comparison_board=state.get("comparison_board", []),
        aggregation=state.get("aggregation"),
        validation=state.get("validation"),
        assessment=state["assessment"],
    )
