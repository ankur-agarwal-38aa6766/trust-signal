import gzip
import hashlib
import json
from io import BytesIO
from unittest.mock import Mock

import httpx
import pytest
from openpyxl import Workbook
from test_ingestion_pipeline import setup_pipeline

from trust_signal.agents.registry import gleif_registry_branch
from trust_signal.connectors.australia_sanctions import AustraliaSanctionsAdapter
from trust_signal.connectors.eu_sanctions import EUSanctionsAdapter
from trust_signal.connectors.http_source import HttpSource, SourceSchemaError
from trust_signal.connectors.norway import NorwayRegistryAdapter, NorwayRegistryProtocolError
from trust_signal.connectors.ofac import OFACAdapter
from trust_signal.connectors.registry import (
    SourceDefinition,
    SourceRegistry,
    SourceRequest,
    default_registry,
)
from trust_signal.connectors.uk_sanctions import UKSanctionsAdapter
from trust_signal.ingestion.observation import prepare_observation
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import CaseRequest, SourceMode


def test_companies_house_pause_blocks_even_with_credentials():
    store = Mock()
    result = IngestionPipeline(default_registry({"COMPANIES_HOUSE_API_KEY": "test"}), store, Mock()).ingest(
        SourceRequest(source_id="uk_companies_house", operation="lookup", value="00445790"))
    assert result.coverage == "blocked"
    assert "paused" in result.limitations[0].lower()
    store.store_observation.assert_not_called()


def test_name_discovery_keeps_lineage_and_does_not_create_findings():
    pipeline, _, _, _, batch = setup_pipeline()
    batch.records = [{"source_id": "gleif_lei_api", "legal_name": "Example", "lei": "0" * 20}]
    pipeline.registry = SourceRegistry([SourceDefinition("gleif_lei_api", "0.1.0", (), ("search",),
                                                        lambda _: iter([batch]))])
    branch = gleif_registry_branch(CaseRequest(source_mode=SourceMode.GLEIF_LIVE,
                                              party={"legal_name": "Example"}), pipeline)
    assert branch.findings == []
    assert branch.identity_resolution.status != "resolved"
    assert branch.identity_resolution.matches[0].candidate.observation_ids == ["obs_1"]


def test_norway_board_and_organization_roles_preserve_deregistration():
    payload = {"rollegrupper": [{"type": {"kode": "STYR"}, "roller": [
        {"type": {"kode": "LEDE", "beskrivelse": "Chair"}, "avregistrert": False,
         "person": {"navn": {"fornavn": "Example", "etternavn": "Person"}, "fodselsdato": "1970-01-01"}},
        {"type": {"kode": "MEDL", "beskrivelse": "Member"}, "avregistrert": True,
         "enhet": {"navn": ["Example", "Organization"], "organisasjonsnummer": "123456789"}}]}]}
    raw = json.dumps(payload).encode()
    with NorwayRegistryAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))) as adapter:
        batch = adapter.fetch_roles("923609016")
    assert len(batch.records) == 2
    assert batch.records[0]["is_board_role"]
    assert "fodselsdato" not in batch.records[0]
    assert batch.records[1]["holder_type"] == "organization"
    assert batch.records[1]["deregistered"]
    assert batch.observations[0].content_hash == "sha256:" + hashlib.sha256(raw).hexdigest()


def test_norway_roles_wrong_entity_is_rejected():
    payload = {"rollegrupper": [], "_links": {"enhet": {"href": "https://example.org/wrong"}}}
    with NorwayRegistryAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) as adapter, pytest.raises(NorwayRegistryProtocolError):
        adapter.fetch_roles("923609016")


