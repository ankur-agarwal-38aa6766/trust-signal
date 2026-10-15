"""In-memory observation and run store implementations for platform-independent execution and testing."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import RLock
from uuid import NAMESPACE_URL, uuid5

from trust_signal.connectors.base import SourceObservation
from trust_signal.persistence.contracts import ObservationReceipt, ObservationStore
from trust_signal.persistence.source_runs import SourceRun, SourceRunStore


class InMemoryObservationStore(ObservationStore):
    """Platform-independent in-memory store for observation byte/hash verification."""

    def __init__(self) -> None:
        self.observations: dict[str, SourceObservation] = {}
        self.receipts: dict[str, ObservationReceipt] = {}
        self._lock = RLock()

    def store_observation(self, observation: SourceObservation) -> ObservationReceipt:
        with self._lock:
            identity = json.dumps(
                [
                    observation.source_id,
                    observation.source_record_id,
                    observation.observed_at.isoformat(),
                    observation.content_hash,
                ],
                separators=(",", ":"),
            )
            obs_id = f"observation_{uuid5(NAMESPACE_URL, identity).hex}"
            receipt = ObservationReceipt(
                observation_id=obs_id,
                source_id=observation.source_id,
                source_record_id=observation.source_record_id,
                content_hash=observation.content_hash,
                inserted_rows=1,
                verified_rows=1,
            )
            self.observations[obs_id] = observation
            self.receipts[obs_id] = receipt
            return receipt


@dataclass
class RunRecord:
    run: SourceRun
    started_details: dict
    finished: bool = False
    status: str | None = None
    seen: int = 0
    accepted: int = 0
    error_category: str | None = None
    finished_details: dict = field(default_factory=dict)


class InMemorySourceRunStore(SourceRunStore):
    """Platform-independent in-memory store for run lifecycle."""

    def __init__(self) -> None:
        self.runs: dict[str, RunRecord] = {}
        self._lock = RLock()

    def start(self, run: SourceRun, details: dict) -> None:
        with self._lock:
            self.runs[run.run_id] = RunRecord(run=run, started_details=details)

    def finish(
        self,
        run: SourceRun,
        status: str,
        seen: int,
        accepted: int,
        error_category: str | None,
        details: dict,
    ) -> None:
        with self._lock:
            if run.run_id in self.runs:
                record = self.runs[run.run_id]
                record.finished = True
                record.status = status
                record.seen = seen
                record.accepted = accepted
                record.error_category = error_category
                record.finished_details = details
            else:
                self.runs[run.run_id] = RunRecord(
                    run=run,
                    started_details={},
                    finished=True,
                    status=status,
                    seen=seen,
                    accepted=accepted,
                    error_category=error_category,
                    finished_details=details,
                )
