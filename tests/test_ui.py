import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from trust_signal.application.contracts import (
    IdentityCandidateView,
    IdentitySearchResult,
)
from trust_signal.application.service import InMemoryApplication

APP = Path(__file__).parents[1] / "ui" / "app.py"


@pytest.mark.parametrize("working_directory", ["ui", "outside_repository"])
def test_streamlit_script_imports_without_repository_on_pythonpath(tmp_path, working_directory):
    directory = APP.parent if working_directory == "ui" else tmp_path
    result = subprocess.run(
        [sys.executable, "-c", (
            "from streamlit.testing.v1 import AppTest; "
            f"app = AppTest.from_file({str(APP)!r}).run(timeout=15); "
            "assert not app.exception, [error.message for error in app.exception]; "
            "assert len(app.radio) == 1"
        )],
        cwd=directory,
        env={**os.environ, "PYTHONPATH": ""},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def open_intake(application=None):
    app = AppTest.from_file(APP)
    if application is not None:
        app.session_state["trust_signal_app"] = application
    app.session_state["navigation"] = "Intake & Lookup"
    return app.run(timeout=15)


@pytest.mark.parametrize("page", [
    "Review & Dossier", "Intake & Lookup", "Cases / Queue",
    "Sources & Feeds", "Operations & DAG",
])
def test_all_workspaces_render_without_calling_backend(page):
    backend = Mock()
    app = AppTest.from_file(APP)
    app.session_state["trust_signal_app"] = backend
    app.session_state["navigation"] = page
    app.run(timeout=15)
    assert not app.exception
    backend.search_identity.assert_not_called()
    backend.submit_case.assert_not_called()
    backend.get_case.assert_not_called()


def test_intake_runs_and_renders_the_demo_case():
    app = open_intake()
    app.text_input(key="input_legal_name").set_value("Example Organization Ltd")
    app.text_input(key="input_jurisdiction").set_value("GB")
    app.text_input(key="input_registration_id").set_value("00000000")
    app.button(key="btn_launch_pipeline").click().run(timeout=15)
    assert not app.exception
    assert app.session_state["case_view"].legal_name == "Example Organization Ltd"
    assert app.session_state["navigation"] == "Review & Dossier"
    assert any("Local fixtures only" in item.value for item in app.info)


def test_two_step_search_selection_and_confirmation_preserves_backend_contract():
    candidates = [IdentityCandidateView(
        candidate_id=f"cand_{index}", legal_name=f"Microsoft {suffix}",
        lei=f"INR2EJN1ERAN0W5ZP97{index}", jurisdiction="US-WA")
        for index, suffix in enumerate(["Corporation", "Online Inc", "Payments LLC", "Services Ltd"])]
    backend = InMemoryApplication(candidates_by_name={"Microsoft": candidates})
    app = open_intake(backend)
    app.text_input(key="input_legal_name").set_value("Microsoft").run(timeout=15)
    assert not app.exception
    assert len([button for button in app.button if str(button.key).startswith("cand_box_")]) == 4
    app.button(key="cand_box_cand_0_0").click().run(timeout=15)
    assert app.session_state["input_lei"] == "INR2EJN1ERAN0W5ZP970"
    assert app.session_state["input_legal_name"] == "Microsoft Corporation"
    app.button(key="btn_launch_pipeline").click().run(timeout=15)
    assert not app.exception
    assert app.session_state["case_view"].legal_name == "Microsoft Corporation"
    assert app.session_state["case_view"].lei == "INR2EJN1ERAN0W5ZP970"


def test_unrelated_rerenders_do_not_repeat_identity_lookup():
    backend = Mock()
    backend.search_identity.return_value = IdentitySearchResult(candidates=[])
    app = open_intake(backend)
    app.text_input(key="input_legal_name").set_value("Microsoft").run(timeout=15)
    backend.search_identity.assert_called_once()
    app.text_input(key="input_registration_id").set_value("123").run(timeout=15)
    backend.search_identity.assert_called_once()


def test_no_match_and_source_failure_are_visible():
    backend = Mock()
    backend.search_identity.return_value = IdentitySearchResult(candidates=[])
    app = open_intake(backend)
    app.text_input(key="input_legal_name").set_value("NonExistentEntity999").run(timeout=15)
    assert any("No registered entity candidates" in item.value for item in app.info)
    backend.search_identity.return_value = IdentitySearchResult(error="Source unavailable")
    app.text_input(key="input_legal_name").set_value("Different Entity").run(timeout=15)
    assert any("Source unavailable" in item.value for item in app.error)
    assert not app.exception


def test_backend_submission_failure_preserves_inputs_without_exposing_secrets():
    backend = Mock()
    backend.search_identity.return_value = IdentitySearchResult(candidates=[])
    backend.submit_case.side_effect = RuntimeError("secret-token-in-driver-error")
    app = open_intake(backend)
    app.text_input(key="input_legal_name").set_value("Error Corp")
    app.button(key="btn_launch_pipeline").click().run(timeout=15)
    assert not app.exception
    assert any("Error running case" in item.value for item in app.error)
    assert all("secret-token" not in item.value for item in app.error)
    assert app.session_state["input_legal_name"] == "Error Corp"


def test_queue_filters_and_native_navigation_work():
    app = AppTest.from_file(APP)
    app.session_state["navigation"] = "Cases / Queue"
    app.run(timeout=15)
    next(item for item in app.text_input if item.label == "Search investigations").set_value("not-a-listed-entity").run(timeout=15)
    assert any("No sample investigations" in item.value for item in app.info)
    next(button for button in app.button if button.label == "New Investigation").click().run(timeout=15)
    assert app.session_state["navigation"] == "Intake & Lookup"
    assert not app.exception


def test_source_filters_show_empty_state():
    app = AppTest.from_file(APP)
    app.session_state["navigation"] = "Sources & Feeds"
    app.run(timeout=15)
    next(item for item in app.text_input if item.label == "Filter sources").set_value("not-a-source").run(timeout=15)
    assert any("No connectors match" in item.value for item in app.info)
    assert not app.exception
