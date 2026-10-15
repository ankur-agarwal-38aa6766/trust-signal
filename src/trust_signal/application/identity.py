"""Live identity commands through shared ingestion, with explicit source failures."""

from datetime import UTC, datetime

from trust_signal.application.contracts import (
    IdentityCandidateView,
    IdentitySearchCommand,
    IdentitySearchResult,
    IdentityVerificationCommand,
    IdentityVerificationResult,
)
from trust_signal.connectors.registry import SourceRequest, default_registry
from trust_signal.domain.identity import IdentityCandidate, ResolutionStatus
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import PartyInput
from trust_signal.persistence.memory import InMemoryObservationStore, InMemorySourceRunStore
from trust_signal.resolution.evidence import stable_id
from trust_signal.resolution.lei import lei_checksum_state
from trust_signal.resolution.resolver import EntityResolver


class LiveIdentityService:
    def __init__(self, pipeline: IngestionPipeline | None = None):
        self.pipeline = pipeline

    def _ingest(self, operation: str, value: str):
        if self.pipeline is None:
            # Session-local evidence only. Deployments inject durable provider stores.
            self.pipeline = IngestionPipeline(default_registry({}),
                                              InMemoryObservationStore(), InMemorySourceRunStore())
        return self.pipeline.ingest(SourceRequest(source_id="gleif_lei_api",
                                                 operation=operation, value=value, max_pages=2))

    def search(self, command: IdentitySearchCommand) -> IdentitySearchResult:
        checked_at = datetime.now(UTC).isoformat()
        try:
            result = self._ingest("search", command.legal_name.strip())
            error = None
            if result.error_category or result.coverage in {"failed", "blocked"}:
                error = ("GLEIF rate limit reached. Retry after the source backoff window."
                         if result.http_status == 429 else
                         "GLEIF search could not be completed. Retry the search.")
            candidates = []
            if not error:
                seen = set()
                for record in result.records:
                    lei = record["lei"]
                    if lei in seen:
                        continue
                    seen.add(lei)
                    candidates.append(IdentityCandidateView(
                        candidate_id=stable_id("candidate", "gleif_lei_api", lei),
                        legal_name=record["legal_name"], lei=lei,
                        jurisdiction=record.get("jurisdiction"), source_record_id=lei,
                        observation_ids=record["observation_ids"]))
            return IdentitySearchResult(candidates=candidates, source_run_id=result.run_id,
                                        coverage=result.coverage, limitations=result.limitations,
                                        raw_observation_ids=[item.observation_id for item in result.receipts],
                                        error=error, http_status=result.http_status,
                                        retry_after=result.retry_after, checked_at=checked_at)
        except Exception:  # noqa: BLE001 - provider/store exceptions may expose secrets
            return IdentitySearchResult(coverage="failed", checked_at=checked_at,
                                        error="GLEIF search could not be completed. Retry the search.")

    def verify(self, command: IdentityVerificationCommand) -> IdentityVerificationResult:
        checked_at = datetime.now(UTC).isoformat()
        lei = command.lei.strip().upper()
        if command.source_mode != "gleif_live":
            return IdentityVerificationResult(status="demo", legal_name=command.legal_name,
                                              lei=lei, checked_at=checked_at)
        if lei_checksum_state(lei) != "valid":
            return IdentityVerificationResult(status="invalid", lei=lei, checked_at=checked_at,
                                              error="The LEI format or check digits are invalid.")
        try:
            result = self._ingest("lookup", lei)
            if result.error_category or result.coverage in {"failed", "blocked"}:
                return IdentityVerificationResult(status="failed", lei=lei, checked_at=checked_at,
                                                  error="Exact GLEIF verification failed. Retry verification.")
            if not result.records:
                return IdentityVerificationResult(status="not_found", lei=lei, checked_at=checked_at,
                                                  error="GLEIF returned no record for the selected LEI.")
            if result.coverage != "available" or len(result.records) != 1:
                raise ValueError("Exact identity evidence is incomplete")
            record = result.records[0]
            ids = record["observation_ids"]
            verified_ids = {receipt.observation_id for receipt in result.receipts
                            if receipt.verified_rows == 1}
            if not ids or not set(ids) <= verified_ids or record["lei"] != lei:
                raise ValueError("Exact identity has no verified observation")
            candidate = IdentityCandidate(
                candidate_id=stable_id("candidate", "gleif_lei_api", record["lei"]),
                source_id="gleif_lei_api", source_record_id=record["lei"],
                legal_name=record["legal_name"], lei=record["lei"],
                jurisdiction=record.get("jurisdiction"), observation_ids=ids)
            resolution = EntityResolver().resolve(PartyInput(
                legal_name=command.legal_name, lei=lei, jurisdiction=command.jurisdiction), [candidate])
            confirmed = resolution.status == ResolutionStatus.RESOLVED
            return IdentityVerificationResult(
                status="verified" if confirmed else "conflict", legal_name=candidate.legal_name,
                lei=candidate.lei, jurisdiction=candidate.jurisdiction, source_run_id=result.run_id,
                observation_ids=ids, checked_at=checked_at,
                error=None if confirmed else "The selected name or jurisdiction conflicts with the exact GLEIF record.")
        except Exception:  # noqa: BLE001 - preserve unknown failures without leaking driver details
            return IdentityVerificationResult(status="failed", lei=lei, checked_at=checked_at,
                                              error="Exact GLEIF verification failed. Retry verification.")
