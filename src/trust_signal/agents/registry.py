"""Registry research branches built on the source-adapter boundary."""

from trust_signal.connectors.gleif import GleifAdapter
from trust_signal.domain.identity import IdentityCandidate
from trust_signal.models import (
    BranchResult,
    BranchStatus,
    CaseRequest,
    EvidenceMode,
    Finding,
    SourceMode,
)
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import EntityResolver


def gleif_registry_branch(request: CaseRequest) -> BranchResult:
    if not request.party.lei:
        return BranchResult(
            branch_id="registry",
            status=BranchStatus.SKIPPED,
            sources_checked=["GLEIF exact-LEI lookup"],
            limitations=["An LEI is required for the configured GLEIF lookup."],
        )

    with GleifAdapter() as adapter:
        lookup = adapter.fetch_by_lei(request.party.lei)

    if lookup is None:
        return BranchResult(
            branch_id="registry",
            status=BranchStatus.COMPLETED,
            sources_checked=["GLEIF exact-LEI lookup"],
            limitations=["GLEIF returned no record for the submitted LEI."],
        )

    entity = lookup.entity
    resolution = EntityResolver().resolve(request.party, [IdentityCandidate(
        candidate_id=stable_id("candidate", entity.source_id, lookup.observation.source_record_id),
        source_id=entity.source_id, source_record_id=lookup.observation.source_record_id,
        legal_name=entity.legal_name, lei=entity.lei,
        registration_id=entity.registration_id, jurisdiction=entity.jurisdiction,
        registered_address=entity.registered_address,
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
        source_id=lookup.observation.source_id,
        source_name="Global Legal Entity Identifier Foundation (GLEIF)",
        source_url=lookup.observation.canonical_url,
        source_record_id=lookup.observation.source_record_id,
        content_hash=lookup.observation.content_hash,
        connector_version=lookup.observation.connector_version,
        observed_at=lookup.observation.observed_at,
        evidence_mode=EvidenceMode.LIVE_SOURCE,
        verification_status="source_record_retrieved",
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


def branches_for_mode(mode: SourceMode) -> dict:
    if mode == SourceMode.GLEIF_LIVE:
        return {"registry": gleif_registry_branch}
    from trust_signal.agents.fixtures import fixture_branches

    return fixture_branches()
