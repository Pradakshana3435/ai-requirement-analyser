import glob
import json
import os
from types import SimpleNamespace as NS

from eval.metrics import aggregate, match_requirements, render_report, review_sheet, score_document

RAW = "Users can log in. Users can log in again. Orders ship fast."


def kind(v):
    return NS(value=v)


def req(rid, text, ty, start=None):
    if start is None:
        start = RAW.find(text)
    return NS(req_id=rid, text=text, type=kind(ty),
              source_span=NS(start=start, end=start + len(text)))


def finding(k, ids, grounded=True):
    return NS(kind=kind(k), req_ids=ids, grounded=grounded)


def make(reqs, findings=(), suggestions=(), warnings=()):
    doc = NS(span_is_valid=lambda s: True)
    return NS(document=doc, requirements=list(reqs), findings=list(findings),
              suggestions=list(suggestions), warnings=list(warnings))


GOLD = {
    "requirements": [
        {"id": "G1", "quote": "Users can log in.", "type": "functional"},
        {"id": "G2", "quote": "Users can log in again.", "type": "functional"},
        {"id": "G3", "quote": "Orders ship fast.", "type": "non_functional"},
    ],
    "issues": [
        {"kind": "duplicate", "req_ids": ["G1", "G2"]},
        {"kind": "ambiguous", "req_ids": ["G3"]},
    ],
}


def perfect():
    return make(
        [req("R1", "Users can log in.", "functional"),
         req("R2", "Users can log in again.", "functional"),
         req("R3", "Orders ship fast.", "non_functional")],
        [finding("duplicate", ["R1", "R2"]), finding("ambiguous", ["R3"])],
    )


def test_perfect_result_scores_100_percent():
    m = aggregate([score_document(RAW, GOLD, perfect())])
    assert m["split"]["f1"] == 1.0
    assert m["type_accuracy"] == 1.0
    assert m["issues"]["overall"]["precision"] == 1.0
    assert m["issues"]["overall"]["recall"] == 1.0


def test_missing_requirement_lowers_recall_and_misses_its_issues():
    result = make([req("R1", "Users can log in.", "functional"),
                   req("R3", "Orders ship fast.", "non_functional")],
                  [finding("duplicate", ["R1"]), finding("ambiguous", ["R3"])])
    m = aggregate([score_document(RAW, GOLD, result)])
    assert abs(m["split"]["recall"] - 2 / 3) < 1e-9
    assert m["issues"]["duplicate"]["recall"] == 0.0
    assert m["issues"]["ambiguous"]["recall"] == 1.0


def test_wrong_type_lowers_accuracy():
    result = perfect()
    result.requirements[2].type = kind("constraint")
    m = aggregate([score_document(RAW, GOLD, result)])
    assert abs(m["type_accuracy"] - 2 / 3) < 1e-9


def test_pair_issue_needs_both_requirements():
    result = perfect()
    result.findings[0] = finding("duplicate", ["R1"])
    m = aggregate([score_document(RAW, GOLD, result)])
    assert m["issues"]["duplicate"]["recall"] == 0.0
    assert m["issues"]["duplicate"]["precision"] == 0.0


def test_extra_finding_lowers_precision_only():
    result = perfect()
    result.findings.append(finding("conflict", ["R1", "R3"]))
    m = aggregate([score_document(RAW, GOLD, result)])
    assert m["issues"]["overall"]["recall"] == 1.0
    assert abs(m["issues"]["overall"]["precision"] - 2 / 3) < 1e-9


def test_matching_falls_back_to_text_when_offsets_differ():
    pred = [req("R1", "Users can log in.", "functional", start=500)]
    got = match_requirements(RAW, GOLD["requirements"], pred)
    assert got["G1"].req_id == "R1"


def test_unsupported_rate_ignores_clarification_questions():
    sugg = [NS(kind=kind("improved_requirement"), req_id="R1", content="x", grounded=False),
            NS(kind=kind("user_story"), req_id="R1", content="y", grounded=True),
            NS(kind=kind("clarification_question"), req_id="R1", content="z", grounded=False)]
    result = perfect()
    result.suggestions = sugg
    m = aggregate([score_document(RAW, GOLD, result)])
    assert m["unsupported_rate"] == 0.5


def test_report_and_review_sheet_render():
    result = perfect()
    result.suggestions = [NS(kind=kind("user_story"), req_id="R1", content="As a user", grounded=True)]
    m = aggregate([score_document(RAW, GOLD, result)])
    report = render_report(m, [("eval_01", 3, 2, 1, 4.2)], 5.0, [])
    assert "## Issue detection" in report and "eval_01" in report
    sheet = review_sheet([("eval_01", result)])
    assert "usefulness_1_to_5" in sheet and "As a user" in sheet


def test_gold_dataset_is_consistent():
    paths = sorted(glob.glob("data/eval/gold/*.json"))
    assert 20 <= len(paths) <= 30
    for path in paths:
        gold = json.load(open(path, encoding="utf-8"))
        text = open(os.path.join("data/eval/docs", gold["doc"]), encoding="utf-8").read()
        ids = {r["id"] for r in gold["requirements"]}
        assert all(r["quote"] in text for r in gold["requirements"]), path
        assert all(set(i["req_ids"]) <= ids for i in gold["issues"]), path
