"""Registry research branches built on the source-adapter boundary."""

from pathlib import Path

from trust_signal.config import environment_config
from trust_signal.connectors.base import EntityRecord
from trust_signal.connectors.registry import SourceRequest, default_registry
from trust_signal.domain.identity import IdentityCandidate
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import (
    BranchResult,
    BranchStatus,
    CaseRequest,
    EvidenceMode,
    Finding,
    SourceMode,
)
from trust_signal.persistence.connection import application_stores
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import EntityResolver


def gleif_registry_branch(request: CaseRequest, pipeline: IngestionPipeline | None = None) -> BranchResult:
    if pipeline is None:
        config = Path(".env")
        if not config.is_file():
            return BranchResult(branch_id="registry", status=BranchStatus.FAILED,
                                error="Snowflake ingestion configuration is required.",
                                limitations=["No source was fetched or attributed without evidence storage."])
        with application_stores(config) as (observations, runs):
            configured = IngestionPipeline(default_registry(environment_config(config)), observations, runs)
            return gleif_registry_branch(request, configured)

    name_search = not request.party.lei
    result = pipeline.ingest(SourceRequest(source_id="gleif_lei_api",
                                          operation="search" if name_search else "lookup",
                                          value=request.party.legal_name if name_search else request.party.lei))
    if result.error_category:
        return BranchResult(branch_id="registry", status=BranchStatus.FAILED,
                            sources_checked=["GLEIF name search" if name_search else "GLEIF exact-LEI lookup"],
                            error=f"Evidence ingestion failed: {result.error_category}",
                            limitations=[*result.limitations, f"Source coverage: {result.coverage}"])

    if name_search:
        candidates = {}
        for record in result.records:
            identifier = record["lei"]
            candidates[identifier] = IdentityCandidate(
                candidate_id=stable_id("candidate", "gleif_lei_api", identifier),
                source_id="gleif_lei_api", source_record_id=identifier,
                legal_name=record["legal_name"], lei=identifier,
                jurisdiction=record.get("jurisdiction"), observation_ids=record["observation_ids"],
            )
        return BranchResult(branch_id="registry", status=BranchStatus.COMPLETED,
                            identity_resolution=EntityResolver().resolve(request.party, list(candidates.values())),
                            sources_checked=["GLEIF name search"],
                            limitations=[*result.limitations, "Select and confirm an LEI before further research."])

    if not result.records:
        return BranchResult(
            branch_id="registry",
            status=BranchStatus.COMPLETED,
            sources_checked=["GLEIF exact-LEI lookup"],
            limitations=["GLEIF returned no record for the submitted LEI."],
        )

    record = result.records[0]
    observation_ids = record["observation_ids"]
    observation = next(item for item in result.evidence if item["observation_id"] in observation_ids)
    entity = EntityRecord.model_validate({key: value for key, value in record.items() if key != "observation_ids"})
    resolution = EntityResolver().resolve(request.party, [IdentityCandidate(
        candidate_id=stable_id("candidate", entity.source_id, observation["source_record_id"]),
        source_id=entity.source_id, source_record_id=observation["source_record_id"],
        legal_name=entity.legal_name, lei=entity.lei,
        registration_id=entity.registration_id, jurisdiction=entity.jurisdiction,
        registered_address=entity.registered_address,
        observation_ids=observation_ids,
    )])
    claim = (
        f"GLEIF returned this exact LEI record: {entity.legal_name}. "
        f"Jurisdiction: {entity.jurisdiction or 'not stated'}; "
        f"entity status: {entity.entity_status or 'not stated'}; "
        f"registration status: {entity.registration_status or 'not stated'}. "
        "Compare this record to the submitted party; retrieval alone is not a final identity decision."
    )
    finding = Finding(
        branch_id="registry",
        claim_type="legal_identity_record",
        claim=claim,
        subject=entity.legal_name,
        subject_id=resolution.selected_candidate_id,
        source_id=observation["source_id"],
        source_name="Global Legal Entity Identifier Foundation (GLEIF)",
        source_url=observation["canonical_url"],
        source_record_id=observation["source_record_id"],
        observation_ids=observation_ids,
        source_run_id=result.run_id,
        content_hash=observation["content_hash"],
        connector_version=observation["connector_version"],
        observed_at=observation["observed_at"],
        evidence_mode=EvidenceMode.LIVE_SOURCE,
        verification_status="source_record_persisted_and_verified",
        procedural_status=entity.registration_status,
    )
    return BranchResult(
        branch_id="registry",
        status=BranchStatus.COMPLETED,
        findings=[finding],
        identity_resolution=resolution,
        sources_checked=["GLEIF exact-LEI lookup"],
        limitations=["GLEIF coverage is limited to entities with an LEI."],
    )


def branches_for_mode(mode: SourceMode, pipeline: IngestionPipeline | None = None) -> dict:
    if mode == SourceMode.GLEIF_LIVE:
        return {"registry": lambda request: gleif_registry_branch(request, pipeline)}
    from trust_signal.agents.fixtures import fixture_branches

    return fixture_branches()
