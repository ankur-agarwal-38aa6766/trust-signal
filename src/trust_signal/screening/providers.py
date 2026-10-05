"""Read sanctions snapshots only after raw storage and run logging succeed."""

from trust_signal.connectors.base import SanctionsListing
from trust_signal.connectors.registry import SourceRequest
from trust_signal.domain.sanctions import SanctionsSourceCoverage, ScreeningEvidence
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.screening.sanctions import (
    SUPPORTED_SANCTIONS_SOURCES,
    SanctionsDataset,
    VerifiedSanctionsRecord,
)


class PipelineSanctionsProvider:
    def __init__(self, pipeline: IngestionPipeline):
        self.pipeline = pipeline

    def load(self, source_id: str) -> SanctionsDataset:
        if source_id not in SUPPORTED_SANCTIONS_SOURCES:
            raise ValueError("Unsupported sanctions source.")
        run_id = None
        try:
            result = self.pipeline.ingest(SourceRequest(source_id=source_id, operation="snapshot"))
            run_id = result.run_id
            if result.source_id != source_id or not run_id:
                raise ValueError("Invalid source run identity.")
            if result.coverage in {"failed", "blocked"}:
                return SanctionsDataset(SanctionsSourceCoverage(
                    source_id=source_id, source_run_id=run_id, coverage=result.coverage,
                    limitations=result.limitations, error_category=result.error_category))
            if result.error_category or result.coverage not in {"available", "partial"} or not result.records:
                raise ValueError("A nonempty successful snapshot is required.")
            receipts = {receipt.observation_id: receipt for receipt in result.receipts}
            if len(receipts) != len(result.receipts):
                raise ValueError("Duplicate evidence receipts.")
            evidence = {}
            for item in result.evidence:
                receipt = receipts.get(item["observation_id"])
                if (receipt is None or receipt.verified_rows != 1 or receipt.source_id != source_id
                        or item["source_id"] != source_id
                        or receipt.source_record_id != item["source_record_id"]
                        or receipt.content_hash != item["content_hash"]
                        or receipt.observation_id in evidence):
                    raise ValueError("Unverified or misassociated raw evidence.")
                evidence[receipt.observation_id] = ScreeningEvidence.model_validate({
                    key: item[key] for key in ScreeningEvidence.model_fields})
            if set(evidence) != set(receipts):
                raise ValueError("Missing raw evidence metadata.")
            records = []
            listing_ids = set()
            for item in result.records:
                ids = item.get("observation_ids", [])
                if not ids or len(set(ids)) != len(ids) or any(key not in evidence for key in ids):
                    raise ValueError("Missing record evidence lineage.")
                listing = SanctionsListing.model_validate({
                    key: value for key, value in item.items() if key != "observation_ids"})
                if (listing.source_id != source_id or not listing.legal_name.strip()
                        or not listing.source_record_id.strip() or listing.source_record_id in listing_ids):
                    raise ValueError("Invalid or duplicate listing identity.")
                listing_ids.add(listing.source_record_id)
                records.append(VerifiedSanctionsRecord(listing, tuple(evidence[key] for key in ids)))
            return SanctionsDataset(SanctionsSourceCoverage(
                source_id=source_id, source_run_id=run_id, coverage=result.coverage,
                limitations=result.limitations), records)
        except Exception as exc:  # noqa: BLE001 - never expose connection/provider secrets
            return SanctionsDataset(SanctionsSourceCoverage(
                source_id=source_id, source_run_id=run_id, coverage="failed",
                error_category=type(exc).__name__,
                limitations=["Snapshot could not be verified; no listings released for screening."]))
