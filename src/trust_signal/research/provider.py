"""Ingestion-backed research: verified responses and records released together."""

from dataclasses import dataclass, field
from typing import Protocol

from trust_signal.connectors.registry import SourceRequest
from trust_signal.domain.ownership import ResearchCoverage
from trust_signal.domain.sanctions import ScreeningEvidence
from trust_signal.ingestion.pipeline import IngestionPipeline


@dataclass
class ResearchDataset:
    coverage: ResearchCoverage
    records: list[dict] = field(default_factory=list)
    evidence: dict[str, ScreeningEvidence] = field(default_factory=dict)


class ResearchProvider(Protocol):
    def load(self, request: SourceRequest) -> ResearchDataset: ...


class PipelineResearchProvider:
    def __init__(self, pipeline: IngestionPipeline):
        self.pipeline = pipeline

    def load(self, request: SourceRequest) -> ResearchDataset:
        run_id = None
        try:
            result = self.pipeline.ingest(request)
            run_id = result.run_id
            if result.source_id != request.source_id or not run_id:
                raise ValueError("Mismatched research run.")
            coverage = ResearchCoverage(source_id=request.source_id, operation=request.operation,
                                        coverage=result.coverage, source_run_id=run_id,
                                        limitations=result.limitations, error_category=result.error_category)
            if result.coverage in {"failed", "blocked"}:
                return ResearchDataset(coverage)
            if result.error_category or result.coverage not in {"available", "partial", "no_matches"}:
                raise ValueError("Unsuccessful research run.")
            if result.coverage == "no_matches" and result.records:
                raise ValueError("Contradictory source coverage.")
            receipts = {receipt.observation_id: receipt for receipt in result.receipts}
            if not receipts or len(receipts) != len(result.receipts):
                raise ValueError("Research requires unique verified observations, including empty responses.")
            evidence = {}
            for item in result.evidence:
                receipt = receipts.get(item["observation_id"])
                if (receipt is None or receipt.verified_rows != 1
                        or receipt.source_id != request.source_id or item["source_id"] != request.source_id
                        or receipt.content_hash != item["content_hash"]
                        or receipt.source_record_id != item["source_record_id"]
                        or receipt.observation_id in evidence):
                    raise ValueError("Unverified research evidence.")
                evidence[receipt.observation_id] = ScreeningEvidence.model_validate({
                    key: item[key] for key in ScreeningEvidence.model_fields})
            if set(evidence) != set(receipts):
                raise ValueError("Missing research evidence metadata.")
            for record in result.records:
                ids = record.get("observation_ids", [])
                if not ids or len(ids) != len(set(ids)) or any(key not in evidence for key in ids):
                    raise ValueError("Research record has no verified lineage.")
            return ResearchDataset(coverage, result.records, evidence)
        except Exception as exc:  # noqa: BLE001 - isolate storage/log/source failures without secrets
            return ResearchDataset(ResearchCoverage(
                source_id=request.source_id, operation=request.operation, coverage="failed",
                source_run_id=run_id, error_category=type(exc).__name__,
                limitations=["Research evidence was not verified; records withheld."]))
