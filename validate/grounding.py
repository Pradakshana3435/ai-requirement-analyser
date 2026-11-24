import re
from typing import Optional

from models import Document, SourceSpan


def find_span(doc: Document, quote: str, within: Optional[SourceSpan] = None) -> Optional[SourceSpan]:
    """Locate quote in the document (optionally only inside `within`).
    Returns a SourceSpan whose quote equals the real document text, or None."""
    quote = (quote or "").strip()
    if not quote:
        return None

    lo, hi = (within.start, within.end) if within else (0, len(doc.raw_text))
    region = doc.raw_text[lo:hi]

    idx = region.find(quote)
    if idx != -1:
        start, end = lo + idx, lo + idx + len(quote)
    else:
        pattern = re.compile(r"\s+".join(re.escape(p) for p in quote.split()), re.IGNORECASE)
        match = pattern.search(region)
        if not match:
            return None
        start, end = lo + match.start(), lo + match.end()

    return SourceSpan(doc_id=doc.doc_id, start=start, end=end, quote=doc.raw_text[start:end])