from analysis import quality
from analysis.quality import FindingItem, QualityResult, analyze_quality
from models import Document, FindingKind, ReqType, Requirement, SourceSpan
from validate.grounding import find_span

RAW = "The website should be fast. Payment must work."


def setup():
    doc = Document(raw_text=RAW)

    def req(i, sentence, typ):
        s = RAW.index(sentence)
        span = SourceSpan(doc_id=doc.doc_id, start=s, end=s + len(sentence), quote=sentence)
        return Requirement(req_id=f"REQ-00{i}", text=sentence, type=typ, source_span=span)

    reqs = [
        req(1, "The website should be fast.", ReqType.NON_FUNCTIONAL),
        req(2, "Payment must work.", ReqType.FUNCTIONAL),
    ]
    return doc, reqs


def fake(items):
    return lambda step, system, user, schema: QualityResult(findings=items)


def test_grounded_finding_has_valid_evidence(monkeypatch):
    doc, reqs = setup()
    monkeypatch.setattr(quality, "call_json", fake([
        FindingItem(req_id="REQ-001", kind="Ambiguous", severity="High",
                    reason="'fast' has no measurable target.", quote="fast"),
    ]))
    findings, warnings = analyze_quality(doc, reqs)
    assert len(findings) == 1 and findings[0].grounded
    assert findings[0].kind == FindingKind.AMBIGUOUS
    assert doc.span_is_valid(findings[0].evidence[0])
    assert findings[0].evidence[0].quote == "fast"


def test_invented_quote_is_kept_but_not_grounded(monkeypatch):
    doc, reqs = setup()
    monkeypatch.setattr(quality, "call_json", fake([
        FindingItem(req_id="REQ-002", kind="incomplete", reason="No payment methods.",
                    quote="credit card"),
    ]))
    findings, _ = analyze_quality(doc, reqs)
    assert len(findings) == 1
    assert findings[0].grounded is False and findings[0].evidence == []


def test_open_questions_are_skipped(monkeypatch):
    doc, reqs = setup()
    reqs[1].type = ReqType.OPEN_QUESTION
    seen = []

    def spy(step, system, user, schema):
        seen.append(user)
        return QualityResult(findings=[])

    monkeypatch.setattr(quality, "call_json", spy)
    analyze_quality(doc, reqs)
    assert "REQ-001" in seen[0] and "REQ-002" not in seen[0]


def test_duplicates_and_unhandled_kinds(monkeypatch):
    doc, reqs = setup()
    monkeypatch.setattr(quality, "call_json", fake([
        FindingItem(req_id="REQ-001", kind="ambiguous", reason="a", quote="fast"),
        FindingItem(req_id="REQ-001", kind="ambiguous", reason="b", quote="fast"),
        FindingItem(req_id="REQ-002", kind="duplicate", reason="c", quote="Payment"),
    ]))
    findings, warnings = analyze_quality(doc, reqs)
    assert len(findings) == 1
    assert len(warnings) == 1


def test_find_span_respects_region():
    doc, reqs = setup()
    assert find_span(doc, "fast", within=reqs[0].source_span) is not None
    assert find_span(doc, "fast", within=reqs[1].source_span) is None