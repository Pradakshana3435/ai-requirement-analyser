import re
from collections import defaultdict
from typing import List, Optional, Tuple
from llm.parallel import map_batches
from pydantic import BaseModel,field_validator
import config
from analysis.pairs import source_text
from llm.client import call_json
from models import Finding, ReqType, Requirement, Suggestion, SuggestionKind

BATCH_SIZE = 5
MAX_ITEMS = 3  # criteria / questions kept per requirement
FLAGGED_ABOVE = 30

SYSTEM_PROMPT = """You are a senior business analyst. For each requirement, produce suggestions that
help a Business Analyst finalise it. You may use ONLY information present in the requirement text.

For each requirement return:
- improved_requirement: a clearer, testable rewrite of the statement. Use the same facts. When a
  needed detail is missing (a number, limit, role, method, deadline), write a placeholder such as
  [TBD: response time limit] instead of inventing a value. If the statement is already clear, return "".
- user_story: "As a <role>, I want <goal>, so that <benefit>." Only for functional requirements or
  rules that serve a user goal; otherwise "". If the role or benefit is not stated, write
  [role not stated] or [benefit not stated] instead of guessing.
- acceptance_criteria: 1 to 4 items in the form "Given <context>, When <action>, Then <outcome>".
  Use only what the text supports; use [TBD: ...] placeholders for missing values. If the
  requirement is too vague to test, return an empty list.
- clarification_questions: 1 to 4 short questions that would resolve the missing or unclear
  information, including the known issues listed for the requirement.

Never add numbers, names, systems, roles, deadlines or technologies that are not in the text.

Return JSON in exactly this shape:
{"suggestions": [{"req_id": "REQ-001", "improved_requirement": "", "user_story": "",
 "acceptance_criteria": [], "clarification_questions": []}]}
"""

def _as_text(item) -> str:
    """Models sometimes return an object instead of a string."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        lower = {str(k).lower(): v for k, v in item.items()}
        if {"given", "when", "then"} <= set(lower):
            return f"Given {lower['given']}, When {lower['when']}, Then {lower['then']}"
        return " ".join(str(v) for v in item.values())
    return str(item)

class SuggItem(BaseModel):
    req_id: str
    improved_requirement: Optional[str] = ""
    user_story: Optional[str] = ""
    acceptance_criteria: Optional[List[str]] = None
    clarification_questions: Optional[List[str]] = None
    @field_validator("acceptance_criteria", "clarification_questions", mode="before")
    @classmethod
    def _to_text_list(cls, value):
        if value is None:
            return value
        if isinstance(value, (str, dict)):
            value = [value]
        return [_as_text(v) for v in value]

class SuggResult(BaseModel):
    suggestions: List[SuggItem]


def _issue_lines(req: Requirement, findings: List[Finding]) -> str:
    lines = []
    for f in findings:
        others = [x for x in f.req_ids if x != req.req_id]
        with_part = f" with {', '.join(others)}" if others else ""
        lines.append(f"  - {f.kind.value}{with_part}: {f.reason}")
    return "\n".join(lines) if lines else "  - none reported"


def _suggest_batch(batch: List[Requirement], findings_by_req) -> Tuple[List[Suggestion], List[str]]:
    suggestions: List[Suggestion] = []
    warnings: List[str] = []
    by_id = {r.req_id: r for r in batch}
    blocks = []
    for r in batch:
        kind = r.type.value if r.type else "unknown"
        blocks.append(
            f"{r.req_id} [{kind}]: {source_text(r)}\n"
            f"  Known issues:\n{_issue_lines(r, findings_by_req[r.req_id])}"
        )
    result = call_json("suggest", SYSTEM_PROMPT, "REQUIREMENTS:\n\n" + "\n\n".join(blocks), SuggResult)

    returned = set()
    for item in result.suggestions:
        req = by_id.get(item.req_id)
        if req is None:
            continue
        returned.add(req.req_id)
        evidence = [req.source_span] if req.source_span else []

        def add(kind: SuggestionKind, content: Optional[str]) -> None:
            content = re.sub(r"^(As) a ([aeiouAEIOU])", r"\1 an \2", (content or "").strip())          
            if content:
                suggestions.append(
                    Suggestion(req_id=req.req_id, kind=kind, content=content, evidence=evidence)
                )

        add(SuggestionKind.IMPROVED_REQUIREMENT, item.improved_requirement)
        add(SuggestionKind.USER_STORY, item.user_story)
        for text in (item.acceptance_criteria or [])[:MAX_ITEMS]:
            add(SuggestionKind.ACCEPTANCE_CRITERIA, text)
        for text in (item.clarification_questions or [])[:MAX_ITEMS]:
            add(SuggestionKind.CLARIFICATION_QUESTION, text)

    for r in batch:
        if r.req_id not in returned:
            warnings.append(f"{r.req_id}: no suggestions returned")
    return suggestions, warnings


def generate_suggestions(
    reqs: List[Requirement], findings: List[Finding]
) -> Tuple[List[Suggestion], List[str]]:
    findings_by_req = defaultdict(list)
    for f in findings:
        for rid in f.req_ids:
            findings_by_req[rid].append(f)

    targets = [r for r in reqs if r.type != ReqType.OPEN_QUESTION]
    if config.SUGGEST_SCOPE == "flagged" and len(targets) > FLAGGED_ABOVE:
        # big document: only requirements that have findings get suggestions
        targets = [r for r in targets if findings_by_req.get(r.req_id)]
    batches = [targets[i:i + BATCH_SIZE] for i in range(0, len(targets), BATCH_SIZE)]

    suggestions: List[Suggestion] = []
    warnings: List[str] = []
    for batch_suggestions, batch_warnings in map_batches(
        lambda b: _suggest_batch(b, findings_by_req), batches
    ):
        suggestions += batch_suggestions
        warnings += batch_warnings
    return suggestions, warnings