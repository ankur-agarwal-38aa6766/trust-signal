from copy import deepcopy
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from trust_signal.agents.ownership import GLEIF, NORWAY, OwnershipSpecialist
from trust_signal.connectors.registry import SourceRequest
from trust_signal.domain.identity import IdentityCandidate
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.domain.sanctions import ScreeningEvidence
from trust_signal.ingestion.pipeline import IngestionResult
from trust_signal.models import CaseRequest
from trust_signal.persistence.contracts import ObservationReceipt
from trust_signal.research.provider import PipelineResearchProvider, ResearchDataset
from trust_signal.resolution import EntityResolver

NOW = datetime(2026, 10, 4, tzinfo=UTC)
LEI = "INR2EJN1ERAN0W5ZP974"
PARENT = "549300B56MD0ZC402L06"
NUMBER = "923609016"
HASH = "sha256:" + "a" * 64


def identity_pair(*, norway=False):
    values = ({"legal_name": "Example Norway AS", "registration_id": NUMBER,
               "registration_authority": NORWAY, "jurisdiction": "NO"} if norway else
              {"legal_name": "Microsoft Corporation", "lei": LEI})
    request = CaseRequest(party=values, source_mode="gleif_live")
    candidate = IdentityCandidate(candidate_id="subject", source_id=NORWAY if norway else GLEIF,
                                  source_record_id=NUMBER if norway else LEI,
                                  **values, observation_ids=["identity_raw"])
    return request, EntityResolver().resolve(request.party, [candidate])


def evidence(key, url):
    return ScreeningEvidence(observation_id=key, canonical_url=url, content_hash=HASH,
                             connector_version="test-1", observed_at=NOW)


def gleif_dataset(*, direction="direct-parent", exception=False, status="ACTIVE"):
    endpoint = f"https://api.gleif.org/api/v1/lei-records/{LEI}/{direction}-reporting-exception"
    attributes = ({"lei": LEI, "reason": "NON_CONSOLIDATING",
                   "category": "DIRECT_ACCOUNTING_CONSOLIDATION_PARENT"} if exception else
                  {"relationship": {"startNode": {"id": PARENT if direction == "direct-children" else LEI},
                                    "endNode": {"id": LEI if direction == "direct-children" else PARENT},
                                    "type": "IS_ULTIMATELY_CONSOLIDATED_BY" if direction == "ultimate-parent"
                                    else "IS_DIRECTLY_CONSOLIDATED_BY", "status": status},
                   "registration": {"status": "PUBLISHED", "corroborationLevel": "ENTITY_SUPPLIED_ONLY"}})
    return ResearchDataset(ResearchCoverage(source_id=GLEIF, operation="relationships", coverage="available",
                                            source_run_id="gleif_run"), records=[
        {"source_id": GLEIF, "source_record_id": LEI, "lei": LEI,
         "legal_name": "Microsoft Corporation", "observation_ids": ["gleif_identity"]},
        {"source_record_id": "relationship_1", "direction": direction, "attributes": attributes,
         "record_type": "reporting-exceptions" if exception else "relationship-records",
         "observation_ids": ["gleif_rel"]}], evidence={
        "gleif_identity": evidence("gleif_identity", f"https://api.gleif.org/api/v1/lei-records/{LEI}"),
        "gleif_rel": evidence("gleif_rel", endpoint if exception else "https://api.gleif.org/api/v1/relationship-records/rel")})


