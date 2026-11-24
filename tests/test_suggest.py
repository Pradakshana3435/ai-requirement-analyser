from analysis import suggest
from analysis.suggest import SuggItem, SuggResult, generate_suggestions
from models import (
    Finding, FindingKind, ReqType, Requirement, SourceSpan, SuggestionKind,
)

RAW = "Customers must log in."


def make():
    span = SourceSpan(doc_id="DOC-1", start=0, end=len(RAW), quote=RAW)
    return Requirement(req_id="REQ-001", text=RAW, type=ReqType.FUNCTIONAL, source_span=span)


def fake(items):
    return lambda step, system, user, schema: SuggResult(suggestions=items)


def test_each_item_becomes_its_own_suggestion(monkeypatch):
    req = make()
    monkeypatch.setattr(suggest, "call_json", fake([SuggItem(
        req_id="REQ-001",
        improved_requirement="Customers must log in with [TBD: login method].",
        user_story="As a customer, I want to log in, so that [benefit not stated].",
        acceptance_criteria=["Given a registered customer, When they log in, Then access is granted."],
        clarification_questions=["Which login method is required?", "What happens after a failed login?"],
    )]))
    result, warnings = generate_suggestions([req], [])
    kinds = [s.kind for s in result]
    assert kinds.count(SuggestionKind.IMPROVED_REQUIREMENT) == 1
    assert kinds.count(SuggestionKind.USER_STORY) == 1
    assert kinds.count(SuggestionKind.ACCEPTANCE_CRITERIA) == 1
    assert kinds.count(SuggestionKind.CLARIFICATION_QUESTION) == 2
    assert warnings == []
    assert all(s.evidence == [req.source_span] and s.grounded is False for s in result)


def test_empty_and_null_fields_are_skipped(monkeypatch):
    req = make()
    monkeypatch.setattr(suggest, "call_json", fake([SuggItem(
        req_id="REQ-001", improved_requirement=None, user_story="  ",
        acceptance_criteria=None, clarification_questions=["Which login method?"],
    )]))
    result, _ = generate_suggestions([req], [])
    assert [s.kind for s in result] == [SuggestionKind.CLARIFICATION_QUESTION]


def test_open_questions_skipped_and_missing_requirement_warns(monkeypatch):
    req = make()
    oq = Requirement(req_id="REQ-002", text="What if payment fails?", type=ReqType.OPEN_QUESTION)
    seen = []

    def spy(step, system, user, schema):
        seen.append(user)
        return SuggResult(suggestions=[])

    monkeypatch.setattr(suggest, "call_json", spy)
    _, warnings = generate_suggestions([req, oq], [])
    assert "REQ-002" not in seen[0]
    assert warnings == ["REQ-001: no suggestions returned"]


def test_known_issues_are_sent_to_the_model(monkeypatch):
    req = make()
    finding = Finding(req_ids=["REQ-001"], kind=FindingKind.INCOMPLETE, reason="No login method stated.")
    seen = []

    def spy(step, system, user, schema):
        seen.append(user)
        return SuggResult(suggestions=[])

    monkeypatch.setattr(suggest, "call_json", spy)
    generate_suggestions([req], [finding])
    assert "incomplete: No login method stated." in seen[0]

def test_big_documents_only_suggest_for_flagged_requirements(monkeypatch):
    reqs = [Requirement(req_id=f"REQ-{i:03d}", text=f"Statement {i}", type=ReqType.FUNCTIONAL)
            for i in range(1, 32)]
    finding = Finding(req_ids=["REQ-005"], kind=FindingKind.AMBIGUOUS, reason="Vague.")
    seen = []

    def spy(step, system, user, schema):
        seen.append(user)
        return SuggResult(suggestions=[])

    monkeypatch.setattr(suggest, "call_json", spy)
    monkeypatch.setattr(suggest.config, "SUGGEST_SCOPE", "flagged")
    generate_suggestions(reqs, [finding])
    assert len(seen) == 1 and "REQ-005" in seen[0] and "REQ-006" not in seen[0]

def test_criteria_objects_and_single_strings_are_accepted():
    item = SuggItem(
        req_id="REQ-001",
        acceptance_criteria=[
            {"given": "a member", "when": "they log in", "then": "access is granted"},
            "Given x, When y, Then z",
        ],
        clarification_questions="Which login method?",
    )
    assert item.acceptance_criteria[0] == "Given a member, When they log in, Then access is granted"
    assert item.acceptance_criteria[1] == "Given x, When y, Then z"
    assert item.clarification_questions == ["Which login method?"]

def test_story_article_is_corrected(monkeypatch):
    req = make()
    monkeypatch.setattr(suggest, "call_json", fake([SuggItem(
        req_id="REQ-001", user_story="As a applicant, I want to apply, so that I can enrol.")]))
    result, _ = generate_suggestions([req], [])
    assert result[0].content.startswith("As an applicant")