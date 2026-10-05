"""Bounded news discovery; headlines are mentions, not attributed facts."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from trust_signal.connectors.base import SourceEvent
from trust_signal.connectors.registry import SourceRequest
from trust_signal.domain.identity import IdentityResolution
from trust_signal.domain.news import NewsCandidate, NewsResearchResult
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.models import BranchResult, CaseRequest, Finding
from trust_signal.research.provider import ResearchDataset, ResearchProvider
from trust_signal.resolution.confirmed import confirmed_subject
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.resolver import name_key

NEWS_SOURCES = ("gdelt_doc_news", "uk_fca_newsroom")


class NewsSpecialist:
    def __init__(self, provider: ResearchProvider, *, source_ids=NEWS_SOURCES,
                 clock: Callable[[], datetime] | None = None,
                 max_observation_age: timedelta = timedelta(hours=24)):
        if (not source_ids or len(set(source_ids)) != len(source_ids)
                or any(source not in NEWS_SOURCES for source in source_ids)
                or max_observation_age <= timedelta(0)):
            raise ValueError("Distinct supported sources and positive freshness are required.")
        self.provider, self.sources = provider, tuple(source_ids)
        self.clock = clock or (lambda: datetime.now(UTC))
        self.max_age = max_observation_age

    def __call__(self, request: CaseRequest, resolution: IdentityResolution) -> BranchResult:
        subject = confirmed_subject(request, resolution)
        now = self.clock()
        if now.utcoffset() is None:
            raise ValueError("Research time requires a timezone.")
        coverage, candidates = [], []
        for source in self.sources:
            operation = "search" if source == "gdelt_doc_news" else "snapshot"
            query = SourceRequest(source_id=source, operation=operation,
                                  value=subject.legal_name if operation == "search" else "")
            if operation == "search" and (len(query.value) > 200 or any(c in query.value for c in '"\\\n\r():')):
                coverage.append(ResearchCoverage(source_id=source, operation=operation, coverage="blocked",
                                                  error_category="UnsupportedQuery", limitations=["Name cannot be safely searched; not rewritten."]))
                continue
            data = self._load(query, now)
            coverage.append(data.coverage)
            if data.coverage.coverage not in {"available", "partial", "no_matches"}:
                continue
            try:
                candidates.extend(self._candidates(data, subject))
            except (ValueError, KeyError, TypeError, AttributeError):
                data.coverage.coverage = "failed"
                data.coverage.error_category = "InvalidNewsRecord"
                data.coverage.limitations.append("Invalid metadata or lineage; source records withheld.")
        limitations = [
            "Bounded metadata discovery, not complete worldwide news or verified adverse facts.",
            "All mentions require party/role confirmation; GDELT does not confer publisher trust.",
            "Metadata and links only; no article full text fetched or publisher rights inferred.",
            "Provider seen time is not publication time; no event dates are guessed.",
            "Same-title groups are possible duplicates, not independent corroboration or proven syndication.",
            "No translation, sentiment, fraud classification, risk score or automatic decision is produced.",
        ]
        for item in coverage:
            limitations.extend(f"{item.source_id}: {text}" for text in item.limitations)
            if item.coverage != "available":
                limitations.append(f"{item.source_id}: coverage {item.coverage}.")
        research = NewsResearchResult(case_id=request.case_id, subject_id=subject.candidate_id,
                                      identity_observation_ids=subject.observation_ids, checked_at=now,
                                      coverage=coverage, candidates=candidates, limitations=limitations)
        usable = any(item.coverage in {"available", "partial", "no_matches"} for item in coverage)
        return BranchResult(branch_id="news", status="completed" if usable else "failed",
                            news_research=research, findings=[self._finding(item, subject) for item in candidates],
                            sources_checked=list(self.sources), limitations=limitations,
                            error=None if usable else "No usable news discovery source.")

    def _load(self, query, now):
        try:
            data = self.provider.load(query)
            if data.coverage.source_id != query.source_id or data.coverage.operation != query.operation:
                raise ValueError("Source operation mismatch.")
            if data.coverage.coverage in {"available", "partial", "no_matches"}:
                if not data.evidence or not data.coverage.source_run_id:
                    raise ValueError("Missing persisted evidence.")
                if any(now - proof.observed_at > self.max_age or proof.observed_at > now + timedelta(minutes=5)
                       for proof in data.evidence.values()):
                    data.coverage.coverage = "stale"
                    data.coverage.limitations.append("Stale or future retrieval evidence; refresh required.")
            return data
        except Exception as exc:  # noqa: BLE001 - isolate sources without secrets
            return ResearchDataset(ResearchCoverage(source_id=query.source_id, operation=query.operation,
                                                      coverage="failed", error_category=type(exc).__name__))

    @staticmethod
    def _candidates(data, subject):
        output, seen, urls = [], set(), set()
        names = [subject.legal_name, *(alias for alias in subject.aliases if len(name_key(alias)) >= 5)]
        for record in data.records:
            event = SourceEvent.model_validate({key: value for key, value in record.items() if key != "observation_ids"})
            url = urlparse(event.canonical_url)
            official = data.coverage.source_id == "uk_fca_newsroom"
            if (event.source_id != data.coverage.source_id or not event.title.strip()
                    or not event.source_record_id.strip() or event.source_record_id in seen
                    or event.event_type != ("regulator_announcement" if official else "news_report")
                    or url.scheme not in {"https", "http"} or not url.hostname
                    or url.username or url.password or url.port not in {None, 80, 443}
                    or (official and (url.scheme != "https" or url.hostname != "www.fca.org.uk"))):
                raise ValueError("Invalid news identity or URL.")
            seen.add(event.source_record_id)
            ids = record["observation_ids"]
            if not ids or len(ids) != len(set(ids)):
                raise ValueError("Missing news lineage.")
            proof = [data.evidence[key] for key in ids]
            title = " " + name_key(event.title) + " "
            if not any(name_key(name) and " " + name_key(name) + " " in title for name in names):
                continue
            if event.canonical_url in urls:
                continue
            urls.add(event.canonical_url)
            output.append(NewsCandidate(
                candidate_id=stable_id("news", "news-0.1", subject.candidate_id, event.source_id,
                                       event.source_record_id, *sorted(ids)),
                source_id=event.source_id, source_record_id=event.source_record_id,
                event=event.model_dump(mode="json"), publisher_trust="official_newsroom" if official else "not_assessed",
                reason_codes=["title_name_mention", "party_and_role_confirmation_required"],
                possible_duplicate_group=stable_id("possible_duplicate", name_key(event.title)),
                source_run_id=data.coverage.source_run_id, evidence=proof))
        data.coverage.records_checked = len(data.records)
        return output

    @staticmethod
    def _finding(item, subject):
        proof = item.evidence[0]
        return Finding(
            finding_id=stable_id("finding", item.candidate_id), branch_id="news", claim_type="news_mention_candidate",
            claim=(f"News metadata mention: {item.event['title']}. Party role and claims require review.")[:2000],
            subject=subject.legal_name, subject_id=None, claim_key="news.article",
            claim_value=item.event["canonical_url"], claim_cardinality="multiple",
            event_id=stable_id("article", item.event["canonical_url"]),
            source_id=item.source_id, source_name=item.source_id, source_url=item.event["canonical_url"],
            source_record_id=item.source_record_id, source_run_id=item.source_run_id,
            observation_ids=[proof.observation_id for proof in item.evidence], content_hash=proof.content_hash,
            connector_version=proof.connector_version, observed_at=proof.observed_at,
            evidence_mode="live_source", verification_status="news_identity_pending")