def norway_datasets(*, name="Example Norway AS", deregistered=False):
    lookup = ResearchDataset(ResearchCoverage(source_id=NORWAY, operation="lookup", coverage="available",
                                              source_run_id="norway_lookup"), records=[{
        "source_id": NORWAY, "source_record_id": NUMBER, "registration_id": NUMBER, "jurisdiction": "NO",
        "legal_name": name, "observation_ids": ["norway_identity"]}], evidence={
        "norway_identity": evidence("norway_identity", f"https://data.brreg.no/enhetsregisteret/oppslag/enheter/{NUMBER}")})
    roles = ResearchDataset(ResearchCoverage(source_id=NORWAY, operation="roles", coverage="available",
                                             source_run_id="norway_roles"), records=[{
        "source_id": NORWAY, "source_record_id": f"{NUMBER}:roles:0:0", "organization_number": NUMBER,
        "display_name": "Example Director", "holder_type": "person", "role_code": "LEDE",
        "role_name": "Board chair", "group_code": "STYR", "is_board_role": True,
        "deregistered": deregistered, "observation_ids": ["norway_role"]}], evidence={
        "norway_role": evidence("norway_role", f"https://data.brreg.no/enhetsregisteret/api/enheter/{NUMBER}/roller")})
    return lookup, roles


def specialist(provider, **kwargs):
    return OwnershipSpecialist(provider, clock=lambda: NOW, **kwargs)


@pytest.mark.parametrize("direction", ["direct-parent", "ultimate-parent", "direct-children"])
def test_relationship_direction_and_accounting_semantics_are_preserved(direction):
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.return_value = gleif_dataset(direction=direction)
    branch = specialist(provider)(request, resolution)
    record = branch.ownership_research.records[0]
    assert record.kind == "consolidation_relationship"
    assert record.details["direction"] == direction
    assert record.attribution == "confirmed"
    assert branch.findings[0].subject_id == "subject"
    assert branch.findings[0].risk_weight == 0
    assert branch.findings[0].event_at is None
    assert any("not beneficial ownership" in item for item in branch.limitations)


def test_live_schema_reporting_exception_is_not_absent_parent_or_fraud():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.return_value = gleif_dataset(exception=True)
    branch = specialist(provider)(request, resolution)
    record = branch.ownership_research.records[0]
    assert record.kind == "reporting_exception"
    assert record.details["exception_reasons"] == ["NON_CONSOLIDATING"]
    assert any("do not prove absence" in item for item in branch.limitations)


@pytest.mark.parametrize("corruption", ["subject", "type", "endpoint", "category", "duplicate", "identity", "schema"])
def test_malformed_or_misattributed_gleif_records_withhold_entire_dataset(corruption):
    request, resolution = identity_pair()
    data = gleif_dataset(exception=corruption in {"endpoint", "category"})
    if corruption == "subject":
        data.records[1]["attributes"]["relationship"]["startNode"]["id"] = PARENT
    elif corruption == "type":
        data.records[1]["attributes"]["relationship"]["type"] = "IS_FUND_MANAGED_BY"
    elif corruption == "endpoint":
        data.evidence["gleif_rel"].canonical_url = f"https://api.gleif.org/api/v1/lei-records/{PARENT}/direct-parent-reporting-exception"
    elif corruption == "category":
        data.records[1]["attributes"]["category"] = "ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT"
    elif corruption == "duplicate":
        data.records.append(deepcopy(data.records[1]))
    elif corruption == "identity":
        data.records[0]["lei"] = PARENT
    else:
        del data.records[1]["attributes"]["relationship"]["status"]
    provider = Mock()
    provider.load.return_value = data
    result = specialist(provider)(request, resolution)
    assert result.status == "failed"
    assert result.findings == []
    assert result.ownership_research.coverage[0].error_category == "InvalidResearchRecord"


@pytest.mark.parametrize("status", ["INACTIVE", "NULL", "ACTIVE"])
def test_relationship_status_is_not_changed_to_current_ownership(status):
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.return_value = gleif_dataset(status=status)
    result = specialist(provider)(request, resolution)
    assert result.ownership_research.records[0].details["relationship"]["status"] == status


@pytest.mark.parametrize("deregistered", [False, True])
def test_scoped_norway_roles_preserve_role_flags_and_both_evidence_links(deregistered):
    request, resolution = identity_pair(norway=True)
    provider = Mock()
    provider.load.side_effect = norway_datasets(deregistered=deregistered)
    result = specialist(provider)(request, resolution)
    role = result.ownership_research.records[0]
    assert role.attribution == "confirmed"
    assert role.details["is_board_role"]
    assert role.details["deregistered"] == deregistered
    assert result.findings[0].observation_ids == ["norway_role", "norway_identity"]
    assert provider.load.call_args_list[0].args[0].operation == "lookup"
    assert provider.load.call_args_list[1].args[0].operation == "roles"


