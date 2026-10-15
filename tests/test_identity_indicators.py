from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from streamlit.testing.v1 import AppTest
from test_gleif_connector import gleif_payload

from trust_signal.application.contracts import (
    IdentityCandidateView,
    IdentitySearchCommand,
    IdentitySearchResult,
    IdentityVerificationCommand,
    IdentityVerificationResult,
)
from trust_signal.application.service import LocalSynchronousApplication
from trust_signal.connectors.base import SourceBatch
from trust_signal.connectors.gleif import GleifAdapter
from trust_signal.connectors.registry import SourceDefinition, SourceRegistry
from trust_signal.ingestion.pipeline import IngestionPipeline
from trust_signal.models import SourceMode
from trust_signal.persistence.memory import InMemoryObservationStore, InMemorySourceRunStore
from trust_signal.resolution.lei import lei_checksum_state
from ui.identity_status import search_indicator

LEI = "INR2EJN1ERAN0W5ZP974"
NAME = "MICROSOFT CORPORATION"
APP = Path(__file__).parents[1] / "ui" / "app.py"


def application(handler):
    def fetch(request):
        with GleifAdapter(transport=httpx.MockTransport(handler)) as adapter:
            if request.operation == "search":
                yield from adapter.search_by_name(request.value, max_pages=request.max_pages)
            else:
                lookup = adapter.fetch_by_lei(request.value)
                yield (SourceBatch(observations=[lookup.observation], records=[lookup.entity.model_dump(mode="json")])
                       if lookup else SourceBatch())
    pipeline = IngestionPipeline(SourceRegistry([SourceDefinition(
        "gleif_lei_api", "0.1.0", ("global",), ("search", "lookup"), fetch)]),
        InMemoryObservationStore(), InMemorySourceRunStore())
    return LocalSynchronousApplication(pipeline)


def record():
    payload = gleif_payload(LEI)
    payload["data"]["attributes"]["entity"]["legalName"]["name"] = NAME
    payload["data"]["attributes"]["entity"]["jurisdiction"] = "US-WA"
    return payload


@pytest.mark.parametrize(("value", "expected"), [
    ("", "empty"), ("INR2", "incomplete"), (LEI, "valid"),
    (LEI.lower(), "valid"), ("  " + LEI + "  ", "valid"),
    ("5493001KJTIIGC8Y1R12", "valid"),
    (LEI[:-1] + "5", "invalid_checksum"),
    (LEI[:-1] + "A", "invalid_format"),
    ("!" + LEI[1:], "invalid_format"), (LEI + "0", "invalid_format"),
])
def test_modulo_97_checks_format_and_digits_locally(value, expected):
    assert lei_checksum_state(value) == expected


def test_live_search_preserves_observation_and_actual_source_run():
    app = application(lambda _: httpx.Response(200, json={"data": [record()["data"]]}))
    result = app.search_identity(IdentitySearchCommand(NAME, source_mode="gleif_live"))
    assert result.coverage == "available" and not result.error
    assert result.source_run_id.startswith("run_")
    assert result.candidates[0].observation_ids == result.raw_observation_ids
    assert result.candidates[0].lei == LEI
    assert result.checked_at


@pytest.mark.parametrize(("response", "coverage", "status"), [
    (httpx.Response(200, json={"data": []}), "no_matches", None),
    (httpx.Response(429, headers={"Retry-After": "60"}), "failed", 429),
    (httpx.Response(503), "failed", 503),
    (httpx.Response(200, json={"wrong": "contract"}), "failed", None),
])
def test_no_matches_rate_limits_and_failures_remain_distinct(response, coverage, status):
    app = application(lambda _: response)
    result = app.search_identity(IdentitySearchCommand(NAME, source_mode="gleif_live"))
    assert result.coverage == coverage
    assert result.http_status == status
    assert bool(result.error) == (coverage == "failed")
    assert search_indicator("gleif_live", result).tone == ("red" if result.error else "green")
    if status == 429:
        assert result.retry_after == "60"


def test_capped_search_is_partial_and_not_healthy_complete():
    app = application(lambda _: httpx.Response(200, json={
        "data": [record()["data"]], "links": {"next": "https://api.gleif.org/api/v1/lei-records?page[number]=2"}}))
    result = app.search_identity(IdentitySearchCommand(NAME, source_mode="gleif_live"))
    # The configured page bound withholds a complete-coverage claim.
    assert result.coverage == "partial"
    assert search_indicator("gleif_live", result).tone == "orange"


def test_selected_name_requires_fresh_exact_lookup_and_verified_receipt():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json=record())
    app = application(handler)
    result = app.verify_identity(IdentityVerificationCommand(NAME, LEI, "US-WA"))
    assert result.status == "verified" and result.observation_ids
    assert len(calls) == 1 and calls[0].endswith("/" + LEI)
    assert result.source_run_id.startswith("run_")


