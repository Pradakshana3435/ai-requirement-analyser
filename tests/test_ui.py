from pathlib import Path
from tests.test_report import make_result
from streamlit.testing.v1 import AppTest
from ui.report_tab import RESULT_KEY
from models import AnalysisResult, Document, Requirement, Suggestion, SuggestionKind

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_starts_without_error():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception


def test_inventory_shows_counts_when_a_result_exists():
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = AnalysisResult(
        document=Document(raw_text="Customers must log in."),
        requirements=[Requirement(req_id="REQ-001", text="Customers must log in.")],
    )
    at.session_state["view"] = "2. Inventory"
    at.run()
    assert not at.exception
    assert any(m.label == "Requirements" and m.value == "1" for m in at.metric)

def test_review_tab_pages_long_lists():
    doc = Document(raw_text="Customers must log in.")
    reqs = [Requirement(req_id="REQ-001", text="Customers must log in.")]
    suggs = [Suggestion(req_id="REQ-001", kind=SuggestionKind.USER_STORY, content=f"Story {i}")
             for i in range(25)]
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = AnalysisResult(document=doc, requirements=reqs, suggestions=suggs)
    at.session_state["view"] = "3. Review"
    at.run()
    assert not at.exception
    assert any("Page 1 of 3" in m.value for m in at.markdown)

def test_report_tab_shows_placeholder_without_result():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.session_state["view"] = "4. Report"
    at.run()
    assert not at.exception
    assert any("Run an analysis" in i.value for i in at.info)


def test_report_tab_renders_with_result():
    from streamlit.testing.v1 import AppTest
    from tests.test_report import make_result
    from ui.report_tab import RESULT_KEY
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.session_state[RESULT_KEY] = make_result()
    at.session_state["view"] = "4. Report"
    at.run()
    assert not at.exception