def test_norway_number_hint_and_exact_name_only_stay_pending():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.side_effect = [gleif_dataset(), *norway_datasets(name="Microsoft Corporation")]
    branch = specialist(provider, norway_organization_number=NUMBER)(request, resolution)
    role = branch.ownership_research.records[-1]
    assert role.attribution == "pending"
    assert branch.findings[-1].subject_id is None
    assert any("analyst confirmation" in item for item in branch.limitations)


def test_wrong_norway_name_does_not_fetch_roles():
    request, resolution = identity_pair(norway=True)
    provider = Mock()
    provider.load.return_value = norway_datasets(name="Unrelated Company")[0]
    result = specialist(provider)(request, resolution)
    provider.load.assert_called_once()
    assert result.findings == []
    assert result.status == "failed"


def test_foreign_confirmed_jurisdiction_blocks_name_only_norway_linkage():
    request, resolution = identity_pair()
    request.party.jurisdiction = "US"
    resolution.matches[0].candidate.jurisdiction = "US"
    provider = Mock()
    provider.load.side_effect = [gleif_dataset(), norway_datasets(name=request.party.legal_name)[0]]
    result = specialist(provider, norway_organization_number=NUMBER)(request, resolution)
    assert len(result.findings) == 1
    assert provider.load.call_count == 2
    assert result.ownership_research.coverage[-1].coverage == "failed"


@pytest.mark.parametrize("corruption", ["organization", "endpoint", "duplicate", "lineage"])
def test_wrong_or_malformed_roles_are_withheld(corruption):
    request, resolution = identity_pair(norway=True)
    lookup, roles = norway_datasets()
    if corruption == "organization":
        roles.records[0]["organization_number"] = "111111111"
    elif corruption == "endpoint":
        roles.evidence["norway_role"].canonical_url = "https://data.brreg.no/enhetsregisteret/api/enheter/111111111/roller"
    elif corruption == "duplicate":
        roles.records.append(deepcopy(roles.records[0]))
    else:
        roles.records[0]["observation_ids"] = []
    provider = Mock()
    provider.load.side_effect = [lookup, roles]
    result = specialist(provider)(request, resolution)
    assert result.findings == []
    assert result.ownership_research.coverage[-1].coverage == "failed"


def test_source_failure_retains_other_source_research_and_is_sanitized():
    request, resolution = identity_pair()
    provider = Mock()
    provider.load.side_effect = [RuntimeError("secret"), *norway_datasets(name=request.party.legal_name)]
    branch = specialist(provider, norway_organization_number=NUMBER)(request, resolution)
    assert branch.status == "completed"
    assert len(branch.findings) == 1
    assert "secret" not in branch.model_dump_json()


@pytest.mark.parametrize("age", [timedelta(days=2), -timedelta(minutes=6)])
def test_stale_or_future_dataset_is_not_used(age):
    request, resolution = identity_pair()
    data = gleif_dataset()
    data.evidence["gleif_rel"].observed_at = NOW - age
    provider = Mock()
    provider.load.return_value = data
    result = specialist(provider)(request, resolution)
    assert result.ownership_research.coverage[0].coverage == "stale"
    assert result.findings == []


def test_unresolved_identity_never_fetches():
    request, resolution = identity_pair()
    resolution.matches[0].eligible_for_attribution = False
    provider = Mock()
    with pytest.raises(ValueError, match="confirmed identity"):
        specialist(provider)(request, resolution)
    provider.load.assert_not_called()


