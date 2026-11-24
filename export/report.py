import csv
import io
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import List

from docx import Document as DocxDocument
from docx.enum.section import WD_ORIENT

from models import AnalysisResult, ReviewStatus, SuggestionKind

STATUS_LABEL = {
    "pending": "Not yet reviewed",
    "accepted": "Accepted",
    "edited": "Edited",
    "rejected": "Rejected",
}

SUGGESTION_SECTIONS = [
    (SuggestionKind.IMPROVED_REQUIREMENT, "Improved Requirements"),
    (SuggestionKind.USER_STORY, "User Stories"),
    (SuggestionKind.ACCEPTANCE_CRITERIA, "Acceptance Criteria"),
    (SuggestionKind.CLARIFICATION_QUESTION, "Clarification Questions"),
]

NOTE = (
    "AI-generated results are suggestions. Only items marked Accepted or Edited have been "
    "reviewed by a Business Analyst; items marked Not yet reviewed have not."
)


@dataclass
class Section:
    title: str
    text: str = ""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)


# ---------- small helpers ----------

def _label(item) -> str:
    return STATUS_LABEL[item.review_status.value]


def _title(value: str) -> str:
    return value.replace("_", " ").title()


def _quote(span) -> str:
    return span.quote.replace("\n", " ") if span else ""


def _evidence(item) -> str:
    return " | ".join(e.quote.replace("\n", " ") for e in item.evidence)


def _flag(item) -> str:
    if item.grounded:
        return ""
    terms = getattr(item, "added_terms", [])
    return "Unsupported" + (f" (added: {', '.join(terms)})" if terms else "")


def _table(title: str, headers: List[str], rows: List[List[str]]) -> Section:
    if not rows:
        return Section(title, text="None.")
    return Section(title, headers=headers, rows=rows)


def _counts(items) -> List[str]:
    counter = Counter(i.review_status.value for i in items)
    return [str(counter.get(k, 0)) for k in ("pending", "accepted", "edited", "rejected")]


# ---------- content ----------

def build_sections(result: AnalysisResult) -> List[Section]:
    rejected = ReviewStatus.REJECTED
    live_findings = [f for f in result.findings if f.review_status != rejected]
    live_suggestions = [s for s in result.suggestions if s.review_status != rejected]

    sections = [
        Section("Requirement Summary", text=result.summary or "No summary available."),
        _table(
            "Requirement Inventory",
            ["ID", "Type", "Requirement", "Source text", "Review status"],
            [
                [r.req_id, r.type.value if r.type else "unclassified", r.text,
                 _quote(r.source_span), _label(r)]
                for r in result.requirements
            ],
        ),
        _table(
            "Requirement Quality Findings",
            ["Requirements", "Issue", "Severity", "Reason", "Evidence", "Review status", "Check"],
            [
                [", ".join(f.req_ids), _title(f.kind.value), f.severity.value.title(), f.reason,
                 _evidence(f), _label(f), _flag(f)]
                for f in live_findings
            ],
        ),
    ]

    for kind, title in SUGGESTION_SECTIONS:
        sections.append(
            _table(
                title,
                ["Requirement", "Suggestion", "Review status", "Check"],
                [
                    [s.req_id, s.final_content, _label(s), _flag(s)]
                    for s in live_suggestions
                    if s.kind == kind
                ],
            )
        )

    sections.append(
        _table(
            "Traceability",
            ["Requirement", "Source text", "Findings", "Suggestions"],
            [
                [
                    r.req_id,
                    _quote(r.source_span),
                    ", ".join(
                        f"{f.finding_id} ({f.kind.value})"
                        for f in live_findings if r.req_id in f.req_ids
                    ),
                    ", ".join(s.sugg_id for s in live_suggestions if s.req_id == r.req_id),
                ]
                for r in result.requirements
            ],
        )
    )

    sections.append(
        Section(
            "Review Status",
            headers=["Item type", "Not yet reviewed", "Accepted", "Edited", "Rejected"],
            rows=[
                ["Requirements"] + _counts(result.requirements),
                ["Findings"] + _counts(result.findings),
                ["Suggestions"] + _counts(result.suggestions),
            ],
        )
    )

    rejected_rows = [
        ["Finding", f.finding_id, ", ".join(f.req_ids), _title(f.kind.value), f.reason]
        for f in result.findings if f.review_status == rejected
    ] + [
        ["Suggestion", s.sugg_id, s.req_id, _title(s.kind.value), s.content]
        for s in result.suggestions if s.review_status == rejected
    ]
    if rejected_rows:
        sections.append(
            Section("Appendix: Rejected Items",
                    headers=["Type", "ID", "Requirement", "Kind", "Content"], rows=rejected_rows)
        )
    else:
        sections.append(Section("Appendix: Rejected Items", text="No items were rejected."))
    return sections


