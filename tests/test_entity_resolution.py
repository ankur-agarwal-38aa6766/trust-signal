import pytest

from trust_signal.domain.identity import IdentityCandidate, MatchStatus, ResolutionStatus
from trust_signal.models import PartyInput
from trust_signal.resolution import EntityResolver

LEI = "INR2EJN1ERAN0W5ZP974"


def candidate(**changes):
    return IdentityCandidate(**{
        "candidate_id": "microsoft", "source_id": "gleif_lei_api",
        "source_record_id": LEI, "legal_name": "MICROSOFT CORPORATION",
        "lei": LEI, "jurisdiction": "US-WA", **changes,
    })


def test_exact_lei_name_and_compatible_country_resolve():
    result = EntityResolver().resolve(
        PartyInput(legal_name="Microsoft Corporation", lei=LEI, jurisdiction="US"), [candidate()])
    assert result.status == ResolutionStatus.RESOLVED
    assert result.matches[0].eligible_for_attribution
    assert "compatible_country_subdivision" in result.matches[0].reason_codes


@pytest.mark.parametrize("changes,reason", [
    ({"lei": "5493001KJTIIGC8Y1R12"}, "lei_conflict"),
    ({"jurisdiction": "GB"}, "jurisdiction_conflict"),
    ({"jurisdiction": "US-NY"}, "jurisdiction_conflict"),
    ({"legal_name": "Other Company"}, "name_conflict"),
])
def test_identifier_or_name_conflicts_require_review(changes, reason):
    result = EntityResolver().resolve(
        PartyInput(legal_name="Microsoft Corporation", lei=LEI, jurisdiction="US-WA"),
        [candidate(**changes)])
    assert result.status == ResolutionStatus.NEEDS_REVIEW
    assert reason in result.matches[0].reason_codes
    assert not result.matches[0].eligible_for_attribution


def test_registration_number_requires_registry_and_jurisdiction():
    item = candidate(lei=None, jurisdiction="GB", registration_id="00445790",
                     registration_authority="companies_house", legal_name="TESCO PLC")
    party = PartyInput(legal_name="Tesco PLC", jurisdiction="GB", registration_id="00445790")
    assert EntityResolver().resolve(party, [item]).status == ResolutionStatus.NEEDS_REVIEW
    party.registration_authority = "companies_house"
    assert EntityResolver().resolve(party, [item]).status == ResolutionStatus.RESOLVED
    party.registration_id = "445790"
    result = EntityResolver().resolve(party, [item])
    assert "registration_id_conflict" in result.matches[0].reason_codes


def test_name_only_and_alias_hits_cannot_confirm_identity():
    for name in ("Microsoft Corporation", "Microsoft Corporatio", "Microsoft"):
        result = EntityResolver().resolve(PartyInput(legal_name=name),
                                          [candidate(aliases=["Microsoft"])])
        assert result.status == ResolutionStatus.NEEDS_REVIEW
        assert result.matches[0].status == MatchStatus.CANDIDATE
        assert not result.matches[0].eligible_for_attribution


def test_unicode_names_preserve_script_and_token_boundaries():
    resolver = EntityResolver()
    assert resolver.resolve(PartyInput(legal_name="東京株式会社", lei=LEI),
                            [candidate(legal_name="東京株式会社")]).status == "resolved"
    assert resolver.resolve(PartyInput(legal_name="AB C", lei=LEI),
                            [candidate(legal_name="A BC")]).status == "needs_review"


def test_multiple_confirmations_and_conflicting_identifier_records_are_ambiguous():
    party = PartyInput(legal_name="Microsoft Corporation", lei=LEI)
    for other in (candidate(candidate_id="second"),
                  candidate(candidate_id="second", legal_name="Other Entity")):
        result = EntityResolver().resolve(party, [candidate(), other])
        assert result.status == ResolutionStatus.AMBIGUOUS
        assert result.selected_candidate_id is None
        assert not any(m.eligible_for_attribution for m in result.matches)


def test_no_match_and_duplicate_candidates():
    resolver = EntityResolver()
    party = PartyInput(legal_name="Unrelated Business")
    assert resolver.resolve(party, []).status == "no_match"
    assert resolver.resolve(party, [candidate(lei=None)]).status == "no_match"
    with pytest.raises(ValueError, match="unique"):
        resolver.resolve(party, [candidate(), candidate()])
