import uuid
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"


class ReqType(str, Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    BUSINESS_RULE = "business_rule"
    CONSTRAINT = "constraint"
    ASSUMPTION = "assumption"
    DEPENDENCY = "dependency"
    OPEN_QUESTION = "open_question"


class FindingKind(str, Enum):
    AMBIGUOUS = "ambiguous"
    INCOMPLETE = "incomplete"
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    NON_TESTABLE = "non_testable"


class SuggestionKind(str, Enum):
    IMPROVED_REQUIREMENT = "improved_requirement"
    USER_STORY = "user_story"
    ACCEPTANCE_CRITERIA = "acceptance_criteria"
    CLARIFICATION_QUESTION = "clarification_question"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SourceSpan(BaseModel):
    """A piece of the original document. quote must equal raw_text[start:end]."""
    doc_id: str
    start: int
    end: int
    quote: str


class Document(BaseModel):
    doc_id: str = Field(default_factory=lambda: new_id("DOC"))
    filename: str = "pasted_text"
    raw_text: str

    def text_of(self, span: SourceSpan) -> str:
        return self.raw_text[span.start:span.end]

    def span_is_valid(self, span: SourceSpan) -> bool:
        return self.text_of(span) == span.quote


class Requirement(BaseModel):
    req_id: str
    text: str
    type: Optional[ReqType] = None
    source_span: Optional[SourceSpan] = None
    review_status: ReviewStatus = ReviewStatus.PENDING


class Finding(BaseModel):
    finding_id: str = Field(default_factory=lambda: new_id("FND"))
    req_ids: List[str]
    kind: FindingKind
    severity: Severity = Severity.MEDIUM
    reason: str
    evidence: List[SourceSpan] = Field(default_factory=list)
    grounded: bool = False
    review_status: ReviewStatus = ReviewStatus.PENDING


class Suggestion(BaseModel):
    sugg_id: str = Field(default_factory=lambda: new_id("SUG"))
    req_id: str
    kind: SuggestionKind
    content: str
    evidence: List[SourceSpan] = Field(default_factory=list)
    grounded: bool = False
    added_terms: List[str] = Field(default_factory=list)  # new facts found by the new-fact check
    review_status: ReviewStatus = ReviewStatus.PENDING
    edited_content: Optional[str] = None

    @property
    def final_content(self) -> str:
        return self.edited_content if self.edited_content else self.content


class AnalysisResult(BaseModel):
    document: Document
    requirements: List[Requirement] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    suggestions: List[Suggestion] = Field(default_factory=list)
    summary: str = ""
    warnings: List[str] = Field(default_factory=list)    