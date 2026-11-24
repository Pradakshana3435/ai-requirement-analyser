import csv
import io

from docx import Document as DocxDocument

from export.report import build_sections, to_csv, to_docx, to_markdown
from models import (
    AnalysisResult, Document, Finding, FindingKind, ReqType, Requirement, ReviewStatus,
    Severity, SourceSpan, Suggestion, SuggestionKind,
)


def make_result() -> AnalysisResult:
    doc = Document(raw_text="Customers must log in. Orders ship fast.")
    span1 = SourceSpan(doc_id=doc.doc_id, start=0, end=22, quote="Customers must log in.")
    span2 = SourceSpan(doc_id=doc.doc_id, start=23, end=40, quote="Orders ship fast.")
    reqs = [
        Requirement(req_id="REQ-001", text="Customers must log in.", type=ReqType.FUNCTIONAL, source_span=span1),
        Requirement(req_id="REQ-002", text="Orders ship fast.", type=ReqType.NON_FUNCTIONAL, source_span=span2),
    ]
    finding = Finding(
        finding_id="FND-1", req_ids=["REQ-002"], kind=FindingKind.AMBIGUOUS, severity=Severity.HIGH,
        reason="'fast' is vague.", evidence=[SourceSpan(doc_id=doc.doc_id, start=36, end=40, quote="fast")],
        grounded=True,
    )
    K = SuggestionKind
    suggestions = [
        Suggestion(sugg_id="SUG-1", req_id="REQ-001", kind=K.IMPROVED_REQUIREMENT,
                   content="Customers must log in with [TBD: method].",
                   review_status=ReviewStatus.ACCEPTED, grounded=True),
        Suggestion(sugg_id="SUG-2", req_id="REQ-002", kind=K.IMPROVED_REQUIREMENT,
                   content="Orders ship within 2 days.", grounded=False, added_terms=["2"]),
        Suggestion(sugg_id="SUG-3", req_id="REQ-001", kind=K.USER_STORY, content="AI story",
                   edited_content="Analyst story", review_status=ReviewStatus.EDITED, grounded=True),
        Suggestion(sugg_id="SUG-4", req_id="REQ-002", kind=K.CLARIFICATION_QUESTION,
                   content="What is fast?", review_status=ReviewStatus.REJECTED, grounded=True),
        Suggestion(sugg_id="SUG-5", req_id="REQ-001", kind=K.ACCEPTANCE_CRITERIA,
                   content="Given a customer, When they log in, Then access is granted.", grounded=True),
    ]
    return AnalysisResult(document=doc, requirements=reqs, findings=[finding],
                          suggestions=suggestions, summary="A login system.")


def sec(result, title):
    return next(s for s in build_sections(result) if s.title == title)


def test_sections_follow_the_spec_order():
    titles = [s.title for s in build_sections(make_result())]
    assert titles == [
        "Requirement Summary", "Requirement Inventory", "Requirement Quality Findings",
        "Improved Requirements", "User Stories", "Acceptance Criteria",
        "Clarification Questions", "Traceability", "Review Status", "Appendix: Rejected Items",
    ]


def test_rejected_items_only_appear_in_the_appendix():
    result = make_result()
    assert sec(result, "Clarification Questions").rows == []
    appendix = sec(result, "Appendix: Rejected Items")
    assert any("What is fast?" in cell for row in appendix.rows for cell in row)


def test_status_labels_flags_and_edited_text():
    result = make_result()
    improved = sec(result, "Improved Requirements").rows
    assert ["REQ-002", "Orders ship within 2 days.", "Not yet reviewed", "Unsupported (added: 2)"] in improved
    stories = sec(result, "User Stories").rows
    assert stories[0][1] == "Analyst story" and stories[0][2] == "Edited"


def test_markdown_has_headings_and_escapes_pipes():
    result = make_result()
    result.requirements[0].text = "A | B"
    md = to_markdown(result)
    assert "## Requirement Inventory" in md and "A \\| B" in md


def test_docx_opens_and_contains_the_report():
    doc = DocxDocument(io.BytesIO(to_docx(make_result())))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "Requirement Analysis Report" in text
    assert len(doc.tables) >= 5
    assert any("Customers must log in." in c.text for t in doc.tables for row in t.rows for c in row.cells)


def test_csv_has_one_row_per_requirement():
    rows = list(csv.DictReader(io.StringIO(to_csv(make_result()))))
    assert [r["req_id"] for r in rows] == ["REQ-001", "REQ-002"]
    assert rows[0]["user_story"] == "Analyst story"
    assert rows[1]["improved_status"] == "Not yet reviewed"