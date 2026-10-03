import hashlib
from datetime import UTC, datetime

import pytest

from trust_signal.connectors.base import (
    EntityLookup,
    EntityRecord,
    SanctionsListing,
    SanctionsSnapshot,
    SourceObservation,
)
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.models import PartyInput
from trust_signal.persistence.contracts import ObservationReceipt
from trust_signal.resolution import EntityResolver
from trust_signal.resolution.evidence import link_finding, registry_evidence, sanctions_evidence
from trust_signal.resolution.service import IdentityEvidenceService

LEI = "INR2EJN1ERAN0W5ZP974"


def lookup():
    raw = '{"name":"Microsoft Corporation"}'
    return EntityLookup(
        entity=EntityRecord(source_id="gleif", source_record_id=LEI,
                            legal_name="Microsoft Corporation", lei=LEI),
        observation=SourceObservation(
            source_id="gleif", source_record_id=LEI, canonical_url="https://example.org/lei",
            observed_at=datetime(2026, 10, 3, tzinfo=UTC), connector_version="1",
            content_hash="sha256:" + hashlib.sha256(raw.encode()).hexdigest(),
            raw_payload={"name": "Microsoft Corporation"}, raw_response_text=raw),
    )


class MemoryObservationStore:
    def store_observation(self, observation):
        return ObservationReceipt(prepare_observation(observation).observation_id,
                                  observation.source_id, observation.source_record_id,
                                  observation.content_hash, 1, 1)


def test_persist_resolve_link_and_replay():
    item = lookup()
    service = IdentityEvidenceService(MemoryObservationStore())
    party = PartyInput(legal_name="Microsoft Corporation", lei=LEI)
    first = service.resolve(party, [item, item])
    assert first.resolution.status == "resolved"
    assert len(first.evidence) == 1
    assert first == service.resolve(party, [item])
    link = link_finding("finding_1", first.evidence[0], first.resolution)
    assert link.attribution_status == "confirmed"
    assert not link.eligible_for_scoring
    assert link.claim_verification_status == "not_validated"


def test_unverified_receipt_and_altered_payload_cannot_create_evidence():
    item = lookup()
    receipt = MemoryObservationStore().store_observation(item.observation)
    invalid = ObservationReceipt("wrong", receipt.source_id, receipt.source_record_id,
                                 receipt.content_hash, 1, 1)
    with pytest.raises(ValueError, match="receipt"):
        registry_evidence(item, invalid)
    item.observation.raw_response_text = "{}"
    with pytest.raises(ValueError, match="hash"):
        registry_evidence(item, receipt)


def test_mismatched_source_and_evidence_binding_rejected():
    item = lookup()
    receipt = MemoryObservationStore().store_observation(item.observation)
    item.entity.source_id = "other"
    with pytest.raises(ValueError, match="different source"):
        registry_evidence(item, receipt)
    result = IdentityEvidenceService(MemoryObservationStore()).resolve(
        PartyInput(legal_name="Microsoft Corporation", lei=LEI), [lookup()])
    result.evidence[0].observation_id = "unrelated"
    with pytest.raises(ValueError, match="not part"):
        link_finding("finding", result.evidence[0], result.resolution)


def test_sanctions_name_hit_is_pending_and_snapshot_is_traceable():
    observation = lookup().observation
    observation.source_id = "un"
    observation.source_record_id = "consolidated"
    snapshot = SanctionsSnapshot(observation=observation, listings=[SanctionsListing(
        source_id="un", source_record_id="QDe.001", legal_name="Listed Company",
        aliases=["Alias Company"], list_type="entity")])
    receipt = MemoryObservationStore().store_observation(observation)
    candidate, document = sanctions_evidence(snapshot, receipt)[0]
    resolution = EntityResolver().resolve(PartyInput(legal_name="Alias Company", lei=LEI),
                                          [candidate])
    link = link_finding("sanctions_finding", document, resolution)
    assert link.attribution_status == "pending_identity"
    assert not link.eligible_for_scoring
    assert document.observation_record_id == "consolidated"
    assert document.source_record_id == "QDe.001"


def test_conflicting_versions_fail_without_releasing_evidence():
    first, second = lookup(), lookup()
    second.entity.legal_name = "Renamed Corporation"
    with pytest.raises(ValueError, match="temporal review"):
        IdentityEvidenceService(MemoryObservationStore()).resolve(
            PartyInput(legal_name="Microsoft Corporation", lei=LEI), [first, second])