# ---------- Markdown ----------

def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def to_markdown(result: AnalysisResult) -> str:
    lines = [
        "# Requirement Analysis Report",
        "",
        f"Source document: {result.document.filename}",
        "",
        f"> {NOTE}",
    ]
    for sec in build_sections(result):
        lines += ["", f"## {sec.title}"]
        if sec.text:
            lines += ["", sec.text]
        if sec.headers:
            lines += ["", "| " + " | ".join(_cell(h) for h in sec.headers) + " |",
                      "| " + " | ".join("---" for _ in sec.headers) + " |"]
            lines += ["| " + " | ".join(_cell(v) for v in row) + " |" for row in sec.rows]
    return "\n".join(lines) + "\n"


# ---------- DOCX ----------

def _clean(value) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value))


def to_docx(result: AnalysisResult) -> bytes:
    doc = DocxDocument()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width

    doc.add_heading("Requirement Analysis Report", 0)
    doc.add_paragraph(f"Source document: {_clean(result.document.filename)}")
    doc.add_paragraph().add_run(NOTE).italic = True

    for sec in build_sections(result):
        doc.add_heading(sec.title, 1)
        if sec.text:
            doc.add_paragraph(_clean(sec.text))
        if sec.headers:
            table = doc.add_table(rows=1, cols=len(sec.headers))
            table.style = "Table Grid"
            for i, header in enumerate(sec.headers):
                table.rows[0].cells[i].paragraphs[0].add_run(_clean(header)).bold = True
            for row in sec.rows:
                cells = table.add_row().cells
                for i, value in enumerate(row):
                    cells[i].text = _clean(value)

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


# ---------- CSV ----------

CSV_COLUMNS = [
    "req_id", "type", "original_requirement", "source_quote", "requirement_status",
    "improved_requirement", "improved_status", "user_story", "acceptance_criteria",
    "clarification_questions", "findings", "unsupported_checks",
]


def to_csv(result: AnalysisResult) -> str:
    """One row per requirement. Rejected suggestions and findings are left out."""
    live = [s for s in result.suggestions if s.review_status != ReviewStatus.REJECTED]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for r in result.requirements:
        mine = [s for s in live if s.req_id == r.req_id]

        def first(kind):
            return next((s for s in mine if s.kind == kind), None)

        def joined(kind):
            return "\n".join(s.final_content for s in mine if s.kind == kind)

        improved = first(SuggestionKind.IMPROVED_REQUIREMENT)
        story = first(SuggestionKind.USER_STORY)
        findings = [
            f for f in result.findings
            if r.req_id in f.req_ids and f.review_status != ReviewStatus.REJECTED
        ]
        writer.writerow({
            "req_id": r.req_id,
            "type": r.type.value if r.type else "unclassified",
            "original_requirement": r.text,
            "source_quote": _quote(r.source_span),
            "requirement_status": _label(r),
            "improved_requirement": improved.final_content if improved else "",
            "improved_status": _label(improved) if improved else "",
            "user_story": story.final_content if story else "",
            "acceptance_criteria": joined(SuggestionKind.ACCEPTANCE_CRITERIA),
            "clarification_questions": joined(SuggestionKind.CLARIFICATION_QUESTION),
            "findings": "; ".join(
                f"{_title(f.kind.value)} ({f.severity.value}): {f.reason}" for f in findings
            ),
            "unsupported_checks": "; ".join(f"{s.sugg_id}: {_flag(s)}" for s in mine if _flag(s)),
        })
    return buffer.getvalue()