@pytest.mark.parametrize("cls,xml,kind", [
    (OFACAdapter, '<sdnList><sdnEntry><uid>1</uid><lastName>Example</lastName><sdnType>Entity</sdnType><programList><program>TEST</program></programList></sdnEntry></sdnList>', "entity"),
    (UKSanctionsAdapter, '<Designations><Designation><UniqueID>TEST1</UniqueID><Names><Name><Name6>Example</Name6><NameType>Primary name</NameType></Name></Names><IndividualEntityShip>Entity</IndividualEntityShip><SanctionsImposedIndicators><AssetFreeze>true</AssetFreeze><TravelBan>false</TravelBan></SanctionsImposedIndicators></Designation></Designations>', "entity"),
    (EUSanctionsAdapter, '<export><sanctionEntity euReferenceNumber="EU.1"><subjectType code="enterprise"/><nameAlias wholeName="Example"/><regulation programme="TEST"/></sanctionEntity></export>', "entity"),
])
def test_sanctions_normalize_and_retain_exact_response(cls, xml, kind):
    with cls(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=xml.encode()))) as adapter:
        snapshot = adapter.fetch_snapshot()
    assert snapshot.listings[0].legal_name == "Example"
    assert snapshot.listings[0].list_type == kind
    assert snapshot.observation.raw_response_text == xml
    if cls is UKSanctionsAdapter:
        assert snapshot.listings[0].measures == ["AssetFreeze"]


@pytest.mark.parametrize("cls", [OFACAdapter, UKSanctionsAdapter, EUSanctionsAdapter])
def test_sanctions_schema_drift_fails_closed(cls):
    with cls(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"<changed/>"))) as adapter, pytest.raises(SourceSchemaError):
        adapter.fetch_snapshot()


def dfat_bytes(alias_reference="1000a"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Reference", "Type", "Name of Individual or Entity", "Name Type", "Targeted Financial Sanction", "Travel Ban"])
    sheet.append([1000, "Entity", "Example", "Primary Name", True, False])
    sheet.append([alias_reference, "Entity", "Alias", "Alias", None, None])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_dfat_preserves_workbook_and_aliases():
    raw = dfat_bytes()
    with AustraliaSanctionsAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))) as adapter:
        snapshot = adapter.fetch_snapshot()
    assert snapshot.listings[0].aliases == ["Alias"]
    assert snapshot.listings[0].measures == ["Targeted Financial Sanction"]
    assert snapshot.observation.raw_response_bytes == raw
    assert snapshot.observation.raw_response_text is None


def test_dfat_orphan_alias_is_not_silently_discarded():
    with AustraliaSanctionsAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=dfat_bytes("2000a")))) as adapter, pytest.raises(SourceSchemaError):
        adapter.fetch_snapshot()


def test_compressed_response_is_decoded_exactly_once():
    raw = b'{"articles": []}'
    with HttpSource(transport=httpx.MockTransport(lambda _: httpx.Response(200,
        content=gzip.compress(raw), headers={"Content-Encoding": "gzip"}))) as adapter:
        response = adapter.get("https://example.org")
    assert response.content == raw
    assert "Content-Encoding" not in response.headers


def test_uk_empty_primary_placeholder_uses_populated_primary_not_an_alias():
    raw = b'<Designations><Designation><UniqueID>1</UniqueID><IndividualEntityShip>Entity</IndividualEntityShip><Names><Name><NameType>Primary Name</NameType></Name><Name><Name6>Alias</Name6><NameType>Alias</NameType></Name><Name><Name6>Example</Name6><NameType>Primary name</NameType></Name></Names></Designation></Designations>'
    with UKSanctionsAdapter(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))) as adapter:
        assert adapter.fetch_snapshot().listings[0].legal_name == "Example"


def test_ofac_keeps_stable_source_url_not_expiring_download_credentials():
    def respond(request):
        if request.url.host == "sanctionslistservice.ofac.treas.gov":
            return httpx.Response(302, headers={"Location": "https://download.example.org/list?X-Amz-Signature=ephemeral"})
        return httpx.Response(200, content=b'<sdnList><sdnEntry><uid>1</uid><lastName>Example</lastName><sdnType>Entity</sdnType></sdnEntry></sdnList>')
    with OFACAdapter(transport=httpx.MockTransport(respond)) as adapter:
        assert adapter.fetch_snapshot().observation.canonical_url == OFACAdapter.url


def test_raw_response_whitespace_is_not_normalized_by_contract_validation():
    raw = b'\n {"articles": []}\n\n'
    with HttpSource(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))) as adapter:
        adapter.source_id = "test"
        response = adapter.get("https://example.org")
        observation = adapter.observation(response, "test", {"articles": []}, "application/json")
    assert observation.raw_response_text.encode() == raw
    assert prepare_observation(observation).raw_bytes == raw
