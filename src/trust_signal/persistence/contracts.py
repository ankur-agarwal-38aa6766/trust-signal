"""Platform-independent raw-evidence storage contract."""

from dataclasses import dataclass
from typing import Protocol

from trust_signal.connectors.base import SourceObservation


@dataclass(frozen=True)
class ObservationReceipt:
    observation_id: str
    source_id: str
    source_record_id: str
    content_hash: str
    inserted_rows: int
    verified_rows: int


class ObservationStore(Protocol):
    def store_observation(self, observation: SourceObservation) -> ObservationReceipt: ...
