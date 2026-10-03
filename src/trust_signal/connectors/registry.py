"""Portable source catalog and dispatch; adapters own their HTTP clients."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Literal

from pydantic import Field, model_validator

from trust_signal.connectors.australia_sanctions import AustraliaSanctionsAdapter
from trust_signal.connectors.base import SourceBatch
from trust_signal.connectors.companies_house import CompaniesHouseAdapter
from trust_signal.connectors.eu_sanctions import EUSanctionsAdapter
from trust_signal.connectors.feeds import (
    FCANewsAdapter,
    FindCaseLawAdapter,
    GazetteInsolvencyAdapter,
)
from trust_signal.connectors.gdelt import GDELTNewsAdapter
from trust_signal.connectors.gleif import GleifAdapter
from trust_signal.connectors.norway import NorwayRegistryAdapter
from trust_signal.connectors.ofac import OFACAdapter
from trust_signal.connectors.uk_sanctions import UKSanctionsAdapter
from trust_signal.connectors.un_sanctions import UNSanctionsAdapter
from trust_signal.connectors.worldbank import WorldBankDebarmentAdapter
from trust_signal.models import Contract


class SourceRequest(Contract):
    source_id: str
    operation: Literal["lookup", "search", "relationships", "snapshot", "roles"]
    value: str = ""
    max_pages: int = Field(default=5, ge=1, le=100)

    @model_validator(mode="after")
    def require_value(self):
        if self.operation != "snapshot" and not self.value.strip():
            raise ValueError("A lookup identifier or search name is required.")
        return self


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    connector_version: str
    jurisdictions: tuple[str, ...]
    operations: tuple[str, ...]
    fetch: Callable[[SourceRequest], Iterator[SourceBatch]]
    credential_env: str | None = None
    paused_reason: str | None = None
    access_requirement: str | None = None
    credential_value: str | None = None


class SourceUnavailableError(RuntimeError):
    """A configured source is unavailable due to a missing credential."""


class SourceRegistry:
    def __init__(self, definitions: list[SourceDefinition], credentials: Mapping[str, str] | None = None):
        self._credentials = credentials
        self._sources = {definition.source_id: definition for definition in definitions}
        if len(self._sources) != len(definitions):
            raise ValueError("Duplicate source IDs.")

    def get(self, request: SourceRequest) -> SourceDefinition:
        definition = self._sources[request.source_id]
        if request.operation not in definition.operations:
            raise ValueError("Operation is not supported by this source.")
        return definition

    def catalog(self) -> list[dict]:
        credentials = self._credentials if self._credentials is not None else os.environ
        return [{"source_id": d.source_id, "connector_version": d.connector_version,
                 "jurisdictions": d.jurisdictions, "operations": d.operations,
                 "paused": bool(d.paused_reason), "paused_reason": d.paused_reason,
                 "access_requirement": d.access_requirement,
                 "configured": not d.credential_env or (
                     credentials.get(d.credential_env, "").strip().casefold() == d.credential_value
                     if d.credential_value else bool(credentials.get(d.credential_env, "").strip()))}
                for d in self._sources.values()]


def _gleif(request: SourceRequest) -> Iterator[SourceBatch]:
    with GleifAdapter() as adapter:
        if request.operation == "search":
            yield from adapter.search_by_name(request.value, max_pages=request.max_pages)
        elif request.operation == "relationships":
            yield from adapter.fetch_relationships(request.value, request.max_pages)
        else:
            yield _lookup_batch(adapter.fetch_by_lei(request.value))


def _lookup_batch(lookup) -> SourceBatch:
    if lookup is None:
        return SourceBatch()
    return SourceBatch(observations=[lookup.observation], records=[lookup.entity.model_dump(mode="json")])


def _companies_house(
    request: SourceRequest, *, credentials: Mapping[str, str] | None = None,
) -> Iterator[SourceBatch]:
    config = credentials if credentials is not None else os.environ
    key = config.get("COMPANIES_HOUSE_API_KEY", "").strip()
    if not key:
        raise SourceUnavailableError("Companies House credential is missing.")
    with CompaniesHouseAdapter(api_key=key) as adapter:
        yield _lookup_batch(adapter.fetch_company_profile(request.value))


def _norway(request: SourceRequest) -> Iterator[SourceBatch]:
    with NorwayRegistryAdapter() as adapter:
        yield (adapter.fetch_roles(request.value) if request.operation == "roles"
               else _lookup_batch(adapter.fetch_organization(request.value)))


def _un(request: SourceRequest) -> Iterator[SourceBatch]:
    with UNSanctionsAdapter() as adapter:
        snapshot = adapter.fetch_snapshot()
        yield SourceBatch(observations=[snapshot.observation],
                          records=[item.model_dump(mode="json") for item in snapshot.listings],
                          limitations=["Entity listings only; individuals are not screened."])


def _sanctions(request: SourceRequest, *, adapter_class, scope: str) -> Iterator[SourceBatch]:
    with adapter_class() as adapter:
        snapshot = adapter.fetch_snapshot()
        yield SourceBatch(observations=[snapshot.observation],
                          records=[item.model_dump(mode="json") for item in snapshot.listings],
                          limitations=[scope, "Snapshot ingestion is not an identity match or a legal decision."])


def _events(request: SourceRequest, *, adapter_class, credentials=None) -> Iterator[SourceBatch]:
    if adapter_class is FindCaseLawAdapter:
        config = credentials if credentials is not None else os.environ
        if config.get("FIND_CASELAW_COMPUTATIONAL_LICENSE_APPROVED", "").strip().lower() != "true":
            raise SourceUnavailableError("Find Case Law computational-analysis permission is required.")
    with adapter_class() as adapter:
        if adapter_class in {FindCaseLawAdapter, GazetteInsolvencyAdapter}:
            yield from adapter.search(request.value, request.max_pages)
        elif adapter_class is GDELTNewsAdapter:
            yield adapter.search(request.value)
        elif adapter_class is FCANewsAdapter:
            yield adapter.fetch_recent()
        else:
            yield adapter.fetch_snapshot()


def default_registry(credentials: Mapping[str, str] | None = None) -> SourceRegistry:
    return SourceRegistry([
        SourceDefinition(GleifAdapter.source_id, GleifAdapter.connector_version,
                         ("global",), ("lookup", "search", "relationships"), _gleif),
        SourceDefinition(CompaniesHouseAdapter.source_id, CompaniesHouseAdapter.connector_version,
                         ("GB",), ("lookup",), partial(_companies_house, credentials=credentials),
                         "COMPANIES_HOUSE_API_KEY", "Verification paused: API key unavailable."),
        SourceDefinition(NorwayRegistryAdapter.source_id, NorwayRegistryAdapter.connector_version,
                         ("NO",), ("lookup", "roles"), _norway),
        SourceDefinition(UNSanctionsAdapter.source_id, UNSanctionsAdapter.connector_version,
                         ("global",), ("snapshot",), _un),
        *[SourceDefinition(cls.source_id, cls.connector_version, jurisdictions, ("snapshot",),
                           partial(_sanctions, adapter_class=cls, scope=scope))
          for cls, jurisdictions, scope in [
              (OFACAdapter, ("US",), "SDN list only; non-SDN lists and ownership-rule screening are not included."),
              (UKSanctionsAdapter, ("GB",), "FCDO UK Sanctions List; measures are retained separately."),
              (EUSanctionsAdapter, ("EU",), "EU consolidated financial sanctions, not all EU restrictive measures."),
              (AustraliaSanctionsAdapter, ("AU",), "DFAT consolidated list; individual sanction measures are retained."),
          ]],
        *[SourceDefinition(cls.source_id, cls.connector_version, jurisdictions, operations,
                           partial(_events, adapter_class=cls, credentials=credentials), credential,
                           access_requirement="Project computational-analysis permission required; set FIND_CASELAW_COMPUTATIONAL_LICENSE_APPROVED=true only after approval."
                           if cls is FindCaseLawAdapter else None,
                           credential_value="true" if cls is FindCaseLawAdapter else None)
          for cls, jurisdictions, operations, credential in [
              (WorldBankDebarmentAdapter, ("global",), ("snapshot",), None),
              (FCANewsAdapter, ("GB",), ("snapshot",), None),
              (GazetteInsolvencyAdapter, ("GB",), ("search",), None),
              (FindCaseLawAdapter, ("GB",), ("search",), "FIND_CASELAW_COMPUTATIONAL_LICENSE_APPROVED"),
              (GDELTNewsAdapter, ("global",), ("search",), None),
          ]],
    ], credentials=credentials)
