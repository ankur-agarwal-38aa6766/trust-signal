"""Shared identity gate for research specialists."""

from trust_signal.domain.identity import IdentityCandidate, IdentityResolution, MatchStatus
from trust_signal.models import CaseRequest
from trust_signal.resolution.resolver import EntityResolver


def confirmed_subject(request: CaseRequest, resolution: IdentityResolution) -> IdentityCandidate:
    resolver = EntityResolver()
    recomputed = resolver.resolve(request.party, [m.candidate for m in resolution.matches])
    selected = [m for m in resolution.matches
                if m.candidate.candidate_id == resolution.selected_candidate_id]
    if (resolution.status != "resolved" or len(selected) != 1
            or selected[0].status != "confirmed" or not selected[0].eligible_for_attribution
            or not selected[0].candidate.observation_ids
            or recomputed.status != "resolved"
            or recomputed.selected_candidate_id != resolution.selected_candidate_id
            or resolver.match(request.party, selected[0].candidate).status != MatchStatus.CONFIRMED):
        raise ValueError("A persisted, confirmed identity for this request is required.")
    return selected[0].candidate
