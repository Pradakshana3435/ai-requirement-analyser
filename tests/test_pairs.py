from analysis import pairs
from analysis.pairs import PairItem, PairResult, find_duplicates_conflicts, shortlist_pairs
from models import Document, FindingKind, Requirement, Severity, SourceSpan

RAW = "Orders must be delivered in 2 days. Delivery can take up to 5 days."


def setup():
    doc = Document(raw_text=RAW)

    def req(i, sentence):
        s = RAW.index(sentence)
        span = SourceSpan(doc_id=doc.doc_id, start=s, end=s + len(sentence), quote=sentence)
        return Requirement(req_id=f"REQ-00{i}", text=sentence, source_span=span)

    return doc, [req(1, "Orders must be delivered in 2 days."), req(2, "Delivery can take up to 5 days.")]


def use_pair(monkeypatch, reqs, items):
    monkeypatch.setattr(pairs, "shortlist_pairs", lambda r: [(reqs[0], reqs[1], 0.9)])
    monkeypatch.setattr(pairs, "call_json",
                        lambda step, system, user, schema: PairResult(results=items))


def test_shortlist_pairs_similar_wording_only():
    reqs = [
        Requirement(req_id="REQ-001", text="Customers must log in to place an order."),
        Requirement(req_id="REQ-002", text="Customers need to log in to place an order."),
        Requirement(req_id="REQ-003", text="Admin can add books."),
    ]
    result = shortlist_pairs(reqs)
    assert [(a.req_id, b.req_id) for a, b, _ in result] == [("REQ-001", "REQ-002")]


def test_shortlist_needs_two_requirements():
    assert shortlist_pairs([Requirement(req_id="REQ-001", text="Only one.")]) == []


def test_conflict_finding_with_two_evidence_spans(monkeypatch):
    doc, reqs = setup()
    use_pair(monkeypatch, reqs, [PairItem(pair_id="P1", relation="Conflict",
                                          reason="2 days versus up to 5 days.",
                                          quote_a="2 days", quote_b="5 days")])
    findings, warnings = find_duplicates_conflicts(doc, reqs)
    assert len(findings) == 1
    f = findings[0]
    assert f.kind == FindingKind.CONFLICT and f.severity == Severity.HIGH
    assert f.req_ids == ["REQ-001", "REQ-002"] and f.grounded
    assert [s.quote for s in f.evidence] == ["2 days", "5 days"]
    assert all(doc.span_is_valid(s) for s in f.evidence)


def test_none_is_ignored(monkeypatch):
    doc, reqs = setup()
    use_pair(monkeypatch, reqs, [PairItem(pair_id="P1", relation="none")])
    findings, warnings = find_duplicates_conflicts(doc, reqs)
    assert findings == [] and warnings == []


def test_invented_quotes_are_not_grounded(monkeypatch):
    doc, reqs = setup()
    use_pair(monkeypatch, reqs, [PairItem(pair_id="P1", relation="duplicate",
                                          reason="Same.", quote_a="by drone", quote_b="5 days")])
    findings, _ = find_duplicates_conflicts(doc, reqs)
    assert findings[0].grounded is False
    assert len(findings[0].evidence) == 1

def test_shortlist_matches_different_word_forms():
    reqs = [
        Requirement(req_id="REQ-001", text="Payment is made in cash only."),
        Requirement(req_id="REQ-002", text="Riders can pay by card or wallet inside the app."),
        Requirement(req_id="REQ-003", text="Admins can add books."),
    ]
    ids = [(a.req_id, b.req_id) for a, b, _ in shortlist_pairs(reqs)]
    assert ("REQ-001", "REQ-002") in ids