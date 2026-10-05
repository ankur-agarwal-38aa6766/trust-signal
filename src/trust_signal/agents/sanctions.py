"""Injectable sanctions specialist; no fetching, scoring or deployment assumptions."""

from collections.abc import Callable
from datetime import UTC, datetime

from trust_signal.domain.identity import IdentityResolution
from trust_signal.domain.sanctions import SanctionsSourceCoverage
from trust_signal.models import BranchResult, CaseRequest, Finding
from trust_signal.resolution.evidence import stable_id
from trust_signal.screening.sanctions import (
    SUPPORTED_SANCTIONS_SOURCES,
    SanctionsDataset,
    SanctionsMatcher,
    SanctionsProvider,
    confirmed_subject,
)

DEFAULT_SANCTIONS_SOURCES = SUPPORTED_SANCTIONS_SOURCES[:4]


class SanctionsSpecialist:
    def __init__(self, provider: SanctionsProvider, *, source_ids=DEFAULT_SANCTIONS_SOURCES,
                 matcher: SanctionsMatcher | None = None, clock: Callable[[], datetime] | None = None):
        if (not source_ids or len(set(source_ids)) != len(source_ids)
                or any(source not in SUPPORTED_SANCTIONS_SOURCES for source in source_ids)):
            raise ValueError("Select distinct supported sanctions sources.")
        self.provider = provider
        self.source_ids = tuple(source_ids)
        self.matcher = matcher or SanctionsMatcher()
        self.clock = clock or (lambda: datetime.now(UTC))

    def __call__(self, request: CaseRequest, resolution: IdentityResolution) -> BranchResult:
        subject = confirmed_subject(request, resolution)
        datasets = []
        for source_id in self.source_ids:
            try:
                dataset = self.provider.load(source_id)
                if dataset.coverage.source_id != source_id:
                    raise ValueError("Provider returned another source.")
            except Exception as exc:  # noqa: BLE001 - isolate sources without disclosing secrets
                dataset = SanctionsDataset(SanctionsSourceCoverage(
                    source_id=source_id, coverage="failed", error_category=type(exc).__name__))
            datasets.append(dataset)
        screening = self.matcher.screen(request, resolution, datasets, now=self.clock())
        findings = []
        for match in screening.matches:
            if match.status == "excluded":
                continue
            evidence = match.evidence[0]
            findings.append(Finding(
                finding_id=stable_id("finding", match.match_id), branch_id="sanctions",
                claim_type="sanctions_listing_candidate",
                claim=(f"{match.status.title()} identity match to listing {match.listing_id}: "
                       f"{match.listing_name}. Legal applicability requires analyst review.")[:2000],
                subject=subject.legal_name,
                subject_id=subject.candidate_id if match.status == "confirmed" else None,
                claim_key="sanctions.listing_identity",
                claim_value=f"{match.source_id}:{match.listing_id}:{match.status}",
                claim_cardinality="multiple", event_id=stable_id("designation", match.source_id, match.listing_id),
                source_id=match.source_id, source_name=match.source_id,
                source_url=evidence.canonical_url, source_record_id=match.listing_id,
                source_run_id=match.source_run_id,
                observation_ids=[item.observation_id for item in match.evidence],
                content_hash=evidence.content_hash, connector_version=evidence.connector_version,
                observed_at=evidence.observed_at, evidence_mode="live_source",
                verification_status=f"sanctions_identity_{'confirmed' if match.status == 'confirmed' else 'pending'}",
                procedural_status="sanctions_designation"))
        usable = any(source.coverage in {"available", "partial"} for source in screening.sources)
        limitations = [*screening.limitations]
        for source in screening.sources:
            limitations.extend(f"{source.source_id}: {item}" for item in source.limitations)
            if source.coverage != "available":
                limitations.append(f"{source.source_id}: coverage {source.coverage}.")
        return BranchResult(
            branch_id="sanctions", status="completed" if usable else "failed",
            findings=findings, sources_checked=list(self.source_ids), limitations=limitations,
            error=None if usable else "No usable sanctions snapshot.", sanctions_screening=screening)
