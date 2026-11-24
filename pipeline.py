#pipeline.py
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from analysis.classify import classify_requirements
from analysis.pairs import find_duplicates_conflicts
from analysis.quality import analyze_quality
from analysis.suggest import generate_suggestions
from analysis.summary import summarize
from ingest.split import split_requirements
from llm.client import LLMError
from models import AnalysisResult, Document
from validate.new_facts import check_new_facts
import config

ProgressFn = Callable[[str, float], None]


def _safe(label: str, fn, default, result: AnalysisResult):
    """Run one stage; on a model failure record a warning and carry on."""
    try:
        return fn()
    except LLMError as exc:
        result.warnings.append(f"{label} failed: {exc}")
        return default


def run_analysis(doc: Document, progress: Optional[ProgressFn] = None) -> AnalysisResult:
    def step(name: str, fraction: float) -> None:
        if progress:
            progress(name, fraction)

    result = AnalysisResult(document=doc)

    step("Splitting into requirements", 0.05)
    reqs, warnings = split_requirements(doc)  # failure here stops the run
    result.requirements = reqs
    result.warnings += warnings
    if not reqs:
        result.warnings.append("No requirements were found in this document.")
        step("Done", 1.0)
        return result

    step("Classifying requirements", 0.20)
    result.warnings += _safe("Classification", lambda: classify_requirements(reqs), [], result)

    with ThreadPoolExecutor(max_workers=max(1, config.MAX_PARALLEL)) as pool:
        # The summary only needs the requirements, so it runs alongside everything below.
        summary_future = pool.submit(_safe, "Summary", lambda: summarize(reqs), "", result)

        step("Checking quality, duplicates and conflicts", 0.40)
        quality_future = pool.submit(
            _safe, "Quality analysis", lambda: analyze_quality(doc, reqs), ([], []), result)
        pairs_future = pool.submit(
            _safe, "Duplicate/conflict check", lambda: find_duplicates_conflicts(doc, reqs), ([], []), result)
        quality, w1 = quality_future.result()
        pairs, w2 = pairs_future.result()
        result.warnings += w1 + w2
        result.findings = quality + pairs

        step("Generating suggestions", 0.65)
        suggestions, w = _safe(
            "Suggestion generation", lambda: generate_suggestions(reqs, result.findings), ([], []), result)
        result.suggestions = suggestions
        result.warnings += w

        step("Checking suggestions for unsupported facts", 0.85)
        result.warnings += _safe(
            "New-fact check", lambda: check_new_facts(reqs, result.suggestions), [], result)

        step("Finishing summary", 0.95)
        result.summary = summary_future.result()

    step("Done", 1.0)
    return result