def test_partial_relationships_remain_visible_with_coverage_gap():
    request, resolution = identity_pair()
    data = gleif_dataset()
    data.coverage.coverage = "partial"
    provider = Mock()
    provider.load.return_value = data
    result = specialist(provider)(request, resolution)
    assert len(result.findings) == 1
    assert any("coverage partial" in item for item in result.limitations)


def test_research_provider_checks_receipts_and_accepts_verified_empty_roles():
    request = SourceRequest(source_id=NORWAY, operation="roles", value=NUMBER)
    proof = norway_datasets()[1].evidence["norway_role"]
    result = IngestionResult(run_id="run", source_id=NORWAY, coverage="no_matches", records=[],
                             receipts=[ObservationReceipt("norway_role", NORWAY, "roles", HASH, 1, 1)],
                             evidence=[{**proof.model_dump(mode="json"), "source_id": NORWAY,
                                        "source_record_id": "roles"}])
    pipeline = Mock()
    pipeline.ingest.return_value = result
    output = PipelineResearchProvider(pipeline).load(request)
    assert output.coverage.coverage == "no_matches"
    assert output.evidence
    result.receipts = []
    assert PipelineResearchProvider(pipeline).load(request).coverage.coverage == "failed"


def test_research_provider_rejects_hash_corruption_and_terminal_log_failure():
    request = SourceRequest(source_id=NORWAY, operation="roles", value=NUMBER)
    proof = norway_datasets()[1].evidence["norway_role"]
    pipeline = Mock()
    pipeline.ingest.return_value = IngestionResult(
        run_id="run", source_id=NORWAY, coverage="available", records=norway_datasets()[1].records,
        receipts=[ObservationReceipt("norway_role", NORWAY, "roles", "sha256:" + "b" * 64, 1, 1)],
        evidence=[{**proof.model_dump(mode="json"), "source_id": NORWAY, "source_record_id": "roles"}])
    assert PipelineResearchProvider(pipeline).load(request).coverage.coverage == "failed"
    pipeline.ingest.side_effect = RuntimeError("private SQL")
    output = PipelineResearchProvider(pipeline).load(request)
    assert output.coverage.coverage == "failed"
    assert "private SQL" not in str(output)


def test_local_graph_and_stage_runner_accept_ownership_and_retry_without_fetching():
    from test_workflow_stages import MemoryWorkflowStore, identity

    from trust_signal.domain.workflow import SPECIALIST_STAGES, WorkflowStage
    from trust_signal.orchestration.case_graph import run_case
    from trust_signal.orchestration.stages import StageRunner

    request, _ = identity_pair()
    provider = Mock()
    provider.load.side_effect = lambda _: gleif_dataset()
    handler = specialist(provider)
    result = run_case(request, branches={"registry": identity}, specialists={"ownership": handler})
    assert result.aggregation is not None
    assert result.assessment.risk_score is None
    store = MemoryWorkflowStore()
    runner = StageRunner(store, identity, {WorkflowStage.OWNERSHIP: handler})
    runner.execute("run", WorkflowStage.IDENTITY)
    output = runner.execute("run", WorkflowStage.OWNERSHIP)
    assert output == runner.execute("run", WorkflowStage.OWNERSHIP)
    assert provider.load.call_count == 2
    for stage in SPECIALIST_STAGES:
        runner.execute("run", stage)
    runner.execute("run", WorkflowStage.AGGREGATE)
    runner.execute("run", WorkflowStage.VALIDATE)
    runner.execute("run", WorkflowStage.ASSESS)
    assert store.results[-1].assessment.disposition == "analyst_review"


@pytest.mark.parametrize("args", [["--ownership"], ["--norway-organization-number", NUMBER],
                                  ["--ownership", "--source-mode", "gleif_live", "--norway-organization-number", "bad"]])
def test_cli_rejects_invalid_ownership_options_before_connecting(monkeypatch, args):
    from trust_signal import cli

    monkeypatch.setattr("sys.argv", ["trust-signal", "Example Company", *args])
    connection = Mock()
    monkeypatch.setattr(cli, "application_stores", connection)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    connection.assert_not_called()
