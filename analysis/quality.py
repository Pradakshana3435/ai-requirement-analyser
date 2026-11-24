from typing import List, Tuple

from pydantic import BaseModel

from llm.client import call_json
from models import Document, Finding, FindingKind, ReqType, Requirement, Severity
from validate.grounding import find_span

BATCH_SIZE = 10
ALLOWED_KINDS = {FindingKind.AMBIGUOUS, FindingKind.INCOMPLETE, FindingKind.NON_TESTABLE}

SYSTEM_PROMPT = """You are a senior business analyst reviewing requirement statements for quality.
For each requirement, report only REAL problems of these kinds:

- ambiguous: vague or subjective wording that IS present (for example fast, easy, secure,
  user-friendly, quickly, as needed, appropriate), or wording that can be read in more than one way.
- incomplete: a detail needed to build or test it is MISSING from the statement: a value, limit,
  timing, method, actor, condition or what happens on failure. Use this when a statement names an
  action or calculation without saying how, when or with which values, even if the wording is clear.
- non_testable: it cannot be verified with a clear pass/fail check as written. A quality statement
  (speed, capacity, security, usability, reliability) with no measurable target is non_testable.

Dependency statements (a requirement that relies on another system, service or team) are incomplete
only when behaviour for failure or unavailability of that dependency is missing. Do not report them
as non_testable, and do not report missing integration details as incomplete.

Rules:
- Judge only the text given. Do not invent facts and do not suggest fixes.
- One requirement can have several findings, one per kind. A vague quality word with no measurable
  target is BOTH ambiguous and non_testable: report both.
- "quote" must be copied EXACTLY from that requirement (the words that cause the problem; for a
  missing detail, copy the most relevant phrase).
- "reason" is one short sentence explaining the problem.
- "severity" is low, medium or high (impact if the problem is not resolved).
- At most 3 findings per requirement. If a requirement is clear, report nothing for it.

Return JSON in exactly this shape:
{"findings": [{"req_id": "REQ-001", "kind": "ambiguous", "severity": "medium",
 "reason": "...", "quote": "..."}]}
The kind value must be one of: ambiguous, incomplete, non_testable.
"""


class FindingItem(BaseModel):
    req_id: str
    kind: str
    severity: str = "medium"
    reason: str
    quote: str


class QualityResult(BaseModel):
    findings: List[FindingItem]


def _norm(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _source_text(r: Requirement) -> str:
    return r.source_span.quote if r.source_span else r.text


def analyze_quality(doc: Document, reqs: List[Requirement]) -> Tuple[List[Finding], List[str]]:
    findings: List[Finding] = []
    warnings: List[str] = []
    seen = set()

    targets = [r for r in reqs if r.type != ReqType.OPEN_QUESTION]

    for i in range(0, len(targets), BATCH_SIZE):
        batch = targets[i:i + BATCH_SIZE]
        by_id = {r.req_id: r for r in batch}
        lines = "\n".join(f"{r.req_id}: {_source_text(r)}" for r in batch)
        result = call_json("quality", SYSTEM_PROMPT, f"REQUIREMENTS:\n{lines}", QualityResult)

        for item in result.findings:
            req = by_id.get(item.req_id)
            if req is None:
                continue
            try:
                kind = FindingKind(_norm(item.kind))
            except ValueError:
                warnings.append(f"{item.req_id}: unknown finding kind {item.kind!r}")
                continue
            if kind not in ALLOWED_KINDS:
                warnings.append(f"{item.req_id}: kind {kind.value!r} is not handled in this step")
                continue
            if (req.req_id, kind) in seen:
                continue
            seen.add((req.req_id, kind))

            try:
                severity = Severity(_norm(item.severity))
            except ValueError:
                severity = Severity.MEDIUM

            span = find_span(doc, item.quote, within=req.source_span)
            findings.append(
                Finding(
                    req_ids=[req.req_id],
                    kind=kind,
                    severity=severity,
                    reason=item.reason.strip(),
                    evidence=[span] if span else [],
                    grounded=span is not None,
                )
            )

    return findings, warnings