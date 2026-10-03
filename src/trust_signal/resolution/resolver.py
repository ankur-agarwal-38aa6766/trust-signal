"""Identifiers establish identity; name similarity only discovers candidates."""

import unicodedata
from difflib import SequenceMatcher
from typing import Protocol

from trust_signal.domain.identity import (
    CandidateMatch,
    IdentityCandidate,
    IdentityResolution,
    MatchStatus,
    ResolutionStatus,
)
from trust_signal.models import PartyInput


def name_key(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in value).split())


def identifier_key(value: str) -> str:
    # Preserve punctuation and leading zeros: their meaning is registry-specific.
    return unicodedata.normalize("NFKC", value).strip().upper()


def jurisdiction_key(value: str) -> str:
    return value.strip().upper()


class ResolutionService(Protocol):
    def resolve(self, party: PartyInput,
                candidates: list[IdentityCandidate]) -> IdentityResolution: ...


class EntityResolver:
    policy_version = "identity-0.1"

    def match(self, party: PartyInput, candidate: IdentityCandidate) -> CandidateMatch:
        reasons = []
        conflicts = []
        exact_identifier = False
        if party.lei and candidate.lei:
            if identifier_key(party.lei) == identifier_key(candidate.lei):
                exact_identifier = True
                reasons.append("exact_lei")
            else:
                conflicts.append("lei_conflict")

        same_scope = False
        if party.jurisdiction and candidate.jurisdiction:
            left = jurisdiction_key(party.jurisdiction)
            right = jurisdiction_key(candidate.jurisdiction)
            same_scope = left == right
            if same_scope:
                reasons.append("exact_jurisdiction")
            elif left.split("-")[0] != right.split("-")[0] or (
                "-" in left and "-" in right
            ):
                conflicts.append("jurisdiction_conflict")
            else:
                reasons.append("compatible_country_subdivision")

        if party.registration_id and candidate.registration_id:
            same_authority = bool(party.registration_authority and candidate.registration_authority
                                  and identifier_key(party.registration_authority) ==
                                  identifier_key(candidate.registration_authority))
            if same_scope and same_authority:
                if identifier_key(party.registration_id) == identifier_key(candidate.registration_id):
                    exact_identifier = True
                    reasons.append("exact_scoped_registration_id")
                else:
                    conflicts.append("registration_id_conflict")
            else:
                reasons.append("registration_scope_unconfirmed")

        submitted = [name_key(n) for n in [party.legal_name, *party.aliases] if name_key(n)]
        names = [name_key(n) for n in [candidate.legal_name, *candidate.aliases] if name_key(n)]
        exact_name = bool(set(submitted) & set(names))
        similarity = max((SequenceMatcher(None, a, b).ratio()
                          for a in submitted for b in names), default=0.0)
        if exact_name:
            reasons.append("exact_name_or_alias")
        elif exact_identifier:
            conflicts.append("name_conflict")
        if party.registered_address and candidate.registered_address:
            reasons.append("exact_address" if name_key(party.registered_address) ==
                           name_key(candidate.registered_address) else "address_differs")

        if conflicts:
            status = MatchStatus.CONFLICT
        elif exact_identifier and exact_name:
            status = MatchStatus.CONFIRMED
        elif exact_name or similarity >= 0.8:
            status = MatchStatus.CANDIDATE
            reasons.append("identifier_confirmation_required")
        else:
            status = MatchStatus.NO_MATCH
            reasons.append("insufficient_matching_information")
        return CandidateMatch(candidate=candidate, status=status,
                              reason_codes=[*reasons, *conflicts],
                              name_similarity=similarity)

    def resolve(self, party: PartyInput,
                candidates: list[IdentityCandidate]) -> IdentityResolution:
        if len({c.candidate_id for c in candidates}) != len(candidates):
            raise ValueError("Candidate IDs must be unique; deduplicate before resolution.")
        matches = [self.match(party, candidate) for candidate in candidates]
        confirmed = [m for m in matches if m.status == MatchStatus.CONFIRMED]
        # Conflicting records carrying the submitted identifier need explicit review.
        relevant_conflicts = [m for m in matches if m.status == MatchStatus.CONFLICT and
                              any(r in m.reason_codes for r in
                                  ("exact_lei", "exact_scoped_registration_id"))]
        selected = None
        if len(confirmed) > 1 or (confirmed and relevant_conflicts):
            status = ResolutionStatus.AMBIGUOUS
            reasons = ["multiple_or_conflicting_identifier_records"]
        elif len(confirmed) == 1:
            status = ResolutionStatus.RESOLVED
            selected = confirmed[0].candidate.candidate_id
            confirmed[0].eligible_for_attribution = True
            reasons = confirmed[0].reason_codes
        elif any(m.status in (MatchStatus.CANDIDATE, MatchStatus.CONFLICT) for m in matches):
            status = ResolutionStatus.NEEDS_REVIEW
            reasons = ["identity_confirmation_required"]
        else:
            status = ResolutionStatus.NO_MATCH
            reasons = ["no_matching_candidate"]
        return IdentityResolution(policy_version=self.policy_version, status=status,
                                  selected_candidate_id=selected, matches=matches,
                                  reason_codes=reasons)
