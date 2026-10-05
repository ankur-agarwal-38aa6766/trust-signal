"""Official adverse-event discovery with conservative party attribution."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from trust_signal.connectors.base import SourceEvent
from trust_signal.connectors.registry import SourceRequest
from trust_signal.domain.identity import IdentityCandidate, IdentityResolution
from trust_signal.domain.legal import LegalCandidate, LegalResearchResult
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.models import BranchResult, CaseRequest, Finding, PartyInput
from trust_signal.research.provider import ResearchDataset, ResearchProvider
from trust_signal.resolution.confirmed import confirmed_subject
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import EntityResolver, name_key

LEGAL_SOURCES = {
    "worldbank_debarment": ("snapshot", "procurement_eligibility", "www.worldbank.org"),
    "uk_fca_newsroom": ("snapshot", "regulator_announcement", "www.fca.org.uk"),
    "uk_gazette_insolvency": ("search", "insolvency_notice", "www.thegazette.co.uk"),
    "uk_find_case_law": ("search", "court_record", "caselaw.nationalarchives.gov.uk"),
}
DEFAULT_LEGAL_SOURCES = tuple(LEGAL_SOURCES)[:3]


class LegalSpecialist:
    def __init__(self, provider: ResearchProvider, *, source_ids=DEFAULT_LEGAL_SOURCES,
                 max_pages: int = 5, max_observation_age: timedelta = timedelta(hours=24),
                 clock: Callable[[], datetime] | None = None):
        if (not source_ids or len(set(source_ids)) != len(source_ids)
                or any(source not in LEGAL_SOURCES for source in source_ids)):
            raise ValueError("Select distinct supported legal sources.")
        if not 1 <= max_pages <= 100 or max_observation_age <= timedelta(0):
            raise ValueError("Bounded pagination and positive freshness are required.")
        self.provider = provider
        self.sources = tuple(source_ids)
        self.max_pages = max_pages
        self.max_age = max_observation_age
        self.clock = clock or (lambda: datetime.now(UTC))

    def __call__(self, request: CaseRequest, resolution: IdentityResolution) -> BranchResult:
        subject = confirmed_subject(request, resolution)
        now = self.clock()
        if now.utcoffset() is None:
            raise ValueError("Research time requires a timezone.")
        coverage, candidates = [], []
        for source in self.sources:
            operation, _, _ = LEGAL_SOURCES[source]
            if operation == "search" and len(subject.legal_name) > 200:
                coverage.append(ResearchCoverage(
                    source_id=source, operation=operation, coverage="blocked",
                    error_category="QueryNameTooLong", limitations=["Search name exceeds adapter limit; not truncated."]))
                continue
            dataset = self._load(SourceRequest(source_id=source, operation=operation,
                                                value=subject.legal_name if operation == "search" else "",
                                                max_pages=self.max_pages), now)
            coverage.append(dataset.coverage)
            if dataset.coverage.coverage not in {"available", "partial", "no_matches"}:
                continue
            try:
                candidates.extend(self._candidates(dataset, subject))
            except (ValueError, KeyError, TypeError, AttributeError):
                dataset.coverage.coverage = "failed"
                dataset.coverage.error_category = "InvalidLegalRecord"
                dataset.coverage.limitations.append("Record schema, source identity or lineage failed validation; withheld.")
        limitations = [
            "These sources are not worldwide or comprehensive legal/adverse-event coverage.",
            "No candidates within selected sources is not proof of no legal or adverse-event risk.",
            "Names and title mentions require analyst confirmation of party identity and role in the event.",
            "Procedural status and finality remain source metadata; publication is not a conviction or adverse outcome.",
            "Debarment eligibility flags and source dates require primary-source review; no criminal guilt is inferred.",
            "No legal applicability decision, risk score or automatic rejection is produced.",
        ]
        for item in coverage:
            limitations.extend(f"{item.source_id}: {text}" for text in item.limitations)
            if item.coverage != "available":
                limitations.append(f"{item.source_id}: coverage {item.coverage}.")
        research = LegalResearchResult(
            case_id=request.case_id, subject_id=subject.candidate_id,
            identity_observation_ids=subject.observation_ids, checked_at=now,
            coverage=coverage, candidates=candidates, limitations=limitations)
        usable = any(item.coverage in {"available", "partial", "no_matches"} for item in coverage)
        return BranchResult(
            branch_id="legal", status="completed" if usable else "failed",
            findings=[self._finding(item, subject) for item in candidates if item.status != "excluded"],
            sources_checked=list(self.sources), limitations=limitations, legal_research=research,
            error=None if usable else "No usable legal research source.")

    def _load(self, query, now):
        try:
            dataset = self.provider.load(query)
            if (dataset.coverage.source_id != query.source_id
                    or dataset.coverage.operation != query.operation):
                raise ValueError("Provider returned another source or operation.")
            if dataset.coverage.coverage in {"available", "partial", "no_matches"}:
                if not dataset.evidence or not dataset.coverage.source_run_id:
                    raise ValueError("Missing persisted legal-source evidence.")
                if any(now - item.observed_at > self.max_age or item.observed_at > now + timedelta(minutes=5)
                       for item in dataset.evidence.values()):
                    dataset.coverage.coverage = "stale"
                    dataset.coverage.limitations.append("Stale or future-dated retrieval evidence; refresh required.")
            return dataset
        except Exception as exc:  # noqa: BLE001 - isolate failures without provider/connection secrets
            return ResearchDataset(ResearchCoverage(source_id=query.source_id, operation=query.operation,
                                                      coverage="failed", error_category=type(exc).__name__))

    def _candidates(self, dataset, subject):
        source = dataset.coverage.source_id
        if source == "worldbank_debarment" and not dataset.records:
            raise ValueError("An empty debarment snapshot is not clean evidence.")
        party = PartyInput(legal_name=subject.legal_name, aliases=subject.aliases, lei=subject.lei,
                           registration_id=subject.registration_id, jurisdiction=subject.jurisdiction,
                           registration_authority=subject.registration_authority)
        output, seen = [], set()
        for record in dataset.records:
            event = SourceEvent.model_validate({key: value for key, value in record.items()
                                                if key != "observation_ids"})
            parsed = urlparse(event.canonical_url)
            if (event.source_id != source or event.event_type != LEGAL_SOURCES[source][1]
                    or parsed.scheme != "https" or parsed.hostname != LEGAL_SOURCES[source][2]
                    or parsed.username or parsed.password or parsed.port not in {None, 443}
                    or not event.title.strip() or not event.source_record_id.strip()
                    or event.source_record_id in seen):
                raise ValueError("Invalid or duplicate legal-source record.")
            seen.add(event.source_record_id)
            ids = record["observation_ids"]
            if not ids or len(ids) != len(set(ids)):
                raise ValueError("Missing legal record lineage.")
            evidence = [dataset.evidence[key] for key in ids]
            status, reasons, relevance = self._match(party, event)
            if status is None:
                continue
            output.append(LegalCandidate(
                candidate_id=stable_id("legal", "legal-0.1", subject.candidate_id, source,
                                       event.source_record_id, *sorted(ids)),
                source_id=source, source_record_id=event.source_record_id, status=status,
                relevance=relevance, reason_codes=reasons, event=event.model_dump(mode="json"),
                source_run_id=dataset.coverage.source_run_id, evidence=evidence))
        dataset.coverage.records_checked = len(dataset.records)
        return output

    @staticmethod
    def _match(party, event):
        if event.subject_name:
            candidate = IdentityCandidate(
                candidate_id=event.source_record_id, source_id=event.source_id,
                source_record_id=event.source_record_id, legal_name=event.subject_name,
                lei=event.subject_lei, registration_id=event.subject_registration_id,
                registration_authority=event.subject_registration_authority,
                jurisdiction=event.subject_registration_jurisdiction)
            match = EntityResolver().match(party, candidate)
            exact_id = any(reason in match.reason_codes for reason in ("exact_lei", "exact_scoped_registration_id"))
            if match.name_similarity < 0.8 and not exact_id:
                return None, [], "named_subject"
            if any(reason in match.reason_codes for reason in ("lei_conflict", "registration_id_conflict")):
                return "excluded", [*match.reason_codes, "comparable_identifier_mismatch"], "named_subject"
            if match.status == "confirmed":
                return "confirmed", match.reason_codes, "named_subject"
            return "potential", [*match.reason_codes, "analyst_party_confirmation_required"], "named_subject"
        title = " " + name_key(event.title) + " "
        # Full bounded phrases only: short aliases are too ambiguous for headline discovery.
        names = [party.legal_name, *(alias for alias in party.aliases if len(name_key(alias)) >= 5)]
        if any(name_key(name) and " " + name_key(name) + " " in title for name in names):
            return "potential", ["title_name_mention", "event_party_role_unknown",
                                  "analyst_party_confirmation_required"], "title_mention"
        return None, [], "title_mention"

    @staticmethod
    def _finding(candidate, subject):
        event, evidence = candidate.event, candidate.evidence[0]
        claim = (f"Official source metadata candidate: {event['title']}. "
                 f"Procedural status: {event['procedural_status']}; finality: {event['finality']}. "
                 "Review party identity, role and primary notice before an adverse conclusion.")
        return Finding(
            finding_id=stable_id("finding", candidate.candidate_id), branch_id="legal",
            claim_type="legal_event_candidate", claim=claim[:2000], subject=subject.legal_name,
            subject_id=subject.candidate_id if candidate.status == "confirmed" else None,
            claim_key="legal.source_event", claim_value=f"{candidate.source_id}:{candidate.source_record_id}",
            claim_cardinality="multiple", event_id=stable_id("source_event", candidate.source_id, candidate.source_record_id),
            source_id=candidate.source_id, source_name=candidate.source_id, source_url=event["canonical_url"],
            source_record_id=candidate.source_record_id, source_run_id=candidate.source_run_id,
            observation_ids=[item.observation_id for item in candidate.evidence],
            content_hash=evidence.content_hash, connector_version=evidence.connector_version,
            observed_at=evidence.observed_at, evidence_mode="live_source",
            procedural_status=event["procedural_status"], verification_status=f"legal_identity_{candidate.status}")
