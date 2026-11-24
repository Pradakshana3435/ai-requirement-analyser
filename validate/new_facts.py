#new_facts.py
import re
from typing import List, Optional
from llm.parallel import map_batches
from pydantic import BaseModel

from analysis.pairs import source_text
from llm.client import LLMError, call_json
from models import Requirement, Suggestion, SuggestionKind

BATCH_SIZE = 6
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\b")
PLACEHOLDER_RE = re.compile(r"\[[^\]]*\]")
REQ_ID_RE = re.compile(r"REQ-\d+", re.IGNORECASE)

STORY_KINDS = {SuggestionKind.USER_STORY, SuggestionKind.ACCEPTANCE_CRITERIA}
STORY_WORDS = {"as", "given", "when", "then", "and", "so", "i", "the", "a", "an"}
CHANNEL_WORDS = {
    "email", "sms", "push", "whatsapp", "otp", "api", "pdf", "qr", "gps", "upi",
    "oauth", "sso", "ldap", "csv", "excel", "bluetooth", "zigbee", "wifi",
}


def _is_real_fact(term: str, suggestion: Suggestion, source: str) -> bool:
    """Improved requirements stay strict. For user stories and acceptance criteria
    only numbers, named systems and channel words count as new facts; the story
    and Given/When/Then wording is the format, not new information."""
    if suggestion.kind not in STORY_KINDS:
        return True
    src_words = set(re.findall(r"[a-z0-9]+", source.lower()))
    if NUMBER_RE.search(term):
        return True
    words = re.findall(r"[A-Za-z0-9]+", term)
    for i, w in enumerate(words):
        low = w.lower()
        if low in src_words or low in STORY_WORDS:
            continue
        if low in CHANNEL_WORDS:
            return True
        if i > 0 and w[0].isupper():  # a named system or product mid-phrase
            return True
    return False

WORD_RE = re.compile(r"[a-z]{3,}")
GENERIC_WORDS = """the and for with that this from into onto upon when then given shall should must will would
can could may able each every all any have has had been being are was were not only also than them they their
there which while where who what user users system application ensure allow allows allowed provide provides
successfully successful valid action result results want wants need needs like role""".split()


def _stem(word: str) -> str:
    return word[:5]  # crude but enough: deliver, delivery and delivered share a stem


GENERIC_STEMS = {_stem(w) for w in GENERIC_WORDS}


def _unseen_words(suggestion: str, source: str) -> List[str]:
    """Words in the suggestion that do not appear (even as a variant) in the source text."""
    known = {_stem(w) for w in WORD_RE.findall(source.lower())} | GENERIC_STEMS
    unseen: List[str] = []
    for word in WORD_RE.findall(_strip(suggestion).lower()):
        if _stem(word) not in known and word not in unseen:
            unseen.append(word)
    return unseen

SYSTEM_PROMPT = """You check suggestions written by an assistant against the ORIGINAL requirement text.
For each suggestion, list the NEW FACTS it adds: specific things that appear in the suggestion but
are not stated in the original text, such as numbers, time limits, names, products, systems,
technologies, roles, actors, conditions or rules.

Do NOT list: placeholders in [square brackets], rewording, grammar, generic connecting words, or
things clearly implied by the original wording.
For suggestions of kind user_story or acceptance_criteria, ALSO ignore: the role in "As a ...", the
"so that" benefit, the Given/When/Then sentence structure, and expected system responses that simply
restate the requirement. For these, list only new numbers, new named systems, products or channels,
and new business rules or conditions that the original text does not contain.
Each listed item must be a short phrase copied exactly from the suggestion text.
If the suggestion adds nothing new, return an empty list.

Return JSON in exactly this shape:
{"checks": [{"sugg_id": "SUG-xxxx", "added_terms": []}]}
Return every sugg_id you were given.
"""


class CheckItem(BaseModel):
    sugg_id: str
    added_terms: Optional[List[str]] = None


class CheckResult(BaseModel):
    checks: List[CheckItem]


def _strip(text: str) -> str:
    """Remove placeholders and requirement IDs so they are not treated as facts."""
    return REQ_ID_RE.sub(" ", PLACEHOLDER_RE.sub(" ", text))


def _new_numbers(suggestion: str, source: str, kind=None) -> List[str]:
    known = set(NUMBER_RE.findall(source))
    text = _strip(suggestion)
    if kind == SuggestionKind.ACCEPTANCE_CRITERIA:
        # test data: example clock times and boundary values (limit plus or minus 1)
        text = TIME_RE.sub(" ", text)
        for k in list(known):
            if k.isdigit():
                known.update({str(int(k) - 1), str(int(k) + 1)})
    found = []
    for num in NUMBER_RE.findall(text):
        if num not in known and num not in found:
            found.append(num)
    return found


def _check_batch(batch: List[Suggestion], src_of) -> List[str]:
    warnings: List[str] = []
    by_id = {s.sugg_id: s for s in batch}
    blocks = "\n\n".join(
        f"{s.sugg_id} ({s.kind.value})\nSOURCE: {src_of(s)}\nSUGGESTION: {s.content}"
        for s in batch
    )
    try:
        result = call_json("newfacts", SYSTEM_PROMPT, "SUGGESTIONS:\n\n" + blocks, CheckResult)
    except LLMError as exc:
        return [f"New-fact check failed for {len(batch)} suggestions (left unsupported): {exc}"]

    checked = set()
    for item in result.checks:
        s = by_id.get(item.sugg_id)
        if s is None:
            continue
        checked.add(s.sugg_id)
        clean = _strip(s.content).lower()
        source = src_of(s).lower()
        for term in item.added_terms or []:
            term = term.strip()
            if not term:
                continue
            low = term.lower()
            # keep only claims we can verify ourselves
            if (low in clean and low not in source and term not in s.added_terms
                    and _is_real_fact(term, s, source)):
                s.added_terms.append(term)
        s.grounded = len(s.added_terms) == 0

    for s in batch:
        if s.sugg_id not in checked:
            warnings.append(f"{s.sugg_id}: not checked by the model (left unsupported)")
    return warnings


def check_new_facts(reqs: List[Requirement], suggestions: List[Suggestion]) -> List[str]:
    """Sets .added_terms and .grounded on each suggestion in place. Returns warnings."""
    req_by_id = {r.req_id: r for r in reqs}

    def src_of(s: Suggestion) -> str:
        r = req_by_id.get(s.req_id)
        return source_text(r) if r else ""

    to_model: List[Suggestion] = []
    for s in suggestions:
        if s.kind == SuggestionKind.CLARIFICATION_QUESTION:
            s.grounded = True
            continue
        source = src_of(s)
        s.added_terms = _new_numbers(s.content, src_of(s), s.kind)
        s.grounded = False
        if s.added_terms:
            continue  # already unsupported because of a new number; no need to ask the model
        if not _unseen_words(s.content, source):
            s.grounded = True  # only words from the source: nothing new to judge
            continue
        to_model.append(s)

    batches = [to_model[i:i + BATCH_SIZE] for i in range(0, len(to_model), BATCH_SIZE)]
    warnings: List[str] = []
    for batch_warnings in map_batches(lambda b: _check_batch(b, src_of), batches):
        warnings += batch_warnings
    return warnings