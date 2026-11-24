import pipeline
from analysis import summary
from analysis.summary import SummaryResult, summarize
from llm.client import LLMError
from models import (
    AnalysisResult, Document, Finding, FindingKind, Requirement, Suggestion, SuggestionKind,
)

DOC = Document(raw_text="Customers must log in.")
REQ = Requirement(req_id="REQ-001", text="Customers must log in.")
FINDING = Finding(req_ids=["REQ-001"], kind=FindingKind.INCOMPLETE, reason="No method.")
SUGG = Suggestion(req_id="REQ-001", kind=SuggestionKind.CLARIFICATION_QUESTION, content="Which method?")


def patch_all(monkeypatch):
    monkeypatch.setattr(pipeline, "split_requirements", lambda d: ([REQ], []))
    monkeypatch.setattr(pipeline, "classify_requirements", lambda r: [])
    monkeypatch.setattr(pipeline, "analyze_quality", lambda d, r: ([FINDING], []))
    monkeypatch.setattr(pipeline, "find_duplicates_conflicts", lambda d, r: ([], []))
    monkeypatch.setattr(pipeline, "generate_suggestions", lambda r, f: ([SUGG], []))
    monkeypatch.setattr(pipeline, "check_new_facts", lambda r, s: [])
    monkeypatch.setattr(pipeline, "summarize", lambda r: "A login system.")


def test_full_run_collects_everything_and_reports_progress(monkeypatch):
    patch_all(monkeypatch)
    seen = []
    result = pipeline.run_analysis(DOC, progress=lambda name, p: seen.append((name, p)))
    assert result.requirements == [REQ]
    assert result.findings == [FINDING]
    assert result.suggestions == [SUGG]
    assert result.summary == "A login system."
    assert result.warnings == []
    assert seen[0][1] < seen[-1][1] == 1.0
    assert len(seen) == 7


def test_later_stage_failure_becomes_a_warning(monkeypatch):
    patch_all(monkeypatch)

    def boom(d, r):
        raise LLMError("rate limited")

    monkeypatch.setattr(pipeline, "analyze_quality", boom)
    result = pipeline.run_analysis(DOC)
    assert result.findings == []
    assert result.suggestions == [SUGG]
    assert any("Quality analysis failed" in w for w in result.warnings)


def test_no_requirements_stops_early(monkeypatch):
    patch_all(monkeypatch)
    monkeypatch.setattr(pipeline, "split_requirements", lambda d: ([], []))

    def must_not_run(*args):
        raise AssertionError("later stage ran")

    monkeypatch.setattr(pipeline, "classify_requirements", must_not_run)
    result = pipeline.run_analysis(DOC)
    assert result.requirements == []
    assert any("No requirements" in w for w in result.warnings)


def test_result_survives_json_round_trip(monkeypatch):
    patch_all(monkeypatch)
    result = pipeline.run_analysis(DOC)
    again = AnalysisResult.model_validate_json(result.model_dump_json())
    assert again == result


def test_summarize_strips_text(monkeypatch):
    monkeypatch.setattr(summary, "call_json",
                        lambda step, system, user, schema: SummaryResult(summary="  Hello.  "))
    assert summarize([REQ]) == "Hello."