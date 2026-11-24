from models import (
    Document, SourceSpan, Requirement, Suggestion,
    SuggestionKind, ReviewStatus,
)


def test_new_items_start_pending():
    r = Requirement(req_id="REQ-001", text="The system shall log users in.")
    assert r.review_status == ReviewStatus.PENDING


def test_span_validation():
    doc = Document(raw_text="The system should respond fast.")
    good = SourceSpan(doc_id=doc.doc_id, start=4, end=10, quote="system")
    bad = SourceSpan(doc_id=doc.doc_id, start=4, end=10, quote="server")
    assert doc.span_is_valid(good)
    assert not doc.span_is_valid(bad)


def test_final_content_prefers_edit():
    s = Suggestion(req_id="REQ-001", kind=SuggestionKind.USER_STORY, content="AI text")
    assert s.final_content == "AI text"
    s.edited_content = "Analyst text"
    assert s.final_content == "Analyst text"