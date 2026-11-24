import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from typing import List, Tuple

from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from llm.client import call_json
from models import Document, Finding, FindingKind, ReqType, Requirement, Severity
from validate.grounding import find_span

MIN_SIMILARITY = 0.05   # raise to send fewer pairs to the model
TOP_K = 4                # neighbours kept per requirement
MAX_PAIRS = 40          # hard cap per document (protects the free-tier limits)
PAIR_BATCH = 10

SYSTEM_PROMPT = """You compare pairs of business requirements. For each pair, decide the relation:

- duplicate: A and B state the same need (the wording may differ) and neither adds anything
  meaningful that the other lacks.
- conflict: A and B cannot both be true or satisfied as written. This includes contradictory
  values, and also two rules that give different or mutually exclusive options for the same thing
  (for example "backups run daily" and "backups run weekly", or "only X is allowed" and "Y is
  allowed").
- none: they are related but are neither duplicates nor in conflict. This includes one statement
  adding detail to the other.

Rules:
- Judge only the text given. Do not invent facts.
- "quote_a" must be copied EXACTLY from A and "quote_b" EXACTLY from B: the words that show the
  duplication or the conflict. Leave them empty for "none".
- "reason" is one short sentence.
- Return every pair_id you were given.

Return JSON in exactly this shape:
{"results": [{"pair_id": "P1", "relation": "none", "reason": "", "quote_a": "", "quote_b": ""}]}
The relation value must be one of: duplicate, conflict, none.
"""


class PairItem(BaseModel):
    pair_id: str
    relation: str
    reason: str = ""
    quote_a: str = ""
    quote_b: str = ""


class PairResult(BaseModel):
    results: List[PairItem]


def source_text(r: Requirement) -> str:
    return r.source_span.quote if r.source_span else r.text

_SUFFIXES = ("ments", "ment", "ations", "ation", "ings", "ing", "ies", "ed", "es", "s")


def _stem(word: str) -> str:
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[: -len(suf)]
    return word


def _tokens(text: str) -> List[str]:
    """Lowercase words with common endings removed, so payment and pay match."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in ENGLISH_STOP_WORDS]

def shortlist_pairs(reqs: List[Requirement]) -> List[Tuple[Requirement, Requirement, float]]:
    if len(reqs) < 2:
        return []
    texts = [source_text(r) for r in reqs]
    try:
        matrix = TfidfVectorizer(
            tokenizer=_tokens, lowercase=False, token_pattern=None, ngram_range=(1, 2)
        ).fit_transform(texts)
    except ValueError:  # nothing left after removing stop words
        return []
    sim = cosine_similarity(matrix)

    chosen = {}
    for i in range(len(reqs)):
        scores = sorted(
            ((float(sim[i][j]), j) for j in range(len(reqs)) if j != i), reverse=True
        )[:TOP_K]
        for score, j in scores:
            if score >= MIN_SIMILARITY:
                chosen[tuple(sorted((i, j)))] = score

    ranked = sorted(chosen.items(), key=lambda kv: -kv[1])[:MAX_PAIRS]
    ranked.sort(key=lambda kv: kv[0])  # back to document order
    return [(reqs[a], reqs[b], s) for (a, b), s in ranked]


def find_duplicates_conflicts(doc: Document, reqs: List[Requirement]) -> Tuple[List[Finding], List[str]]:
    findings: List[Finding] = []
    warnings: List[str] = []

    candidates = [r for r in reqs if r.type != ReqType.OPEN_QUESTION]
    pairs = shortlist_pairs(candidates)

    for i in range(0, len(pairs), PAIR_BATCH):
        batch = pairs[i:i + PAIR_BATCH]
        by_pair = {f"P{n}": (a, b) for n, (a, b, _) in enumerate(batch, start=1)}
        blocks = "\n\n".join(
            f"{pid}\nA ({a.req_id}): {source_text(a)}\nB ({b.req_id}): {source_text(b)}"
            for pid, (a, b) in by_pair.items()
        )
        result = call_json("pairs", SYSTEM_PROMPT, f"PAIRS:\n\n{blocks}", PairResult)

        for item in result.results:
            if item.pair_id not in by_pair:
                continue
            a, b = by_pair[item.pair_id]
            relation = item.relation.strip().lower()
            if relation == "none":
                continue
            if relation not in ("duplicate", "conflict"):
                warnings.append(f"{item.pair_id}: unknown relation {item.relation!r}")
                continue

            span_a = find_span(doc, item.quote_a, within=a.source_span)
            span_b = find_span(doc, item.quote_b, within=b.source_span)
            findings.append(
                Finding(
                    req_ids=[a.req_id, b.req_id],
                    kind=FindingKind.CONFLICT if relation == "conflict" else FindingKind.DUPLICATE,
                    severity=Severity.HIGH if relation == "conflict" else Severity.MEDIUM,
                    reason=item.reason.strip(),
                    evidence=[s for s in (span_a, span_b) if s],
                    grounded=span_a is not None and span_b is not None,
                )
            )

    return findings, warnings