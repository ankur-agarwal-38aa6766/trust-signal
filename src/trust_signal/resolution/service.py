"""Connectable RAW -> identity -> evidence service with injected persistence."""

from trust_signal.connectors.base import EntityLookup
from trust_signal.domain.base import Contract
from trust_signal.domain.evidence import EvidenceDocument
from trust_signal.domain.identity import IdentityResolution
from trust_signal.models import PartyInput
from trust_signal.persistence.contracts import ObservationStore
from trust_signal.resolution.evidence import registry_evidence
from trust_signal.resolution.resolver import EntityResolver, ResolutionService


class ResearchIdentity(Contract):
    party: PartyInput
    resolution: IdentityResolution
    evidence: list[EvidenceDocument]


class IdentityEvidenceService:
    def __init__(self, observations: ObservationStore,
                 resolver: ResolutionService | None = None):
        self.observations = observations
        self.resolver = resolver or EntityResolver()

    def resolve(self, party: PartyInput, lookups: list[EntityLookup]) -> ResearchIdentity:
        candidates = {}
        documents = {}
        for lookup in lookups:
            receipt = self.observations.store_observation(lookup.observation)
            candidate, document = registry_evidence(lookup, receipt)
            previous = candidates.get(candidate.candidate_id)
            if previous:
                before = previous.model_dump(exclude={"observation_ids"})
                after = candidate.model_dump(exclude={"observation_ids"})
                if before != after:
                    raise ValueError("Conflicting versions of a record require temporal review.")
                candidate.observation_ids = sorted(set(
                    previous.observation_ids + candidate.observation_ids))
            candidates[candidate.candidate_id] = candidate
            documents[document.evidence_id] = document
        return ResearchIdentity(party=party.model_copy(deep=True),
                                resolution=self.resolver.resolve(party, list(candidates.values())),
                                evidence=list(documents.values()))