@pytest.mark.parametrize(("name", "jurisdiction"), [("Other Company", "US-WA"), (NAME, "GB")])
def test_conflicting_identity_is_not_verified(name, jurisdiction):
    result = application(lambda _: httpx.Response(200, json=record())).verify_identity(
        IdentityVerificationCommand(name, LEI, jurisdiction))
    assert result.status == "conflict" and result.error


@pytest.mark.parametrize(("response", "status"), [(httpx.Response(404), "not_found"), (httpx.Response(503), "failed")])
def test_exact_lookup_failures_never_verify(response, status):
    result = application(lambda _: response).verify_identity(IdentityVerificationCommand(NAME, LEI))
    assert result.status == status and result.error


def test_invalid_checksum_and_demo_never_call_live_source():
    app = application(lambda _: pytest.fail("Unexpected live source call"))
    assert app.verify_identity(IdentityVerificationCommand(NAME, LEI[:-1] + "5")).status == "invalid"
    assert app.verify_identity(IdentityVerificationCommand(NAME, LEI, source_mode="demo_fixtures")).status == "demo"


def test_unverified_store_receipt_prevents_green_verification():
    app = application(lambda _: httpx.Response(200, json=record()))
    app._identity.pipeline.observations.store_observation = Mock(side_effect=RuntimeError("secret"))
    result = app.verify_identity(IdentityVerificationCommand(NAME, LEI))
    assert result.status == "failed"
    assert "secret" not in result.error


def html(app):
    return " ".join(element.proto.body for element in app.get("html"))


def open_live(backend):
    app = AppTest.from_file(APP)
    app.session_state["trust_signal_app"] = backend
    app.session_state["navigation"] = "Intake & Lookup"
    app.session_state["research_source_mode"] = SourceMode.GLEIF_LIVE
    return app.run(timeout=15)


def fake_backend():
    backend = Mock()
    backend.search_identity.return_value = IdentitySearchResult(coverage="available", candidates=[
        IdentityCandidateView("microsoft", NAME, LEI, "US-WA")])
    backend.verify_identity.return_value = IdentityVerificationResult(
        status="verified", legal_name=NAME, lei=LEI, observation_ids=["obs_exact"])
    return backend


def test_selection_verifies_and_editing_name_or_lei_revokes_badge():
    backend = fake_backend()
    app = open_live(backend)
    assert "GLEIF Auto-Suggest Ready" in html(app)
    app.text_input(key="input_legal_name").set_value("Microsoft").run(timeout=15)
    assert "GLEIF Real-time Auto-Suggest Active" in html(app)
    backend.verify_identity.assert_not_called()
    app.button(key="cand_box_microsoft_0").click().run(timeout=15)
    assert not app.exception
    assert app.session_state["identity_verification"].status == "verified"
    assert 'ts-name-badge green' in html(app) and ">check_circle</span> Verified" in html(app)
    assert "Modulo 97-10: Valid" in html(app)
    backend.verify_identity.assert_called_once()
    app.text_input(key="input_lei").set_value(LEI[:-1] + "5").run(timeout=15)
    assert 'ts-name-badge green' not in html(app)
    assert "Modulo 97-10: Invalid" in html(app)
    app.text_input(key="input_legal_name").set_value("Other Company").run(timeout=15)
    assert 'ts-name-badge green' not in html(app)


def test_failed_search_turns_red_and_retry_recovers_without_false_no_match():
    backend = fake_backend()
    success = backend.search_identity.return_value
    backend.search_identity.return_value = IdentitySearchResult(
        coverage="failed", http_status=429, retry_after="60", error="Rate limit reached")
    app = open_live(backend)
    app.text_input(key="input_legal_name").set_value("Microsoft").run(timeout=15)
    assert "GLEIF Auto-Suggest Rate Limited" in html(app)
    assert 'ts-search-state red' in html(app)
    assert not any("No registered entity candidates" in item.value for item in app.info)
    backend.search_identity.return_value = success
    app.button(key="retry_source_error").click().run(timeout=15)
    assert "GLEIF Real-time Auto-Suggest Active" in html(app)
    assert not app.error


def test_changing_source_mode_revokes_live_verification():
    backend = fake_backend()
    app = open_live(backend)
    app.text_input(key="input_legal_name").set_value("Microsoft").run(timeout=15)
    app.button(key="cand_box_microsoft_0").click().run(timeout=15)
    app.radio(key="research_source_mode").set_value(SourceMode.DEMO_FIXTURES).run(timeout=15)
    assert 'ts-name-badge green' not in html(app)
    assert "Fixture mode · live GLEIF off" in html(app)
    assert not app.exception
