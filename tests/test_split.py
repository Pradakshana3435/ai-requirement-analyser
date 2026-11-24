from ingest import split
from ingest.split import SplitItem, SplitResult, _chunks, split_requirements
from models import Document


def fake(items):
    return lambda step, system, user, schema: SplitResult(statements=items)


def test_offsets_point_to_source(monkeypatch):
    doc = Document(raw_text="Intro line.\n\nUsers must log in. Admins can add books.")
    monkeypatch.setattr(split, "call_json", fake([
        SplitItem(quote="Users must log in.", text="Users must log in."),
        SplitItem(quote="Admins can add books.", text="Admins can add books."),
    ]))
    reqs, warnings = split_requirements(doc)
    assert [r.req_id for r in reqs] == ["REQ-001", "REQ-002"]
    assert all(doc.span_is_valid(r.source_span) for r in reqs)
    assert reqs[0].source_span.start == doc.raw_text.index("Users")
    assert warnings == []


def test_whitespace_differences_are_tolerated(monkeypatch):
    doc = Document(raw_text="Users must\nlog in.")
    monkeypatch.setattr(split, "call_json", fake([
        SplitItem(quote="Users must log in.", text="Users must log in."),
    ]))
    reqs, warnings = split_requirements(doc)
    assert len(reqs) == 1 and doc.span_is_valid(reqs[0].source_span)


def test_invented_quote_is_skipped_with_warning(monkeypatch):
    doc = Document(raw_text="Users must log in.")
    monkeypatch.setattr(split, "call_json", fake([
        SplitItem(quote="The system shall send emails.", text="The system shall send emails."),
    ]))
    reqs, warnings = split_requirements(doc)
    assert reqs == []
    assert len(warnings) == 1


def test_chunks_cover_text_at_paragraph_boundaries():
    text = "A" * 3000 + "\n\n" + "B" * 3000
    chunks = _chunks(text, 5000)
    assert len(chunks) == 2
    assert text[chunks[0][0]:chunks[0][1]] == "A" * 3000
    assert text[chunks[1][0]:chunks[1][1]] == "B" * 3000