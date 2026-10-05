"""Match confirmed organization identity to verified listings, without risk scoring."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol

from trust_signal.connectors.base import SanctionsListing
from trust_signal.domain.identity import IdentityCandidate, IdentityResolution, MatchStatus
from trust_signal.domain.sanctions import (
    SanctionsMatch,
    SanctionsScreeningResult,
    SanctionsSourceCoverage,
    ScreeningEvidence,
)
from trust_signal.models import CaseRequest, PartyInput
from trust_signal.resolution.confirmed import confirmed_subject
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import EntityResolver

SUPPORTED_SANCTIONS_SOURCES = (
    "un_security_council_consolidated_list", "us_ofac_sdn", "uk_fcdo_sanctions",
    "eu_financial_sanctions", "au_dfat_sanctions",
)


@dataclass(frozen=True)
class VerifiedSanctionsRecord:
    listing: SanctionsListing
    evidence: tuple[ScreeningEvidence, ...]


@dataclass
class SanctionsDataset:
    coverage: SanctionsSourceCoverage
    records: list[VerifiedSanctionsRecord] = field(default_factory=list)


class SanctionsProvider(Protocol):
    def load(self, source_id: str) -> SanctionsDataset: ...


class SanctionsMatcher:
    """Reuse the identity resolver; name similarity is discovery, not confidence."""

    def __init__(self, max_observation_age: timedelta = timedelta(hours=24)):
        if max_observation_age <= timedelta(0):
            raise ValueError("A positive source retrieval freshness limit is required.")
        self.max_observation_age = max_observation_age
        self.resolver = EntityResolver()

    def screen(self, request: CaseRequest, resolution: IdentityResolution,
               datasets: list[SanctionsDataset], *, now: datetime | None = None) -> SanctionsScreeningResult:
        subject = confirmed_subject(request, resolution)
        now = now or datetime.now(UTC)
        if now.utcoffset() is None:
            raise ValueError("Screening time requires a timezone.")
        if not datasets or len({d.coverage.source_id for d in datasets}) != len(datasets):
            raise ValueError("Unique, explicit screening sources are required.")
        party = PartyInput(legal_name=subject.legal_name, lei=subject.lei,
                           registration_id=subject.registration_id,
                           registration_authority=subject.registration_authority,
                           jurisdiction=subject.jurisdiction, aliases=subject.aliases,
                           registered_address=subject.registered_address)
        matches = []
        sources = []
        for dataset in datasets:
            coverage = dataset.coverage.model_copy(deep=True)
            coverage.records_checked = 0
            sources.append(coverage)
            if coverage.coverage not in {"available", "partial"}:
                continue
            if not dataset.records or not coverage.source_run_id:
                coverage.coverage = "failed"
                coverage.error_category = "MissingSnapshotEvidence"
                continue
            ids = set()
            for record in dataset.records:
                listing = record.listing
                if (listing.source_id != coverage.source_id or listing.source_record_id in ids
                        or not record.evidence or not listing.source_record_id.strip()
                        or not listing.legal_name.strip()):
                    raise ValueError("Invalid listing identity, duplicate or missing verified evidence.")
                ids.add(listing.source_record_id)
            if any(now - e.observed_at > self.max_observation_age or e.observed_at > now + timedelta(minutes=5)
                   for record in dataset.records for e in record.evidence):
                coverage.coverage = "stale"
                coverage.limitations.append("Retrieval evidence is stale or future-dated; refresh before screening.")
                continue
            for record in dataset.records:
                coverage.records_checked += 1
                match = self._match(party, record, coverage.source_run_id)
                if match:
                    matches.append(match)
        complete = all(source.coverage == "available" for source in sources)
        statuses = {match.status for match in matches}
        outcome = ("confirmed_match" if "confirmed" in statuses else "potential_match"
                   if "potential" in statuses else "no_candidates" if complete else "incomplete")
        return SanctionsScreeningResult(
            case_id=request.case_id, subject_id=subject.candidate_id,
            identity_observation_ids=subject.observation_ids, outcome=outcome, complete=complete,
            checked_at=now, sources=sources, matches=matches,
            limitations=[
                "Direct organization listings only; directors, ownership rules and debarment are not screened.",
                "No candidates means no candidate within selected sources and this matching policy, not no sanctions risk.",
                "Retrieval freshness does not independently establish the authority's publication freshness.",
                "Matching does not validate legal applicability, calculate a score or authorize rejection.",
            ],
        )

    def _match(self, party, record, run_id) -> SanctionsMatch | None:
        listing = record.listing
        candidate = IdentityCandidate(
            candidate_id=stable_id("listing", listing.source_id, listing.source_record_id),
            source_id=listing.source_id, source_record_id=listing.source_record_id,
            legal_name=listing.legal_name, aliases=listing.aliases, lei=listing.lei,
            registration_id=listing.registration_id, registration_authority=listing.registration_authority,
            # Address/country text on sanctions lists is not an issuing-registry jurisdiction.
            jurisdiction=listing.registration_jurisdiction,
            registered_address=listing.registered_address,
            observation_ids=[e.observation_id for e in record.evidence],
        )
        result = self.resolver.match(party, candidate)
        exact_id = any(reason in result.reason_codes for reason in ("exact_lei", "exact_scoped_registration_id"))
        if result.name_similarity < 0.8 and not exact_id:
            return None
        reasons = list(result.reason_codes)
        if listing.list_type.casefold() in {"individual", "person", "vessel", "aircraft"}:
            status = "excluded"
            reasons.append("incompatible_subject_type")
        elif listing.list_type.casefold() != "entity":
            status = "potential"
            reasons.append("unknown_subject_type_requires_review")
        elif any(reason in reasons for reason in ("lei_conflict", "registration_id_conflict")):
            status = "excluded"
            reasons.append("comparable_identifier_mismatch")
        elif result.status == MatchStatus.CONFIRMED:
            status = "confirmed"
        else:
            status = "potential"
            reasons.append("analyst_identity_confirmation_required")
        return SanctionsMatch(
            match_id=stable_id("sanctions_match", "sanctions-0.1", party.model_dump_json(), listing.source_id,
                               listing.source_record_id, *sorted(e.observation_id for e in record.evidence)),
            source_id=listing.source_id, listing_id=listing.source_record_id,
            listing_name=listing.legal_name, list_type=listing.list_type, status=status,
            reason_codes=reasons, name_similarity=result.name_similarity, aliases=listing.aliases,
            measures=listing.measures, programs=listing.programs, sanctions_regime=listing.sanctions_regime,
            listed_on=listing.listed_on, source_run_id=run_id, evidence=list(record.evidence),
        )
