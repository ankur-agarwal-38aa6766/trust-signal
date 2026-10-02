from pathlib import Path

from streamlit.testing.v1 import AppTest

from trust_signal.models import SourceMode


def test_intake_runs_and_renders_the_demo_case():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run(timeout=15)
    app.text_input[0].set_value("Example Organization Ltd")
    app.text_input[1].set_value("GB")
    app.text_input[2].set_value("00000000")
    app.button[0].click().run(timeout=15)

    assert not app.exception
    assert "Example Organization Ltd" in [item.value for item in app.subheader]
    assert any("Local fixtures only" in item.value for item in app.info)


def test_live_mode_without_lei_requests_more_information_without_fetching():
    app = AppTest.from_file(Path(__file__).parents[1] / "app.py").run(timeout=15)
    app.radio[0].set_value(SourceMode.GLEIF_LIVE)
    app.text_input[0].set_value("Example Organization Ltd")
    app.button[0].click().run(timeout=15)

    assert not app.exception
    assert any("More identity information" in item.value for item in app.warning)
    assert any(item.value == "lei" for item in app.markdown)
