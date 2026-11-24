#split.py
import re
from typing import List, Tuple

from pydantic import BaseModel

from llm.client import call_json
from models import Document, Requirement, SourceSpan

MAX_CHUNK_CHARS = 5000

SYSTEM_PROMPT = """You are a business analyst assistant. You split business requirement text into
individual statements.

Rules:
- Extract every statement that expresses a need, rule, constraint, assumption, dependency, quality
  expectation or open question. Skip titles, greetings and filler.
- If one sentence contains several separate requirements, return one item for each part.
- "quote" must be copied EXACTLY, character for character, from the text (a sentence or part of one).
- "text" is the statement in one clear sentence. Stay close to the quote. Do NOT add numbers, names,
  systems, deadlines or any information that is not in the text.
- Keep the statements in the order they appear.

Return JSON in exactly this shape:
{"statements": [{"quote": "...", "text": "..."}]}
"""


class SplitItem(BaseModel):
    quote: str
    text: str


class SplitResult(BaseModel):
    statements: List[SplitItem]


def _chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[Tuple[int, int]]:
    """Split at paragraph boundaries. Returns (start, end) offsets into text."""
    chunks = []
    offset = 0
    chunk_start = 0
    chunk_end = 0
    for para in text.split("\n\n"):
        p_start, p_end = offset, offset + len(para)
        if chunk_end > chunk_start and p_end - chunk_start > max_chars:
            chunks.append((chunk_start, chunk_end))
            chunk_start = p_start
        chunk_end = p_end
        offset = p_end + 2
    chunks.append((chunk_start, chunk_end))
    return chunks


def _locate(chunk: str, quote: str, cursor: int):
    """Find quote in chunk, preferring a position after cursor. Returns (start, end) or None."""
    quote = quote.strip()
    if not quote:
        return None
    idx = chunk.find(quote, cursor)
    if idx == -1:
        idx = chunk.find(quote)
    if idx != -1:
        return idx, idx + len(quote)
    pattern = re.compile(r"\s+".join(re.escape(part) for part in quote.split()))
    match = pattern.search(chunk, cursor) or pattern.search(chunk)
    if match:
        return match.start(), match.end()
    return None


def split_requirements(doc: Document) -> Tuple[List[Requirement], List[str]]:
    requirements: List[Requirement] = []
    warnings: List[str] = []
    seen = set()

    for c_start, c_end in _chunks(doc.raw_text):
        chunk = doc.raw_text[c_start:c_end]
        user = f'TEXT:\n"""\n{chunk}\n"""'
        result = call_json("split", SYSTEM_PROMPT, user, SplitResult)

        cursor = 0
        for item in result.statements:
            found = _locate(chunk, item.quote, cursor)
            if not found:
                warnings.append(f"Quote not found in source, skipped: {item.quote[:80]!r}")
                continue
            start, end = found[0] + c_start, found[1] + c_start
            if (start, end) in seen:
                continue
            seen.add((start, end))
            cursor = found[1]
            span = SourceSpan(
                doc_id=doc.doc_id, start=start, end=end, quote=doc.raw_text[start:end]
            )
            requirements.append(
                Requirement(
                    req_id=f"REQ-{len(requirements) + 1:03d}",
                    text=item.text.strip() or span.quote,
                    source_span=span,
                )
            )
    return requirements, warnings