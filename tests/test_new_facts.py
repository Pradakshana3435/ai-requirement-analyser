from llm.client import LLMError
from models import Requirement, Suggestion, SuggestionKind
from validate import new_facts
from validate.new_facts import CheckItem, CheckResult, check_new_facts

REQ = Requirement(req_id="REQ-001", text="Orders must be delivered in 2 days.")
LOGIN = Requirement(req_id="REQ-002", text="Customers must log in.")


def sugg(sid, req_id, content, kind=SuggestionKind.IMPROVED_REQUIREMENT):
    return Suggestion(sugg_id=sid, req_id=req_id, kind=kind, content=content)


def llm_returns(monkeypatch, checks):
    monkeypatch.setattr(new_facts, "call_json",
                        lambda step, system, user, schema: CheckResult(checks=checks))


def test_new_number_is_flagged_by_code(monkeypatch):
    s = sugg("SUG-1", "REQ-001", "Orders must be delivered within 3 days.")
    llm_returns(monkeypatch, [CheckItem(sugg_id="SUG-1", added_terms=[])])
    check_new_facts([REQ], [s])
    assert s.added_terms == ["3"] and s.grounded is False


def test_placeholders_are_not_facts(monkeypatch):
    s = sugg("SUG-1", "REQ-002", "Customers must log in with [TBD: login method, 10 attempts max].")
    llm_returns(monkeypatch, [CheckItem(sugg_id="SUG-1", added_terms=[])])
    check_new_facts([LOGIN], [s])
    assert s.added_terms == [] and s.grounded is True


def test_model_claims_are_verified(monkeypatch):
    s = sugg("SUG-1", "REQ-002", "Customers must log in using OAuth.")
    llm_returns(monkeypatch, [CheckItem(sugg_id="SUG-1", added_terms=["OAuth", "Customers", "banana"])])
    check_new_facts([LOGIN], [s])
    assert s.added_terms == ["OAuth"] and s.grounded is False


def test_clarification_questions_are_skipped(monkeypatch):
    q = sugg("SUG-1", "REQ-002", "Should login use OAuth or a password?",
             SuggestionKind.CLARIFICATION_QUESTION)
    calls = []

    def spy(step, system, user, schema):
        calls.append(1)
        return CheckResult(checks=[])

    monkeypatch.setattr(new_facts, "call_json", spy)
    check_new_facts([LOGIN], [q])
    assert q.grounded is True and calls == []


def test_model_failure_leaves_items_unsupported(monkeypatch):
    s = sugg("SUG-1", "REQ-002", "Customers must log in using OAuth.")

    def boom(step, system, user, schema):
        raise LLMError("rate limited")

    monkeypatch.setattr(new_facts, "call_json", boom)
    warnings = check_new_facts([LOGIN], [s])
    assert s.grounded is False and len(warnings) == 1


def test_unchecked_item_stays_unsupported(monkeypatch):
    a = sugg("SUG-1", "REQ-002", "Customers must log in.")
    b = sugg("SUG-2", "REQ-002", "Customers must sign in.")
    llm_returns(monkeypatch, [CheckItem(sugg_id="SUG-1", added_terms=[])])
    warnings = check_new_facts([LOGIN], [a, b])
    assert a.grounded is True and b.grounded is False
    assert len(warnings) == 1

def spy_model(monkeypatch):
    calls = []

    def spy(step, system, user, schema):
        calls.append(1)
        return CheckResult(checks=[])

    monkeypatch.setattr(new_facts, "call_json", spy)
    return calls


def test_clean_rewording_skips_the_model(monkeypatch):
    calls = spy_model(monkeypatch)
    s = sugg("SUG-1", "REQ-002", "Customers must be able to log in.")
    check_new_facts([LOGIN], [s])
    assert s.grounded is True and calls == []


def test_new_word_goes_to_the_model(monkeypatch):
    calls = spy_model(monkeypatch)
    s = sugg("SUG-1", "REQ-002", "Customers must log in with fingerprint scans.")
    llm_returns_empty = CheckResult(checks=[CheckItem(sugg_id="SUG-1", added_terms=[])])
    monkeypatch.setattr(new_facts, "call_json", lambda step, system, user, schema: (calls.append(1), llm_returns_empty)[1])
    check_new_facts([LOGIN], [s])
    assert len(calls) == 1 and s.grounded is True


def test_new_number_skips_the_model(monkeypatch):
    calls = spy_model(monkeypatch)
    s = sugg("SUG-1", "REQ-001", "Orders must be delivered within 3 days.")
    check_new_facts([REQ], [s])
    assert s.added_terms == ["3"] and s.grounded is False and calls == []

from validate.new_facts import _is_real_fact


def _sugg(kind):
    return Suggestion(sugg_id="SUG-1", req_id="REQ-001", kind=kind, content="x")


def test_story_wording_is_not_a_new_fact():
    s = _sugg(SuggestionKind.USER_STORY)
    source = "Patients can book an appointment online."
    assert not _is_real_fact("As a patient", s, source)
    assert not _is_real_fact("so that I do not forget it", s, source)


def test_story_with_number_or_channel_is_a_new_fact():
    s = _sugg(SuggestionKind.ACCEPTANCE_CRITERIA)
    source = "The system must send a reminder."
    assert _is_real_fact("a reminder within 24 hours", s, source)
    assert _is_real_fact("sends an SMS reminder", s, source)
    assert not _is_real_fact("sends an SMS reminder", s, "Send an SMS reminder.")


def test_improved_requirements_stay_strict():
    s = _sugg(SuggestionKind.IMPROVED_REQUIREMENT)
    assert _is_real_fact("validation and confirmation", s, "Patients can book online.")

def test_criteria_allow_boundary_values_and_times_but_not_other_numbers():
    from validate.new_facts import _new_numbers
    src = "A member may borrow up to 5 books."
    assert _new_numbers("Given 4 books borrowed", src, SuggestionKind.ACCEPTANCE_CRITERIA) == []
    assert _new_numbers("Given a slot at 10:00 to 10:30", src, SuggestionKind.ACCEPTANCE_CRITERIA) == []
    assert _new_numbers("Given 9 books borrowed", src, SuggestionKind.ACCEPTANCE_CRITERIA) == ["9"]
    assert _new_numbers("Given 4 books borrowed", src, SuggestionKind.IMPROVED_REQUIREMENT) == ["4"]