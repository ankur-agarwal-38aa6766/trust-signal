"""Build provenance only from persisted, hash-verified source responses."""

import json
from uuid import NAMESPACE_URL, uuid5

from trust_signal.connectors.base import EntityLookup, SanctionsSnapshot, SourceObservation
from trust_signal.domain.evidence import (
    AttributionStatus,
    EvidenceDocument,
    EvidenceType,
    FindingEvidence,
)
from trust_signal.domain.identity import IdentityCandidate, IdentityResolution, MatchStatus
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.persistence.contracts import ObservationReceipt


def stable_id(prefix: str, *values: str) -> str:
    return prefix + "_" + uuid5(NAMESPACE_URL, json.dumps(values)).hex


def verified_observation(observation: SourceObservation, receipt: ObservationReceipt) -> None:
    prepared = prepare_observation(observation)
    if (receipt.verified_rows != 1 or receipt.observation_id != prepared.observation_id
            or receipt.source_id != observation.source_id
            or receipt.source_record_id != observation.source_record_id
            or receipt.content_hash != observation.content_hash):
        raise ValueError("Evidence requires a matching verified observation receipt.")
    if observation.observed_at.tzinfo is None:
        raise ValueError("Evidence observation timestamps must include a timezone.")
    if not observation.canonical_url.startswith(("https://", "http://")):
        raise ValueError("Evidence requires a source URL.")


def registry_evidence(lookup: EntityLookup, receipt: ObservationReceipt
                      ) -> tuple[IdentityCandidate, EvidenceDocument]:
    observation, entity = lookup.observation, lookup.entity
    verified_observation(observation, receipt)
    record_id = entity.source_record_id or observation.source_record_id
    if entity.source_id != observation.source_id or record_id != observation.source_record_id:
        raise ValueError("Entity and observation refer to different source records.")
    candidate = IdentityCandidate(
        candidate_id=stable_id("candidate", entity.source_id, record_id),
        source_id=entity.source_id, source_record_id=record_id, legal_name=entity.legal_name,
        lei=entity.lei, registration_id=entity.registration_id, jurisdiction=entity.jurisdiction,
        registration_authority=entity.source_id,
        registered_address=entity.registered_address, observation_ids=[receipt.observation_id],
    )
    document = EvidenceDocument(
        evidence_id=stable_id("evidence", receipt.observation_id, record_id),
        observation_id=receipt.observation_id, source_id=observation.source_id,
        source_record_id=record_id, observation_record_id=observation.source_record_id,
        canonical_url=observation.canonical_url, observed_at=observation.observed_at,
        content_hash=observation.content_hash, connector_version=observation.connector_version,
        evidence_type=EvidenceType.REGISTRY_RECORD, source_locator="normalized_entity",
        subject_candidate_id=candidate.candidate_id,
    )
    return candidate, document


def link_finding(finding_id: str, document: EvidenceDocument,
                 resolution: IdentityResolution) -> FindingEvidence:
    match = next((m for m in resolution.matches
                  if m.candidate.candidate_id == document.subject_candidate_id), None)
    if match is None or document.observation_id not in match.candidate.observation_ids:
        raise ValueError("Evidence is not part of the identity decision.")
    if (match.candidate.source_id != document.source_id or
            match.candidate.source_record_id != document.source_record_id):
        raise ValueError("Evidence source does not match the identity candidate.")
    if (resolution.status == "resolved" and
            resolution.selected_candidate_id == match.candidate.candidate_id and
            match.status == MatchStatus.CONFIRMED and match.eligible_for_attribution):
        status = AttributionStatus.CONFIRMED
    elif match.status == MatchStatus.NO_MATCH:
        status = AttributionStatus.EXCLUDED
    else:
        status = AttributionStatus.PENDING_IDENTITY
    return FindingEvidence(
        finding_id=finding_id, evidence_id=document.evidence_id,
        subject_candidate_id=document.subject_candidate_id, attribution_status=status,
        identity_policy_version=resolution.policy_version, reason_codes=match.reason_codes,
    )


def sanctions_evidence(snapshot: SanctionsSnapshot, receipt: ObservationReceipt
                       ) -> list[tuple[IdentityCandidate, EvidenceDocument]]:
    observation = snapshot.observation
    verified_observation(observation, receipt)
    results = []
    seen = set()
    for listing in snapshot.listings:
        if listing.source_id != observation.source_id or listing.source_record_id in seen:
            raise ValueError("Sanctions listing has a mismatched source or duplicate record ID.")
        seen.add(listing.source_record_id)
        candidate = IdentityCandidate(
            candidate_id=stable_id("candidate", listing.source_id, listing.source_record_id),
            source_id=listing.source_id, source_record_id=listing.source_record_id,
            legal_name=listing.legal_name, aliases=listing.aliases,
            # Source country text is not a registry jurisdiction or an identifier scope.
            observation_ids=[receipt.observation_id],
        )
        document = EvidenceDocument(
            evidence_id=stable_id("evidence", receipt.observation_id, listing.source_record_id),
            observation_id=receipt.observation_id, source_id=listing.source_id,
            source_record_id=listing.source_record_id,
            observation_record_id=observation.source_record_id,
            canonical_url=observation.canonical_url, observed_at=observation.observed_at,
            content_hash=observation.content_hash, connector_version=observation.connector_version,
            evidence_type=EvidenceType.SANCTIONS_LISTING,
            source_locator="ENTITY:" + listing.source_record_id,
            subject_candidate_id=candidate.candidate_id,
        )
        results.append((candidate, document))
    return results
