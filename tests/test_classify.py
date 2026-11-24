from analysis import classify
from analysis.classify import ClassItem, ClassResult, classify_requirements
from models import ReqType, Requirement, SourceSpan


def make(n):
    return [Requirement(req_id=f"REQ-{i:03d}", text=f"Statement {i}") for i in range(1, n + 1)]


def test_types_are_assigned_and_normalised(monkeypatch):
    reqs = make(2)
    monkeypatch.setattr(classify, "call_json", lambda step, system, user, schema: ClassResult(
        classifications=[
            ClassItem(req_id="REQ-001", type="Non-Functional"),
            ClassItem(req_id="REQ-002", type="open question"),
        ]))
    warnings = classify_requirements(reqs)
    assert reqs[0].type == ReqType.NON_FUNCTIONAL
    assert reqs[1].type == ReqType.OPEN_QUESTION
    assert warnings == []


def test_missing_and_unknown_types_give_warnings(monkeypatch):
    reqs = make(3)
    monkeypatch.setattr(classify, "call_json", lambda step, system, user, schema: ClassResult(
        classifications=[
            ClassItem(req_id="REQ-001", type="functional"),
            ClassItem(req_id="REQ-002", type="banana"),
        ]))
    warnings = classify_requirements(reqs)
    assert reqs[0].type == ReqType.FUNCTIONAL
    assert reqs[1].type is None and reqs[2].type is None
    assert len(warnings) == 2


def test_batches_of_25(monkeypatch):
    reqs = make(60)
    calls = []

    def fake(step, system, user, schema):
        calls.append(user)
        ids = [line.split(":")[0] for line in user.split("\n")[1:]]
        return ClassResult(classifications=[ClassItem(req_id=i, type="functional") for i in ids])

    monkeypatch.setattr(classify, "call_json", fake)
    warnings = classify_requirements(reqs)
    assert len(calls) == 3
    assert warnings == []
    assert all(r.type == ReqType.FUNCTIONAL for r in reqs)

def test_classifier_sees_the_original_quote(monkeypatch):
    from models import SourceSpan
    seen = []

    def fake(step, system, user, schema):
        seen.append(user)
        return ClassResult(classifications=[ClassItem(req_id="REQ-001", type="assumption")])

    monkeypatch.setattr(classify, "call_json", fake)
    span = SourceSpan(doc_id="D", start=0, end=30, quote="Assumption: every book has a barcode.")
    req = Requirement(req_id="REQ-001", text="Every book has a barcode.", source_span=span)
    classify_requirements([req])
    assert "Assumption: every book" in seen[0]