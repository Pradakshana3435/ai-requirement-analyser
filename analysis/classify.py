from typing import List

from pydantic import BaseModel

from llm.client import call_json
from models import ReqType, Requirement

BATCH_SIZE = 25

SYSTEM_PROMPT = """You are a business analyst assistant. Classify each requirement statement into
exactly one type:

- functional: a capability the system performs for a user or another system, such as search, send,
  display, calculate, generate or notify.
- non_functional: how well the system works: speed, capacity, availability, usability, reliability,
  scalability or similar qualities, whether measured or vague.
- business_rule: a policy, limit or decision rule of the business: quantities, amounts, time windows,
  deadlines for users, fees, penalties, eligibility, approvals, and who may do what. A statement that
  sets a limit or threshold on user actions or data is a business_rule even if it mentions the system.
- constraint: a fixed restriction on how the solution is built or run: required technology, platform,
  hosting or protocol, a mandated standard or regulation, privacy, security or data-retention
  mandates, budget or delivery deadline.
- assumption: something presumed true without confirmation, including any statement that begins
  with "Assumption" or says something is expected or taken for granted. Prefer this type over
  business_rule when the statement presumes something outside the system's control.
- dependency: something that relies on another team, system, vendor, service or deliverable.
- open_question: a question, or something explicitly undecided or unknown.

If a statement could fit two types, choose the one that describes its main point: an action the
system performs is functional, a rule or limit about users or data is business_rule, and a
restriction on how it is built is a constraint.

Judge only from the statement text. Do not rewrite the statements.
Return every req_id you were given, in the same order.

Return JSON in exactly this shape:
{"classifications": [{"req_id": "REQ-001", "type": "functional"}]}
The type value must be one of: functional, non_functional, business_rule, constraint,
assumption, dependency, open_question.
"""


class ClassItem(BaseModel):
    req_id: str
    type: str


class ClassResult(BaseModel):
    classifications: List[ClassItem]


def _normalise_type(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def classify_requirements(reqs: List[Requirement]) -> List[str]:
    """Sets .type on each requirement in place. Returns a list of warnings."""
    warnings: List[str] = []

    for i in range(0, len(reqs), BATCH_SIZE):
        batch = reqs[i:i + BATCH_SIZE]
        by_id = {r.req_id: r for r in batch}
        lines = "\n".join(
            f"{r.req_id}: {r.source_span.quote if r.source_span else r.text}" for r in batch
        )
        result = call_json("classify", SYSTEM_PROMPT, f"REQUIREMENTS:\n{lines}", ClassResult)

        for item in result.classifications:
            req = by_id.get(item.req_id)
            if req is None:
                continue
            try:
                req.type = ReqType(_normalise_type(item.type))
            except ValueError:
                warnings.append(f"{item.req_id}: unknown type {item.type!r}")

        for r in batch:
            if r.type is None and not any(w.startswith(r.req_id) for w in warnings):
                warnings.append(f"{r.req_id}: was not classified")

    return warnings